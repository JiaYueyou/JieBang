"""Step 2: replace target MySQL data with the checked-in complete snapshot."""

from __future__ import annotations

import argparse
import asyncio

from db_transfer_common import (
    SNAPSHOT_PATH,
    connect_mysql,
    current_alembic_revision,
    load_manifest,
    table_counts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import every MySQL table from mysql_snapshot.sql."
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Required confirmation because existing rows will be deleted.",
    )
    return parser.parse_args()


async def import_snapshot(*, replace: bool) -> None:
    if not replace:
        raise RuntimeError(
            "This operation replaces all rows in the configured database. "
            "Re-run with --replace after checking DB_HOST/DB_NAME in .env."
        )

    manifest = load_manifest()
    connection = await connect_mysql()
    try:
        current_revision = await current_alembic_revision(connection)
        expected_revision = str(manifest["alembic_revision"])
        if current_revision != expected_revision:
            raise RuntimeError(
                "Schema revision mismatch: "
                f"database={current_revision!r}, snapshot={expected_revision!r}. "
                "Run 01_prepare_mysql_schema.py with the same source checkout first."
            )

        statements = [
            line.strip()
            for line in SNAPSHOT_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("--")
        ]
        print(f"[2/4] Importing {len(statements)} snapshot statements...")
        async with connection.cursor() as cursor:
            await cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                for statement in statements:
                    await cursor.execute(statement)
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise
            finally:
                await cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        actual_counts = await table_counts(connection)
        expected_counts = {
            str(table): int(count)
            for table, count in manifest["table_counts"].items()
        }
        if actual_counts != expected_counts:
            raise RuntimeError(
                f"Imported row counts differ from manifest: expected={expected_counts}, "
                f"actual={actual_counts}"
            )
        print(
            f"[2/4] Imported {sum(actual_counts.values())} rows "
            f"across {len(actual_counts)} MySQL tables."
        )
    finally:
        connection.close()


def main() -> None:
    args = parse_args()
    asyncio.run(import_snapshot(replace=args.replace))


if __name__ == "__main__":
    main()
