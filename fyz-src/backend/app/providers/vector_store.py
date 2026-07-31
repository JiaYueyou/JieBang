"""Rebuildable vector-store adapters; MySQL remains the authority."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any, Protocol

from app.core.config import CHROMA_MODE, CHROMA_PERSIST_PATH


class VectorStore(Protocol):
    async def sync_index(
        self,
        *,
        index_version: str,
        dimension: int,
        records: list[dict[str, Any]],
    ) -> str: ...

    async def query(
        self,
        *,
        index_version: str,
        embedding: list[float],
        limit: int,
        where: dict[str, Any] | None = None,
    ) -> dict[str, float]: ...


_CHROMA_CLIENTS: dict[tuple[str, str], Any] = {}


class ChromaVectorStore:
    """Chroma adapter using pre-computed embeddings and cosine distance."""

    def __init__(
        self,
        *,
        mode: str = CHROMA_MODE,
        persist_path: str | Path = CHROMA_PERSIST_PATH,
        client: Any | None = None,
    ) -> None:
        if mode not in {"ephemeral", "persistent"}:
            raise ValueError("CHROMA_MODE must be ephemeral or persistent")
        self.mode = mode
        self.persist_path = str(Path(persist_path).resolve())
        self._client = client
        self._collections: dict[str, Any] = {}
        self._collection_counts: dict[str, int] = {}

    @staticmethod
    def collection_name(index_version: str) -> str:
        digest = hashlib.sha256(index_version.encode("utf-8")).hexdigest()[:20]
        return f"jiebang-evidence-{digest}"

    def _client_or_create(self) -> Any:
        if self._client is not None:
            return self._client
        cache_key = (self.mode, self.persist_path)
        if cache_key in _CHROMA_CLIENTS:
            return _CHROMA_CLIENTS[cache_key]
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise RuntimeError(
                "chromadb is not installed; install backend requirements"
            ) from exc
        settings = Settings(anonymized_telemetry=False)
        if self.mode == "ephemeral":
            client = chromadb.EphemeralClient(settings=settings)
        else:
            Path(self.persist_path).mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(
                path=self.persist_path,
                settings=settings,
            )
        _CHROMA_CLIENTS[cache_key] = client
        return client

    async def sync_index(
        self,
        *,
        index_version: str,
        dimension: int,
        records: list[dict[str, Any]],
    ) -> str:
        return await asyncio.to_thread(
            self._sync_index,
            index_version,
            dimension,
            records,
        )

    def _sync_index(
        self,
        index_version: str,
        dimension: int,
        records: list[dict[str, Any]],
    ) -> str:
        client = self._client_or_create()
        name = self.collection_name(index_version)
        collection = client.get_or_create_collection(
            name=name,
            metadata={
                "namespace": "jiebang",
                "index_version": index_version,
                "dimension": dimension,
            },
            configuration={"hnsw": {"space": "cosine"}},
        )
        if records:
            collection.upsert(
                ids=[record["evidence_id"] for record in records],
                embeddings=[record["embedding"] for record in records],
                documents=[record["document"] for record in records],
                metadatas=[record["metadata"] for record in records],
            )
        self._collections[index_version] = collection
        self._collection_counts[index_version] = len(records)
        return name

    async def query(
        self,
        *,
        index_version: str,
        embedding: list[float],
        limit: int,
        where: dict[str, Any] | None = None,
    ) -> dict[str, float]:
        return await asyncio.to_thread(
            self._query,
            index_version,
            embedding,
            limit,
            where,
        )

    def _query(
        self,
        index_version: str,
        embedding: list[float],
        limit: int,
        where: dict[str, Any] | None,
    ) -> dict[str, float]:
        collection = self._collections.get(index_version)
        if collection is None:
            collection = self._client_or_create().get_collection(
                name=self.collection_name(index_version)
            )
            self._collections[index_version] = collection
        count = self._collection_counts.get(index_version)
        if count is None:
            count = int(collection.count())
            self._collection_counts[index_version] = count
        if count <= 0:
            return {}
        result = collection.query(
            query_embeddings=[embedding],
            n_results=min(limit, count),
            where=where,
            include=["distances"],
        )
        ids = list((result.get("ids") or [[]])[0])
        distances = list((result.get("distances") or [[]])[0])
        return {
            evidence_id: round(
                max(0.0, min(1.0, 1.0 - float(distance))),
                6,
            )
            for evidence_id, distance in zip(ids, distances)
        }
