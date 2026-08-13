from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from app.services import query_cache


class ExampleResult(BaseModel):
    name: str
    count: int


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.generations: dict[str, int] = {}
        self.set_calls: list[tuple[str, object, int | None]] = []

    async def get_generation(self, namespace: str) -> int:
        return self.generations.get(namespace, 0)

    async def bump_generation(self, namespace: str) -> int:
        value = self.generations.get(namespace, 0) + 1
        self.generations[namespace] = value
        return value

    async def get_json(self, key: str):
        return self.values.get(key)

    async def set_json(
        self, key: str, value: object, *, ttl_seconds: int | None = None
    ) -> bool:
        self.values[key] = value
        self.set_calls.append((key, value, ttl_seconds))
        return True


@pytest.fixture
def fake_cache(monkeypatch) -> FakeCache:
    cache = FakeCache()
    monkeypatch.setattr(query_cache, "get_cache", lambda: cache)
    return cache


@pytest.mark.asyncio
async def test_model_cache_hit_restores_pydantic_type(fake_cache: FakeCache):
    loader = AsyncMock(return_value=ExampleResult(name="Python", count=3))
    options = dict(
        generation_namespace="query:test",
        operation="model",
        params={"page": 1},
        ttl_seconds=60,
        model_type=ExampleResult,
        loader=loader,
    )

    first = await query_cache.cached_model_query(**options)
    second = await query_cache.cached_model_query(**options)

    assert isinstance(first, ExampleResult)
    assert isinstance(second, ExampleResult)
    assert second == first
    assert loader.await_count == 1
    assert fake_cache.set_calls[0][2] == 60


@pytest.mark.asyncio
async def test_generation_bump_makes_previous_entry_unreachable(
    fake_cache: FakeCache,
):
    loader = AsyncMock(
        side_effect=[
            ExampleResult(name="before", count=1),
            ExampleResult(name="after", count=2),
        ]
    )
    options = dict(
        generation_namespace=query_cache.ANALYSIS_CACHE_NAMESPACE,
        operation="overview",
        params={"window": "3m"},
        ttl_seconds=60,
        model_type=ExampleResult,
        loader=loader,
    )

    before = await query_cache.cached_model_query(**options)
    await query_cache.bump_analysis_generation()
    after = await query_cache.cached_model_query(**options)

    assert before.name == "before"
    assert after.name == "after"
    assert loader.await_count == 2
    assert len(fake_cache.values) == 2


@pytest.mark.asyncio
async def test_query_parameters_keep_user_results_isolated(fake_cache: FakeCache):
    loader_one = AsyncMock(return_value={"user": 1})
    loader_two = AsyncMock(return_value={"user": 2})

    one = await query_cache.cached_dict_query(
        generation_namespace=query_cache.DASHBOARD_CACHE_NAMESPACE,
        operation="overview",
        params={"user_id": 1, "page": 1},
        ttl_seconds=30,
        loader=loader_one,
    )
    two = await query_cache.cached_dict_query(
        generation_namespace=query_cache.DASHBOARD_CACHE_NAMESPACE,
        operation="overview",
        params={"user_id": 2, "page": 1},
        ttl_seconds=30,
        loader=loader_two,
    )

    assert one == {"user": 1}
    assert two == {"user": 2}
    assert len(fake_cache.values) == 2


@pytest.mark.asyncio
async def test_large_result_is_not_written(monkeypatch, fake_cache: FakeCache):
    monkeypatch.setattr(query_cache, "MAX_QUERY_CACHE_BYTES", 32)

    result = await query_cache.cached_dict_query(
        generation_namespace="query:test",
        operation="large",
        params={},
        ttl_seconds=30,
        loader=AsyncMock(return_value={"body": "x" * 100}),
    )

    assert result["body"] == "x" * 100
    assert fake_cache.set_calls == []


@pytest.mark.asyncio
async def test_force_refresh_replaces_cached_value(fake_cache: FakeCache):
    loader = AsyncMock(
        side_effect=[{"value": "old"}, {"value": "fresh"}]
    )
    options = dict(
        generation_namespace="query:test",
        operation="warm",
        params={},
        ttl_seconds=30,
        loader=loader,
    )

    assert await query_cache.cached_dict_query(**options) == {"value": "old"}
    assert await query_cache.cached_dict_query(
        **options, force_refresh=True
    ) == {"value": "fresh"}
    assert loader.await_count == 2
