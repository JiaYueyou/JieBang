from types import SimpleNamespace

import pytest

from app.providers.embedding import OpenAIEmbeddingProvider


class _FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    index=index,
                    embedding=[float(index + 1)] * kwargs["dimensions"],
                )
                for index, _ in enumerate(kwargs["input"])
            ]
        )


async def test_openai_embedding_provider_batches_and_preserves_order():
    embeddings = _FakeEmbeddings()
    client = SimpleNamespace(embeddings=embeddings)
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        base_url="https://api.openai-proxy.org",
        model="text-embedding-3-large",
        dimension=4,
        batch_size=2,
        client=client,
    )

    result = await provider.embed_texts(["一", "二", "三"])

    assert result == [
        [1.0, 1.0, 1.0, 1.0],
        [2.0, 2.0, 2.0, 2.0],
        [1.0, 1.0, 1.0, 1.0],
    ]
    assert len(embeddings.calls) == 2
    assert provider.base_url == "https://api.openai-proxy.org"
    assert all(
        call["model"] == "text-embedding-3-large"
        and call["dimensions"] == 4
        and call["encoding_format"] == "float"
        for call in embeddings.calls
    )


def test_openai_embedding_provider_preserves_explicit_api_path():
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        base_url="https://example.com/openai/v1/",
    )

    assert provider.base_url == "https://example.com/openai/v1"


async def test_openai_embedding_provider_requires_local_secret():
    provider = OpenAIEmbeddingProvider(
        api_key="",
        base_url="https://api.openai-proxy.org",
    )

    with pytest.raises(
        RuntimeError,
        match="OPENAI_EMBEDDING_API_KEY",
    ):
        await provider.embed_texts(["需要向量化的文本"])
