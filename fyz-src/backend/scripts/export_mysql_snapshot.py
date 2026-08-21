"""Maintainer tool: create and optionally publish a complete MySQL snapshot.

Export runs inside one repeatable-read, read-only transaction.  Canonical files
are never touched until a staged package has passed the same strict checks used
by the importer.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from db_transfer_common import (
    MANIFEST_PATH,
    PACKAGE_FORMAT_VERSION,
    SNAPSHOT_PATH,
    VERIFICATION_PATH,
    connect_mysql,
    current_alembic_revision,
    list_base_tables,
    mysql_connection_options,
    quote_identifier,
    repository_alembic_head,
    sha256_file,
    sha256_text,
    table_counts,
    validate_snapshot_package,
)

BATCH_SIZE = 100
REQUIRED_TABLES_BY_REVISION = {
    "20260809_0020": {
        "analysis_baseline_snapshot",
        "analysis_baseline_skill",
        "job_source_observation",
        "pipeline_run",
    },
    "20260820_0021": {"enterprise_department"},
    "20260820_0022": {
        "external_job_identity",
        "external_job_version",
        "source_snapshot",
    },
    "20260820_0023": {"source_snapshot"},
    "20260820_0024": {"job_import_quarantine"},
    "20260820_0025": {"standard_job", "standard_job_alias"},
}

REQUIRED_COLUMNS_BY_REVISION = {
    "20260820_0023": {
        "source_snapshot": {"scope_hash", "scope_json"},
    },
    "20260820_0024": {
        "data_source": {"last_success_at", "last_error", "freshness_slo_minutes"},
        "job_import_quarantine": {
            "source_file", "record_index", "payload_hash", "raw_payload",
            "error_codes", "status",
        },
    },
}


def sql_literal(connection, value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("NaN and Infinity cannot be exported to portable SQL")
        return repr(value)
    if isinstance(value, (datetime, date, time)):
        text = value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
        return connection.escape(text)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"0x{bytes(value).hex()}"
    return connection.escape(str(value))


def sanitize_competition_row(
    table: str,
    columns: list[str],
    row: tuple[Any, ...],
    identity_replacements: dict[str, str] | None = None,
) -> tuple[Any, ...]:
    """Remove development identities while preserving analytical demo facts."""
    data = dict(zip(columns, row))
    row_id = int(data.get("id") or 0) if str(data.get("id") or "0").isdigit() else 0
    if table == "user":
        data["password_hash"] = "!competition-bootstrap-required!"
    elif table == "resume":
        extension = Path(str(data.get("original_filename") or "resume.txt")).suffix or ".txt"
        data["name"] = f"演示候选人{row_id:02d}"
        data["original_filename"] = f"candidate-{row_id:02d}{extension.lower()}"
        data["storage_key"] = f"competition/resume-{row_id:02d}{extension.lower()}"
        data["content_hash"] = hashlib.sha256(f"competition-resume-{row_id}".encode()).hexdigest()
    elif table == "resume_parse_result":
        resume_id = int(data.get("resume_id") or row_id)
        data["parsed_text"] = "比赛演示候选人档案；能力分析以已审核的结构化技能证据为准。"
        profile = data.get("profile")
        if isinstance(profile, str):
            try:
                profile = json.loads(profile)
            except json.JSONDecodeError:
                profile = {}
        profile = dict(profile or {})
        for key in ("email", "phone", "mobile", "wechat", "address", "contact"):
            profile.pop(key, None)
        profile["name"] = f"演示候选人{resume_id:02d}"
        data["profile"] = json.dumps(profile, ensure_ascii=False)
    elif table in {"enterprise_talent", "enterprise_employee_directory"}:
        data["employee_no"] = f"DEMO{row_id:04d}"
        data["name"] = f"演示人才{row_id:02d}"
    elif table == "retrieval_query_log":
        data["query_summary"] = "比赛演示检索"
    elif table == "user_favorite":
        data["note"] = ""
    elif table == "user_browse_history":
        data["description"] = ""
    elif table == "agent_run" and "resume" in str(data.get("agent_type") or "").lower():
        data["input_summary"] = "比赛演示候选人档案"
        data["structured_output"] = None
    replacements = identity_replacements or {}
    for column, value in data.items():
        if not isinstance(value, str):
            continue
        for original, pseudonym in replacements.items():
            if original:
                value = value.replace(original, pseudonym)
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[已脱敏邮箱]", value)
        value = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[已脱敏手机]", value)
        value = re.sub(r"(?<!\d)\d{17}[0-9Xx](?!\d)", "[已脱敏证件]", value)
        data[column] = value
    return tuple(data[column] for column in columns)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_verification_summary(
    snapshot_path: Path,
    manifest_path: Path,
    verification_path: Path,
    manifest: dict[str, Any],
) -> None:
    summary = {
        "format_version": 1,
        "status": "passed",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "alembic_revision": manifest["alembic_revision"],
        "snapshot_sha256": sha256_file(snapshot_path),
        "manifest_sha256": sha256_file(manifest_path),
        "table_count": manifest["table_count"],
        "total_rows": manifest["total_rows"],
        "checks": {
            "source_revision_matches_repository_head": True,
            "required_migration_tables_present": True,
            "consistent_snapshot_transaction": True,
            "sql_grammar_valid": True,
            "sql_row_counts_match_manifest": True,
            "sql_checksum_matches_manifest": True,
            "per_table_checksums_match_manifest": True,
        },
    }
    _write_json(verification_path, summary)


async def export_snapshot(
    output_dir: Path, *, expected_revision: str, competition: bool = False
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_dir / SNAPSHOT_PATH.name
    manifest_path = output_dir / MANIFEST_PATH.name
    verification_path = output_dir / VERIFICATION_PATH.name
    for path in (snapshot_path, manifest_path, verification_path):
        if path.exists():
            raise RuntimeError(f"Refuse to overwrite staged export file: {path}")

    connection = await connect_mysql()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            await cursor.execute("SET TRANSACTION READ ONLY")
            await cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")

        revision = await current_alembic_revision(connection)
        if revision != expected_revision:
            raise RuntimeError(
                f"Source database revision is {revision!r}, expected {expected_revision!r}; "
                "refuse to label or publish this database as the requested revision."
            )
        tables = await list_base_tables(connection)
        if expected_revision not in REQUIRED_TABLES_BY_REVISION:
            raise RuntimeError(
                f"No required-table contract is registered for {expected_revision}."
            )
        required: set[str] = set()
        for revision_key, revision_tables in REQUIRED_TABLES_BY_REVISION.items():
            required.update(revision_tables)
            if revision_key == expected_revision:
                break
        missing = sorted(required - set(tables))
        if missing:
            raise RuntimeError(
                f"Source database is missing tables required by {expected_revision}: {missing}."
            )
        required_columns: dict[str, set[str]] = {}
        for revision_key in REQUIRED_TABLES_BY_REVISION:
            for table, columns in REQUIRED_COLUMNS_BY_REVISION.get(revision_key, {}).items():
                required_columns.setdefault(table, set()).update(columns)
            if revision_key == expected_revision:
                break
        if required_columns:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE()"
                )
                actual_columns: dict[str, set[str]] = {}
                for table, column in await cursor.fetchall():
                    actual_columns.setdefault(str(table), set()).add(str(column))
            missing_columns = sorted(
                f"{table}.{column}"
                for table, columns in required_columns.items()
                for column in columns - actual_columns.get(table, set())
            )
            if missing_columns:
                raise RuntimeError(
                    f"Source database is missing columns required by {expected_revision}: "
                    f"{missing_columns}."
                )
        counts = await table_counts(connection)

        identity_replacements: dict[str, str] = {}
        if competition:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT id, name, original_filename FROM resume ORDER BY id")
                for row_id, name, filename in await cursor.fetchall():
                    identity_replacements.setdefault(str(name or ""), f"演示候选人{int(row_id):02d}")
                    extension = Path(str(filename or "resume.txt")).suffix or ".txt"
                    identity_replacements.setdefault(
                        str(filename or ""), f"candidate-{int(row_id):02d}{extension.lower()}"
                    )
                for table in ("enterprise_talent", "enterprise_employee_directory"):
                    await cursor.execute(f"SELECT id, name FROM `{table}` ORDER BY id")
                    for row_id, name in await cursor.fetchall():
                        identity_replacements.setdefault(
                            str(name or ""), f"演示人才{int(row_id):02d}"
                        )
            identity_replacements.pop("", None)

        async with connection.cursor() as cursor:
            await cursor.execute(
                "SELECT version, embedding_provider, embedding_model, "
                "embedding_dimension, entry_count FROM retrieval_index_version "
                "WHERE backend = 'chroma' AND status = 'ready' ORDER BY created_at"
            )
            chroma_indexes = [
                {
                    "version": str(row[0]),
                    "embedding_provider": str(row[1]),
                    "embedding_model": str(row[2]),
                    "embedding_dimension": int(row[3]),
                    "entry_count": int(row[4]),
                }
                for row in await cursor.fetchall()
            ]
            await cursor.execute(
                "SELECT node_count, edge_count FROM graph_snapshot "
                "WHERE status = 'succeeded' "
                "ORDER BY completed_at DESC, created_at DESC LIMIT 1"
            )
            graph_row = await cursor.fetchone()

        lines = [
            "-- JieBang complete MySQL data snapshot (schema is managed by Alembic)",
            f"-- Alembic revision: {revision}",
            "-- Generated statements are one-per-line for the Python importer.",
        ]
        table_digests = {table: hashlib.sha256() for table in tables}
        exported_counts = {table: 0 for table in tables}

        async with connection.cursor() as cursor:
            for table in reversed(tables):
                lines.append(f"DELETE FROM {quote_identifier(table)};")

            for table in tables:
                await cursor.execute(f"SHOW COLUMNS FROM {quote_identifier(table)}")
                columns = [str(row[0]) for row in await cursor.fetchall()]
                await cursor.execute(
                    f"SHOW KEYS FROM {quote_identifier(table)} WHERE Key_name = 'PRIMARY'"
                )
                key_rows = sorted(await cursor.fetchall(), key=lambda row: int(row[3]))
                primary_keys = [str(row[4]) for row in key_rows]
                if not primary_keys:
                    raise RuntimeError(
                        f"Table {table!r} has no primary key; deterministic export is unsafe."
                    )
                order_clause = " ORDER BY " + ", ".join(
                    quote_identifier(key) for key in primary_keys
                )
                await cursor.execute(f"SELECT * FROM {quote_identifier(table)}{order_clause}")
                rows = list(await cursor.fetchall())
                if len(rows) != counts[table]:
                    raise RuntimeError(
                        f"Consistent snapshot count changed for {table}: "
                        f"count={counts[table]}, selected={len(rows)}."
                    )
                column_sql = ", ".join(quote_identifier(column) for column in columns)
                if competition:
                    rows = [
                        sanitize_competition_row(
                            table, columns, row, identity_replacements
                        )
                        for row in rows
                    ]
                for start in range(0, len(rows), BATCH_SIZE):
                    batch = rows[start : start + BATCH_SIZE]
                    values_sql = [
                        "("
                        + ", ".join(sql_literal(connection, value) for value in row)
                        + ")"
                        for row in batch
                    ]
                    line = (
                        f"INSERT INTO {quote_identifier(table)} ({column_sql}) VALUES "
                        + ", ".join(values_sql)
                        + ";"
                    )
                    lines.append(line)
                    table_digests[table].update((line + "\n").encode("utf-8"))
                    exported_counts[table] += len(batch)

        final_revision = await current_alembic_revision(connection)
        final_tables = await list_base_tables(connection)
        if final_revision != revision or final_tables != tables or exported_counts != counts:
            raise RuntimeError("Source schema or row accounting changed during snapshot export.")

        snapshot_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        options = mysql_connection_options()
        manifest = {
            "format_version": PACKAGE_FORMAT_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_database": options["db"],
            "alembic_revision": revision,
            "schema_source": "alembic",
            "snapshot_profile": (
                "competition-sanitized-v1" if competition else "complete-internal"
            ),
            "data_file": snapshot_path.name,
            "table_count": len(tables),
            "table_names_sha256": sha256_text("\n".join(tables) + "\n"),
            "table_counts": counts,
            "table_sha256": {
                table: table_digests[table].hexdigest() for table in tables
            },
            "total_rows": sum(counts.values()),
            "chroma": {
                "materialization": "restore_from_mysql_precomputed_vectors",
                "indexes": chroma_indexes,
                "collection_count": len(chroma_indexes),
                "vector_count": sum(index["entry_count"] for index in chroma_indexes),
            },
            "neo4j": {
                "materialization": "rebuild_namespace_from_mysql",
                "latest_snapshot": (
                    {"node_count": int(graph_row[0]), "edge_count": int(graph_row[1])}
                    if graph_row
                    else None
                ),
            },
            "size_bytes": snapshot_path.stat().st_size,
            "sha256": sha256_file(snapshot_path),
        }
        _write_json(manifest_path, manifest)
        validate_snapshot_package(
            snapshot_path,
            manifest_path,
            None,
            expected_revision=expected_revision,
        )
        _write_verification_summary(snapshot_path, manifest_path, verification_path, manifest)
        validate_snapshot_package(
            snapshot_path,
            manifest_path,
            verification_path,
            expected_revision=expected_revision,
        )
        return manifest
    finally:
        try:
            await connection.rollback()
        finally:
            connection.close()


def publish_staged_package(staging_dir: Path) -> None:
    """Publish validated files with the manifest last, so readers fail closed."""
    staged_snapshot = staging_dir / SNAPSHOT_PATH.name
    staged_manifest = staging_dir / MANIFEST_PATH.name
    staged_verification = staging_dir / VERIFICATION_PATH.name
    expected_revision = repository_alembic_head()
    validate_snapshot_package(
        staged_snapshot,
        staged_manifest,
        staged_verification,
        expected_revision=expected_revision,
    )
    os.replace(staged_snapshot, SNAPSHOT_PATH)
    os.replace(staged_verification, VERIFICATION_PATH)
    os.replace(staged_manifest, MANIFEST_PATH)
    validate_snapshot_package(expected_revision=expected_revision)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument(
        "--publish",
        action="store_true",
        help="Atomically replace the checked-in package after staged validation.",
    )
    destination.add_argument(
        "--output-dir",
        type=Path,
        help="Write a non-canonical package to a new/empty directory.",
    )
    parser.add_argument(
        "--expected-revision",
        help="Required source revision (defaults to the repository's unique Alembic head).",
    )
    parser.add_argument(
        "--competition",
        action="store_true",
        help="Pseudonymize development identities in the exported SQL package.",
    )
    return parser.parse_args()


async def _main() -> None:
    args = parse_args()
    expected_revision = args.expected_revision or repository_alembic_head()
    if args.publish:
        with tempfile.TemporaryDirectory(
            prefix="mysql-snapshot-stage-", dir=SNAPSHOT_PATH.parent
        ) as temp:
            staging_dir = Path(temp)
            manifest = await export_snapshot(
                staging_dir, expected_revision=expected_revision, competition=args.competition
            )
            publish_staged_package(staging_dir)
    else:
        manifest = await export_snapshot(
            args.output_dir.resolve(), expected_revision=expected_revision,
            competition=args.competition,
        )
    print(
        f"Exported and verified {manifest['total_rows']} rows from "
        f"{manifest['table_count']} tables at {manifest['alembic_revision']}."
    )
    print(f"SHA-256: {manifest['sha256']}")


if __name__ == "__main__":
    asyncio.run(_main())
