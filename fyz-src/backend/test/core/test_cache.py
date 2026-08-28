from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

from app.core import config
from app.core.cache import AsyncJsonCache, stable_query_key


class FakeRedis:
    def __init__(self, *, fail: bool = False) -> None:
        self.values: dict[str, str] = {}
        self.expiries: dict[str, int] = {}
        self.fail = fail
        self.closed = False

    def _check(self) -> None:
        if self.fail:
            raise ConnectionError("redis unavailable")

    async def ping(self) -> bool:
        self._check()
        return True

    async def get(self, key: str) -> str | None:
        self._check()
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> bool:
        self._check()
        self.values[key] = value
        self.expiries[key] = ex
        return True

    async def delete(self, *keys: str) -> int:
        self._check()
        deleted = 0
        for key in keys:
            deleted += int(key in self.values)
            self.values.pop(key, None)
        return deleted

    async def incr(self, key: str) -> int:
        self._check()
        value = int(self.values.get(key, "0")) + 1
        self.values[key] = str(value)
        return value

    async def eval(
        self, _script: str, _numkeys: int, key: str, payload: str, ttl: int
    ) -> int:
        self._check()
        incoming = json.loads(payload)
        current = json.loads(self.values[key]) if key in self.values else None
        if current:
            current_meta = current.get("_cache_meta") or {}
            incoming_meta = incoming.get("_cache_meta") or {}
            if current_meta.get("terminal") and not incoming_meta.get("terminal"):
                return 0
            if (
                not current_meta.get("terminal")
                and not incoming_meta.get("terminal")
                and current_meta.get("progress", -1) > incoming_meta.get("progress", -1)
            ):
                return 0
        self.values[key] = payload
        self.expiries[key] = int(ttl)
        return 1

    async def aclose(self) -> None:
        self.closed = True


class CacheState(str, Enum):
    ready = "ready"


class CachePayload(BaseModel):
    state: CacheState
    generated_at: datetime


async def test_json_round_trip_supports_pydantic_datetime_and_enum():
    redis = FakeRedis()
    cache = AsyncJsonCache(
        "redis://unused/3", client=redis, key_prefix="test", default_ttl_seconds=42
    )
    payload = CachePayload(
        state=CacheState.ready,
        generated_at=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
    )

    assert await cache.set_json("payload", payload) is True
    assert redis.expiries["test:payload"] == 42
    assert await cache.get_json("payload") == {
        "generated_at": "2026-08-10T12:00:00Z",
        "state": "ready",
    }


async def test_corrupt_json_is_a_cache_miss_and_is_removed():
    redis = FakeRedis()
    redis.values["test:broken"] = "not-json"
    cache = AsyncJsonCache("redis://unused/3", client=redis, key_prefix="test")

    assert await cache.get_json("broken") is None
    assert "test:broken" not in redis.values


async def test_redis_failure_is_fail_open():
    redis = FakeRedis(fail=True)
    cache = AsyncJsonCache("redis://unused/3", client=redis, key_prefix="test")

    assert await cache.start() is False
    assert await cache.get_json("key") is None
    assert await cache.set_json("key", {"value": 1}) is False
    assert await cache.delete("key") is False
    assert await cache.get_generation("analysis") == 0
    assert await cache.bump_generation("analysis") is None
    assert cache.available is False


async def test_recovery_invalidates_query_generations_before_serving_cache():
    redis = FakeRedis()
    redis.values.update(
        {
            "test:generation:analysis": "4",
            "test:generation:dashboard": "7",
            "test:generation:graph": "2",
        }
    )
    cache = AsyncJsonCache("redis://unused/3", client=redis, key_prefix="test")
    cache._mark_unavailable()
    cache._retry_after = 0

    assert await cache.get_generation("analysis") == 5
    assert redis.values["test:generation:dashboard"] == "8"
    assert redis.values["test:generation:graph"] == "3"
    assert cache.available is True


async def test_generation_keys_use_prefix_and_invalidate_without_scan():
    redis = FakeRedis()
    cache = AsyncJsonCache("redis://unused/3", client=redis, key_prefix="test")

    assert await cache.get_generation("analysis") == 0
    assert await cache.versioned_key("analysis", "overview") == "analysis:g0:overview"
    assert await cache.bump_generation("analysis") == 1
    assert redis.values["test:generation:analysis"] == "1"
    assert await cache.versioned_key("analysis", "overview") == "analysis:g1:overview"


async def test_monotonic_json_atomically_rejects_progress_and_terminal_rollback():
    redis = FakeRedis()
    cache = AsyncJsonCache("redis://unused/3", client=redis, key_prefix="test")

    running_80 = {"_cache_meta": {"terminal": False, "progress": 80}}
    running_40 = {"_cache_meta": {"terminal": False, "progress": 40}}
    succeeded = {"_cache_meta": {"terminal": True, "progress": 100}}

    assert await cache.set_monotonic_json("task:1", running_80, ttl_seconds=15)
    assert not await cache.set_monotonic_json("task:1", running_40, ttl_seconds=15)
    assert await cache.set_monotonic_json("task:1", succeeded, ttl_seconds=86400)
    assert not await cache.set_monotonic_json("task:1", running_80, ttl_seconds=15)
    assert json.loads(redis.values["test:task:1"])["_cache_meta"]["terminal"] is True


def test_stable_query_key_is_order_independent_and_bounded():
    first = stable_query_key(
        "graph:overview", {"page": 1, "filters": {"city": "北京", "level": 3}}
    )
    second = stable_query_key(
        "graph:overview", filters={"level": 3, "city": "北京"}, page=1
    )

    assert first == second
    assert first.startswith("graph:overview:")
    assert len(first) < 64


async def test_disabled_cache_never_uses_client_for_operations():
    redis = FakeRedis(fail=True)
    cache = AsyncJsonCache(
        "redis://unused/3", enabled=False, client=redis, key_prefix="test"
    )

    assert await cache.start() is False
    assert await cache.get_json("key") is None
    assert await cache.set_json("key", {"value": 1}) is False
    await cache.close()
    assert redis.closed is True


async def test_close_releases_client():
    redis = FakeRedis()
    cache = AsyncJsonCache("redis://unused/3", client=redis)

    assert await cache.start() is True
    await cache.close()

    assert redis.closed is True
    assert cache.available is None


async def test_client_is_created_with_short_timeouts(monkeypatch):
    redis = FakeRedis()
    captured: dict = {}

    def from_url(url: str, **kwargs):
        captured.update({"url": url, **kwargs})
        return redis

    monkeypatch.setattr("app.core.cache.Redis.from_url", from_url)
    cache = AsyncJsonCache(
        "redis://cache/0",
        connect_timeout_seconds=0.25,
        socket_timeout_seconds=0.75,
    )

    assert await cache.start() is True
    assert captured["url"] == "redis://cache/0"
    assert captured["decode_responses"] is True
    assert captured["socket_connect_timeout"] == 0.25
    assert captured["socket_timeout"] == 0.75


def test_testing_configuration_disables_external_cache_by_default():
    assert config.TESTING is True
    assert config.CACHE_ENABLED is False
