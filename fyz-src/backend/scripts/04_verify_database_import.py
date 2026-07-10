"""Step 4: verify MySQL snapshot integrity and the rebuilt Neo4j counts."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db_transfer_common import (  # noqa: E402
    connect_mysql,
    current_alembic_revision,
    load_manifest,
    table_counts,
)
from app.core.database import async_session, engine  # noqa: E402
from app.core.neo4j import close_driver, health_detail  # noqa: E402
from app.models import GraphSnapshot  # noqa: E402
from app.repositories.graph_repository import Neo4jGraphRepository  # noqa: E402

DERIVED_TABLES = {
    "graph_enrichment_candidate",
    "graph_snapshot",
    "graph_sync_batch",
    "standard_job",
    "standard_job_source",
}


async def verify() -> None:
    try:
        manifest = load_manifest()
        connection = await connect_mysql()
        try:
            revision = await current_alembic_revision(connection)
            if revision != manifest["alembic_revision"]:
                raise RuntimeError(
                    f"Alembic revision mismatch: expected={manifest['alembic_revision']}, actual={revision}"
                )
            actual = await table_counts(connection)
        finally:
            connection.close()

        expected = {str(key): int(value) for key, value in manifest["table_counts"].items()}
        errors: list[str] = []
        for table, expected_count in expected.items():
            actual_count = actual.get(table)
            if actual_count is None:
                errors.append(f"missing table {table}")
            elif table in DERIVED_TABLES and actual_count < expected_count:
                errors.append(f"{table}: expected at least {expected_count}, got {actual_count}")
            elif table not in DERIVED_TABLES and actual_count != expected_count:
                errors.append(f"{table}: expected {expected_count}, got {actual_count}")
        unexpected = sorted(set(actual) - set(expected))
        if unexpected:
            errors.append(f"unexpected tables: {unexpected}")
        if errors:
            raise RuntimeError("MySQL verification failed: " + "; ".join(errors))

        detail = await asyncio.to_thread(health_detail)
        if not detail.startswith("OK"):
            raise RuntimeError(f"Neo4j verification failed: {detail}")
        counts = await asyncio.to_thread(Neo4jGraphRepository().counts)
        async with async_session() as session:
            snapshot = (
                await session.execute(
                    select(GraphSnapshot)
                    .where(GraphSnapshot.status == "succeeded")
                    .order_by(GraphSnapshot.completed_at.desc(), GraphSnapshot.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
        if snapshot is None:
            raise RuntimeError("No succeeded graph snapshot exists in MySQL.")
        if counts["nodes"] != snapshot.node_count or counts["edges"] != snapshot.edge_count:
            raise RuntimeError(
                "Neo4j counts do not match the latest MySQL graph snapshot: "
                f"neo4j={counts}, snapshot={{'nodes': {snapshot.node_count}, "
                f"'edges': {snapshot.edge_count}}}"
            )
        if counts["nodes"] <= 0 or counts["edges"] <= 0:
            raise RuntimeError(f"Neo4j graph is unexpectedly empty: {counts}")

        print(
            f"[4/4] Verification passed: {len(actual)} MySQL tables, "
            f"{sum(actual.values())} current rows, {counts['nodes']} Neo4j nodes, "
            f"{counts['edges']} Neo4j relationships."
        )
    finally:
        close_driver()
        await engine.dispose()


def main() -> None:
    asyncio.run(verify())


if __name__ == "__main__":
    main()
