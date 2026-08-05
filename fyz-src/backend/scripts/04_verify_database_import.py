"""Step 5: verify MySQL, Chroma and rebuilt Neo4j integrity."""

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
from app.core.config import CHROMA_MODE, CHROMA_PERSIST_PATH  # noqa: E402
from app.core.neo4j import close_driver, health_detail  # noqa: E402
from app.models import GraphSnapshot, RetrievalIndexVersion  # noqa: E402
from app.providers.vector_store import ChromaVectorStore  # noqa: E402
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

        if CHROMA_MODE != "persistent":
            raise RuntimeError(
                "Chroma verification requires CHROMA_MODE=persistent."
            )
        async with async_session() as session:
            chroma_indexes = list(
                (
                    await session.execute(
                        select(RetrievalIndexVersion).where(
                            RetrievalIndexVersion.backend == "chroma",
                            RetrievalIndexVersion.status == "ready",
                        )
                    )
                ).scalars()
            )
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise RuntimeError("chromadb is not installed") from exc
        client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        chroma_vectors = 0
        for index in chroma_indexes:
            collection_name = ChromaVectorStore.collection_name(index.version)
            try:
                collection = client.get_collection(name=collection_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Missing Chroma collection {collection_name} for "
                    f"index {index.version}"
                ) from exc
            actual_count = int(collection.count())
            if actual_count != index.entry_count:
                raise RuntimeError(
                    f"Chroma count mismatch for {index.version}: "
                    f"expected={index.entry_count}, actual={actual_count}"
                )
            chroma_vectors += actual_count

        print(
            f"[5/5] Verification passed: {len(actual)} MySQL tables, "
            f"{sum(actual.values())} current rows, {counts['nodes']} Neo4j nodes, "
            f"{counts['edges']} Neo4j relationships, "
            f"{len(chroma_indexes)} Chroma collections and "
            f"{chroma_vectors} vectors."
        )
    finally:
        close_driver()
        await engine.dispose()


def main() -> None:
    asyncio.run(verify())


if __name__ == "__main__":
    main()
