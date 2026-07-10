"""Maintainer tool: refresh the portable data-only MySQL snapshot.

This file is intentionally not numbered because recipients do not run it.
Run it on the source machine whenever the shared database data changes.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from db_transfer_common import (
    MANIFEST_PATH,
    SNAPSHOT_PATH,
    connect_mysql,
    current_alembic_revision,
    list_base_tables,
    mysql_connection_options,
    quote_identifier,
    sha256_file,
    table_counts,
)

BATCH_SIZE = 100


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
        return connection.escape(value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat())
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"0x{bytes(value).hex()}"
    return connection.escape(str(value))


async def export_snapshot() -> None:
    connection = await connect_mysql()
    try:
        revision = await current_alembic_revision(connection)
        if not revision:
            raise RuntimeError("The source database has no Alembic revision.")
        tables = await list_base_tables(connection)
        counts = await table_counts(connection)
        lines = [
            "-- JieBang complete MySQL data snapshot (schema is managed by Alembic)",
            f"-- Alembic revision: {revision}",
            "-- Generated statements are one-per-line for the Python importer.",
        ]

        async with connection.cursor() as cursor:
            for table in reversed(tables):
                lines.append(f"DELETE FROM {quote_identifier(table)};")

            for table in tables:
                await cursor.execute(f"SHOW COLUMNS FROM {quote_identifier(table)}")
                columns = [str(row[0]) for row in await cursor.fetchall()]
                await cursor.execute(
                    f"SHOW KEYS FROM {quote_identifier(table)} WHERE Key_name = 'PRIMARY'"
                )
                primary_keys = [str(row[4]) for row in await cursor.fetchall()]
                order_clause = (
                    " ORDER BY " + ", ".join(quote_identifier(key) for key in primary_keys)
                    if primary_keys
                    else ""
                )
                await cursor.execute(
                    f"SELECT * FROM {quote_identifier(table)}{order_clause}"
                )
                rows = list(await cursor.fetchall())
                column_sql = ", ".join(quote_identifier(column) for column in columns)
                for start in range(0, len(rows), BATCH_SIZE):
                    values_sql = []
                    for row in rows[start : start + BATCH_SIZE]:
                        values_sql.append(
                            "(" + ", ".join(sql_literal(connection, value) for value in row) + ")"
                        )
                    lines.append(
                        f"INSERT INTO {quote_identifier(table)} ({column_sql}) VALUES "
                        + ", ".join(values_sql)
                        + ";"
                    )

        SNAPSHOT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        options = mysql_connection_options()
        manifest = {
            "format_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_database": options["db"],
            "alembic_revision": revision,
            "table_counts": counts,
            "total_rows": sum(counts.values()),
            "sha256": sha256_file(SNAPSHOT_PATH),
        }
        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(
            f"Exported {manifest['total_rows']} rows from {len(tables)} tables to "
            f"{SNAPSHOT_PATH.name}."
        )
        print(f"SHA-256: {manifest['sha256']}")
    finally:
        connection.close()


if __name__ == "__main__":
    asyncio.run(export_snapshot())
