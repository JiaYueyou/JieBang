"""Shared helpers for the numbered database-transfer scripts.

The checked-in snapshot, manifest, and verification summary form one package.
Every consumer validates all three before connecting to or mutating a target
database.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import aiomysql
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
SNAPSHOT_PATH = SCRIPTS_DIR / "mysql_snapshot.sql"
MANIFEST_PATH = SCRIPTS_DIR / "mysql_snapshot_manifest.json"
VERIFICATION_PATH = SCRIPTS_DIR / "mysql_snapshot_verification.json"
PACKAGE_FORMAT_VERSION = 3

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import DATABASE_URL  # noqa: E402


def quote_identifier(value: str) -> str:
    """Quote a MySQL identifier obtained from database metadata."""
    return f"`{value.replace('`', '``')}`"


def mysql_connection_options() -> dict[str, Any]:
    """Build aiomysql options from the same DATABASE_URL used by FastAPI."""
    url = make_url(DATABASE_URL)
    if not url.drivername.startswith("mysql"):
        raise RuntimeError(
            f"Database transfer requires MySQL, but DATABASE_URL uses {url.drivername!r}."
        )
    if not url.database:
        raise RuntimeError("DATABASE_URL must include the target database name.")
    return {
        "host": url.host or "localhost",
        "port": url.port or 3306,
        "user": url.username or "root",
        "password": url.password or "",
        "db": url.database,
        "charset": "utf8mb4",
        "autocommit": False,
    }


async def connect_mysql() -> aiomysql.Connection:
    return await aiomysql.connect(**mysql_connection_options())


async def list_base_tables(connection: aiomysql.Connection) -> list[str]:
    async with connection.cursor() as cursor:
        await cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        return sorted(str(row[0]) for row in await cursor.fetchall())


async def table_counts(connection: aiomysql.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    async with connection.cursor() as cursor:
        for table in await list_base_tables(connection):
            await cursor.execute(f"SELECT COUNT(*) FROM {quote_identifier(table)}")
            counts[table] = int((await cursor.fetchone())[0])
    return counts


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def repository_alembic_head() -> str:
    """Return the repository's one and only Alembic head."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    heads = ScriptDirectory.from_config(config).get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"Expected exactly one Alembic head, found {heads!r}.")
    return str(heads[0])


def _count_insert_rows(values_sql: str) -> int:
    """Count top-level value tuples in SQL emitted by our exporter."""
    depth = 0
    rows = 0
    quoted = False
    escaped = False
    for char in values_sql:
        if escaped:
            escaped = False
            continue
        if quoted and char == "\\":
            escaped = True
            continue
        if char == "'":
            quoted = not quoted
            continue
        if quoted:
            continue
        if char == "(":
            if depth == 0:
                rows += 1
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise RuntimeError("Snapshot SQL contains unbalanced parentheses.")
    if quoted or depth != 0:
        raise RuntimeError("Snapshot SQL contains an unterminated literal or tuple.")
    return rows


def inspect_snapshot_sql(path: Path) -> dict[str, Any]:
    """Inspect only the deliberately narrow SQL grammar emitted by this project."""
    revision: str | None = None
    deletes: list[str] = []
    row_counts: dict[str, int] = {}
    table_digests: dict[str, Any] = {}
    # Column identifiers cannot contain ``)`` in exporter output.  Keeping this
    # group narrow is important because JSON/text values may themselves contain
    # the token " VALUES ".
    insert_pattern = re.compile(r"^INSERT INTO `([^`]+)` \([^)]*\) VALUES (.*);$")
    delete_pattern = re.compile(r"^DELETE FROM `([^`]+)`;$")
    revision_pattern = re.compile(r"^-- Alembic revision: (\S+)$")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("--"):
            match = revision_pattern.match(line)
            if match:
                revision = match.group(1)
            continue
        match = delete_pattern.match(line)
        if match:
            deletes.append(match.group(1))
            continue
        match = insert_pattern.match(line)
        if not match:
            raise RuntimeError(f"Snapshot contains unsupported SQL: {line[:120]!r}")
        table, values_sql = match.groups()
        row_counts[table] = row_counts.get(table, 0) + _count_insert_rows(values_sql)
        digest = table_digests.setdefault(table, hashlib.sha256())
        digest.update((line + "\n").encode("utf-8"))

    return {
        "revision": revision,
        "delete_tables": deletes,
        "row_counts": row_counts,
        "table_sha256": {
            table: digest.hexdigest() for table, digest in sorted(table_digests.items())
        },
    }


