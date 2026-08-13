from __future__ import annotations

from app.core.config import CACHE_TASK_TERMINAL_TTL_SECONDS
from app.services import pipeline_status_cache


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[str, dict] = {}
        self.ttls: dict[str, int] = {}
        self.deleted: list[str] = []

    async def set_monotonic_json(self, key: str, value: dict, *, ttl_seconds: int) -> bool:
        self.values[key] = value
        self.ttls[key] = ttl_seconds
        return True

    async def get_json(self, key: str):
        return self.values.get(key)

    async def delete(self, key: str) -> bool:
        self.deleted.append(key)
        self.values.pop(key, None)
        return True


async def test_pipeline_projection_validates_and_uses_terminal_ttl(monkeypatch):
    cache = FakeCache()
    monkeypatch.setattr(pipeline_status_cache, "get_cache", lambda: cache)
    snapshot = {
        "id": "pipeline-1",
        "status": "succeeded",
        "stage": "completed",
        "progress": 100,
        "stage_results": {"graph": "ok"},
    }

    assert await pipeline_status_cache.publish_pipeline_status(snapshot)
    key = "pipeline-status:v1:pipeline-1"
    assert cache.ttls[key] == CACHE_TASK_TERMINAL_TTL_SECONDS
    assert cache.values[key]["_cache_meta"] == {"terminal": True, "progress": 100}
    assert await pipeline_status_cache.get_cached_pipeline_status("pipeline-1") == snapshot


async def test_pipeline_projection_rejects_invalid_payload_and_deletes_bad_cache(monkeypatch):
    cache = FakeCache()
    monkeypatch.setattr(pipeline_status_cache, "get_cache", lambda: cache)

    assert not await pipeline_status_cache.publish_pipeline_status(
        {"id": "bad", "status": "running", "stage": "collect", "progress": 101}
    )

    key = "pipeline-status:v1:bad"
    cache.values[key] = {"pipeline": {"id": "bad", "status": "running"}}
    assert await pipeline_status_cache.get_cached_pipeline_status("bad") is None
    assert cache.deleted == [key]
