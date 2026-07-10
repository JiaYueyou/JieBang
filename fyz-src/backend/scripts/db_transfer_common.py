"""Shared helpers for the numbered database-transfer scripts."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import aiomysql
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
SNAPSHOT_PATH = SCRIPTS_DIR / "mysql_snapshot.sql"
MANIFEST_PATH = SCRIPTS_DIR / "mysql_snapshot_manifest.json"

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


def load_manifest() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists() or not MANIFEST_PATH.exists():
        raise RuntimeError(
            "MySQL snapshot is missing. The repository maintainer must run "
            "'python scripts/export_mysql_snapshot.py' first."
        )
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    actual_hash = sha256_file(SNAPSHOT_PATH)
    if manifest.get("sha256") != actual_hash:
        raise RuntimeError(
            "mysql_snapshot.sql checksum does not match its manifest; refuse to import."
        )
    return manifest


async def current_alembic_revision(connection: aiomysql.Connection) -> str | None:
    tables = await list_base_tables(connection)
    if "alembic_version" not in tables:
        return None
    async with connection.cursor() as cursor:
        await cursor.execute("SELECT version_num FROM alembic_version")
        row = await cursor.fetchone()
        return str(row[0]) if row else None
