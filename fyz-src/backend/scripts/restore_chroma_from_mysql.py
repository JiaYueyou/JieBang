"""Restore persistent Chroma collections from authoritative MySQL vectors.

The checked-in MySQL snapshot already contains the pre-computed embeddings in
``retrieval_index_entry``.  This script materializes those vectors into Chroma
without calling an external embedding API.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import CHROMA_MODE, CHROMA_PERSIST_PATH  # noqa: E402
from app.core.database import async_session, engine  # noqa: E402
from app.domain.retrieval import embedding_checksum  # noqa: E402
from app.models import (  # noqa: E402
    EvidenceChunk,
    RetrievalIndexEntry,
    RetrievalIndexVersion,
)
from app.providers.vector_store import ChromaVectorStore  # noqa: E402

COLLECTION_PREFIX = "jiebang-evidence-"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Restore JieBang Chroma collections from embeddings already stored "
            "in MySQL. No external embedding API is called."
        )
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Required confirmation before replacing JieBang Chroma collections.",
    )
    return parser.parse_args()


async def restore(*, replace: bool) -> None:
    if not replace:
        raise RuntimeError(
            "This operation replaces Chroma collections whose names start with "
            f"{COLLECTION_PREFIX!r}. Re-run with --replace."
        )
    if CHROMA_MODE != "persistent":
        raise RuntimeError(
            "CHROMA_MODE must be 'persistent' for a transferable local index."
        )

    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError as exc:
        raise RuntimeError(
            "chromadb is not installed; install backend requirements first"
        ) from exc

    async with async_session() as session:
        indexes = list(
            (
                await session.execute(
                    select(RetrievalIndexVersion)
                    .where(
                        RetrievalIndexVersion.backend == "chroma",
                        RetrievalIndexVersion.status == "ready",
                    )
                    .order_by(RetrievalIndexVersion.created_at)
                )
            ).scalars()
        )

        payloads: list[tuple[RetrievalIndexVersion, list[dict]]] = []
        for index in indexes:
            rows = (
                await session.execute(
                    select(RetrievalIndexEntry, EvidenceChunk)
                    .join(
                        EvidenceChunk,
                        RetrievalIndexEntry.evidence_id == EvidenceChunk.id,
                    )
                    .where(RetrievalIndexEntry.index_version_id == index.id)
                    .order_by(RetrievalIndexEntry.id)
                )
            ).all()
            records: list[dict] = []
            for entry, chunk in rows:
                if len(entry.embedding) != index.embedding_dimension:
                    raise RuntimeError(
                        f"Vector dimension mismatch for {index.version}/"
                        f"{entry.evidence_id}: expected {index.embedding_dimension}, "
                        f"got {len(entry.embedding)}"
                    )
                if embedding_checksum(entry.embedding) != entry.embedding_checksum:
                    raise RuntimeError(
                        f"Vector checksum mismatch for {index.version}/"
                        f"{entry.evidence_id}"
                    )
                records.append(
                    {
                        "evidence_id": entry.evidence_id,
                        "embedding": entry.embedding,
                        "document": entry.lexical_text,
                        "metadata": {
                            "namespace": "jiebang",
                            "index_version": index.version,
                            "standard_job_id": chunk.standard_job_id,
                            "skill_id": chunk.skill_id,
                            "source_platform": chunk.source_platform,
                            "quality_score": float(chunk.quality_score),
                            "verification_status": chunk.verification_status,
                            "posted_at_epoch": (
                                int(chunk.posted_at.timestamp())
                                if chunk.posted_at
                                else 0
                            ),
                            "near_duplicate_group_id": (
                                chunk.near_duplicate_group_id or ""
                            ),
                        },
                    }
                )
            if len(records) != index.entry_count:
                raise RuntimeError(
                    f"MySQL index count mismatch for {index.version}: "
                    f"metadata={index.entry_count}, rows={len(records)}"
                )
            payloads.append((index, records))

    Path(CHROMA_PERSIST_PATH).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=CHROMA_PERSIST_PATH,
        settings=Settings(anonymized_telemetry=False),
    )
    expected_names = {
        ChromaVectorStore.collection_name(index.version)
        for index, _ in payloads
    }
    for collection in client.list_collections():
        if collection.name.startswith(COLLECTION_PREFIX):
            client.delete_collection(collection.name)

    store = ChromaVectorStore(
        mode="persistent",
        persist_path=CHROMA_PERSIST_PATH,
        client=client,
    )
    restored_vectors = 0
    for index, records in payloads:
        name = await store.sync_index(
            index_version=index.version,
            dimension=index.embedding_dimension,
            records=records,
        )
        actual_count = int(client.get_collection(name=name).count())
        if name not in expected_names or actual_count != len(records):
            raise RuntimeError(
                f"Chroma verification failed for {name}: "
                f"expected={len(records)}, actual={actual_count}"
            )
        restored_vectors += actual_count
        print(
            f"[3/5] Restored {name}: {actual_count} vectors, "
            f"dimension={index.embedding_dimension}."
        )
    print(
        f"[3/5] Chroma restore completed: {len(payloads)} collections, "
        f"{restored_vectors} vectors, path={CHROMA_PERSIST_PATH}."
    )


def main() -> None:
    args = parse_args()

    async def run() -> None:
        try:
            await restore(replace=args.replace)
        finally:
            await engine.dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()
