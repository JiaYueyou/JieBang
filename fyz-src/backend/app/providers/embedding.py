"""Embedding providers selected by configuration or persisted index metadata."""

from __future__ import annotations

from typing import Any

from app.core.config import (
    OPENAI_EMBEDDING_API_KEY,
    OPENAI_EMBEDDING_BASE_URL,
    OPENAI_EMBEDDING_BATCH_SIZE,
    OPENAI_EMBEDDING_DIMENSIONS,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_TIMEOUT_SECONDS,
    RETRIEVAL_EMBEDDING_PROVIDER,
)
from app.domain.retrieval import (
    EmbeddingProvider,
    HashEmbeddingProvider,
)


class OpenAIEmbeddingProvider:
    """OpenAI-compatible async embedding client with deterministic dimensions."""

    name = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str = OPENAI_EMBEDDING_API_KEY,
        base_url: str = OPENAI_EMBEDDING_BASE_URL,
        model: str = OPENAI_EMBEDDING_MODEL,
        dimension: int = OPENAI_EMBEDDING_DIMENSIONS,
        batch_size: int = OPENAI_EMBEDDING_BATCH_SIZE,
        timeout_seconds: float = OPENAI_EMBEDDING_TIMEOUT_SECONDS,
        client: Any | None = None,
    ) -> None:
        if dimension <= 0:
            raise ValueError("embedding dimension must be positive")
        if batch_size <= 0:
            raise ValueError("embedding batch size must be positive")
        self.api_key = api_key.strip()
        self.base_url = base_url.strip().rstrip("/")
        self.model = model
        self.dimension = dimension
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self._client = client

    def _client_or_raise(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_EMBEDDING_API_KEY is not configured; "
                "fill it in the local .env before rebuilding the OpenAI index"
            )
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            max_retries=2,
        )
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        normalized = [text.strip() for text in texts]
        if any(not text for text in normalized):
            raise ValueError("embedding input cannot be empty")
        client = self._client_or_raise()
        embeddings: list[list[float]] = []
        for start in range(0, len(normalized), self.batch_size):
            response = await client.embeddings.create(
                input=normalized[start : start + self.batch_size],
                model=self.model,
                dimensions=self.dimension,
                encoding_format="float",
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            batch = [
                [float(value) for value in item.embedding]
                for item in ordered
            ]
            if len(batch) != len(
                normalized[start : start + self.batch_size]
            ):
                raise RuntimeError("embedding response count mismatch")
            if any(len(vector) != self.dimension for vector in batch):
                raise RuntimeError(
                    "embedding response dimension does not match "
                    f"configured dimension {self.dimension}"
                )
            embeddings.extend(batch)
        return embeddings
def build_embedding_provider(
    *,
    provider_name: str | None = None,
    model: str | None = None,
    dimension: int | None = None,
) -> EmbeddingProvider:
    selected = (provider_name or RETRIEVAL_EMBEDDING_PROVIDER).casefold()
    selected_model = model or OPENAI_EMBEDDING_MODEL
    if (
        selected in {"local_hash", "local_deterministic"}
        or selected_model.startswith("signed-token-hash")
    ):
        return HashEmbeddingProvider(
            dimension=dimension or 256,
        )
    if selected in {"openai", "openai_compatible"}:
        return OpenAIEmbeddingProvider(
            model=selected_model,
            dimension=dimension or OPENAI_EMBEDDING_DIMENSIONS,
        )
    raise ValueError(f"Unsupported embedding provider: {selected}")