def validate_snapshot_package(
    snapshot_path: Path = SNAPSHOT_PATH,
    manifest_path: Path = MANIFEST_PATH,
    verification_path: Path | None = VERIFICATION_PATH,
    *,
    expected_revision: str | None = None,
) -> dict[str, Any]:
    """Strictly validate package metadata, SQL contents, and checksums."""
    if not snapshot_path.is_file() or not manifest_path.is_file():
        raise RuntimeError(
            "MySQL snapshot package is incomplete. The source maintainer must run "
            "'python scripts/export_mysql_snapshot.py --publish'."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read snapshot manifest: {exc}") from exc
    if manifest.get("format_version") != PACKAGE_FORMAT_VERSION:
        raise RuntimeError(
            f"Unsupported snapshot manifest format {manifest.get('format_version')!r}; "
            f"expected {PACKAGE_FORMAT_VERSION}."
        )
    revision = manifest.get("alembic_revision")
    if not isinstance(revision, str) or not revision:
        raise RuntimeError("Snapshot manifest has no Alembic revision.")
    if expected_revision is not None and revision != expected_revision:
        raise RuntimeError(
            f"Snapshot revision mismatch: expected={expected_revision!r}, actual={revision!r}."
        )
    if manifest.get("data_file") != snapshot_path.name:
        raise RuntimeError("Snapshot manifest data_file does not name the supplied SQL file.")

    raw_counts = manifest.get("table_counts")
    if not isinstance(raw_counts, dict) or not raw_counts:
        raise RuntimeError("Snapshot manifest table_counts must be a non-empty object.")
    counts: dict[str, int] = {}
    for table, count in raw_counts.items():
        if (
            not isinstance(table, str)
            or not table
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
        ):
            raise RuntimeError(f"Invalid table count entry: {table!r}={count!r}.")
        counts[table] = count
    if list(counts) != sorted(counts):
        raise RuntimeError("Snapshot manifest table_counts must be sorted by table name.")
    if manifest.get("total_rows") != sum(counts.values()):
        raise RuntimeError("Snapshot manifest total_rows does not equal its table counts.")
    if manifest.get("table_count") != len(counts):
        raise RuntimeError("Snapshot manifest table_count does not equal its table list.")
    expected_names_hash = sha256_text("\n".join(counts) + "\n")
    if manifest.get("table_names_sha256") != expected_names_hash:
        raise RuntimeError("Snapshot manifest table_names_sha256 is invalid.")

    actual_hash = sha256_file(snapshot_path)
    if manifest.get("sha256") != actual_hash:
        raise RuntimeError("Snapshot SQL checksum does not match its manifest; refuse to import.")
    if manifest.get("size_bytes") != snapshot_path.stat().st_size:
        raise RuntimeError("Snapshot SQL byte size does not match its manifest.")

    audit = inspect_snapshot_sql(snapshot_path)
    if audit["revision"] != revision:
        raise RuntimeError("Snapshot SQL header and manifest revisions differ.")
    if sorted(audit["delete_tables"]) != sorted(counts) or len(
        audit["delete_tables"]
    ) != len(counts):
        raise RuntimeError("Snapshot SQL must delete every manifest table exactly once.")
    sql_counts = {table: int(audit["row_counts"].get(table, 0)) for table in counts}
    if set(audit["row_counts"]) - set(counts) or sql_counts != counts:
        raise RuntimeError(
            f"Snapshot SQL row counts differ from manifest: expected={counts}, actual={sql_counts}."
        )
    empty_hash = hashlib.sha256(b"").hexdigest()
    sql_table_hashes = {
        table: audit["table_sha256"].get(table, empty_hash) for table in counts
    }
    if manifest.get("table_sha256") != sql_table_hashes:
        raise RuntimeError("Snapshot per-table content checksums differ from its manifest.")

    if verification_path is not None:
        if not verification_path.is_file():
            raise RuntimeError("Snapshot verification summary is missing.")
        try:
            summary = json.loads(verification_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot read snapshot verification summary: {exc}") from exc
        if summary.get("status") != "passed":
            raise RuntimeError("Snapshot verification summary is not passed.")
        expected_summary = {
            "alembic_revision": revision,
            "snapshot_sha256": actual_hash,
            "manifest_sha256": sha256_file(manifest_path),
            "table_count": len(counts),
            "total_rows": sum(counts.values()),
        }
        for key, value in expected_summary.items():
            if summary.get(key) != value:
                raise RuntimeError(f"Snapshot verification summary field {key!r} is invalid.")
        checks = summary.get("checks")
        if (
            not isinstance(checks, dict)
            or not checks
            or not all(value is True for value in checks.values())
        ):
            raise RuntimeError("Snapshot verification summary contains a failed check.")
    return manifest


def load_manifest() -> dict[str, Any]:
    """Load the current, complete package and require the repository head."""
    # Validate the three package files first.  This preserves a purely file-based
    # fast-fail path for missing/corrupt packages before Alembic metadata is even
    # inspected by an orchestrator preflight.
    manifest = validate_snapshot_package(
        SNAPSHOT_PATH,
        MANIFEST_PATH,
        VERIFICATION_PATH,
    )
    expected_revision = repository_alembic_head()
    if manifest["alembic_revision"] != expected_revision:
        raise RuntimeError(
            "Snapshot revision mismatch: "
            f"expected={expected_revision!r}, "
            f"actual={manifest['alembic_revision']!r}."
        )
    return manifest


async def current_alembic_revision(connection: aiomysql.Connection) -> str | None:
    tables = await list_base_tables(connection)
    if "alembic_version" not in tables:
        return None
    async with connection.cursor() as cursor:
        await cursor.execute("SELECT version_num FROM alembic_version")
        rows = await cursor.fetchall()
        if len(rows) > 1:
            raise RuntimeError(f"Database has multiple Alembic heads: {rows!r}.")
        return str(rows[0][0]) if rows else None
