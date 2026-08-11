"""Redis task-status projection tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.exceptions import ResourceNotFoundError
from app.models import AsyncTask
from app.services import task_status_cache
from app.services.task_service import TaskService


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[str, dict] = {}
        self.ttls: dict[str, int | None] = {}
        self.generations: list[str] = []

    async def get_json(self, key: str):
        return self.values.get(key)

    async def set_json(self, key: str, value, *, ttl_seconds=None) -> bool:
        self.values[key] = value
        self.ttls[key] = ttl_seconds
        return True

    async def delete(self, *keys: str) -> bool:
        for key in keys:
            self.values.pop(key, None)
        return True

    async def bump_generation(self, namespace: str) -> int:
        self.generations.append(namespace)
        return len(self.generations)


def make_task(*, status: str = "running", progress: int = 25) -> AsyncTask:
    now = datetime.now(timezone.utc)
    return AsyncTask(
        id="task-1",
        task_type="job_data_import",
        status=status,
        progress=progress,
        request_data={"files": ["private-input.json"], "secret": "not-for-cache"},
        result={"imported": 3} if status == "succeeded" else None,
        created_by=7,
        created_at=now,
        started_at=now,
        finished_at=now if status == "succeeded" else None,
    )


@pytest.mark.asyncio
async def test_task_projection_excludes_request_data_and_uses_status_ttl(monkeypatch):
    cache = FakeCache()
    monkeypatch.setattr(task_status_cache, "get_cache", lambda: cache)

    task = make_task()
    assert await task_status_cache.publish_task_status(task) is True

    key = "task-status:v1:task-1"
    assert "request_data" not in cache.values[key]
    assert "secret" not in str(cache.values[key])
    assert cache.ttls[key] == task_status_cache.ACTIVE_TASK_TTL_SECONDS

    task.status = "succeeded"
    task.progress = 100
    task.result = {"imported": 3}
    task.finished_at = datetime.now(timezone.utc)
    assert await task_status_cache.publish_task_status(task) is True
    assert cache.ttls[key] == task_status_cache.TERMINAL_TASK_TTL_SECONDS


@pytest.mark.asyncio
async def test_terminal_projection_cannot_regress_to_running(monkeypatch):
    cache = FakeCache()
    monkeypatch.setattr(task_status_cache, "get_cache", lambda: cache)
    task = make_task(status="succeeded", progress=100)
    await task_status_cache.publish_task_status(task)

    task.status = "running"
    task.progress = 50
    task.finished_at = None
    assert await task_status_cache.publish_task_status(task) is False
    assert cache.values["task-status:v1:task-1"]["task"]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_cached_task_status_validates_and_returns_owner(monkeypatch):
    cache = FakeCache()
    monkeypatch.setattr(task_status_cache, "get_cache", lambda: cache)
    await task_status_cache.publish_task_status(make_task())

    cached = await task_status_cache.get_cached_task_status("task-1")
    assert cached is not None
    response, owner = cached
    assert response.task_id == "task-1"
    assert owner == 7


@pytest.mark.asyncio
async def test_task_service_enforces_owner_on_cache_hit(monkeypatch):
    response = TaskService.to_response(make_task())

    async def cached(_task_id: str):
        return response, 7

    monkeypatch.setattr("app.services.task_service.get_cached_task_status", cached)
    service = TaskService(object())

    assert (await service.get("task-1", user_id=7)).task_id == "task-1"
    with pytest.raises(ResourceNotFoundError):
        await service.get("task-1", user_id=8)


@pytest.mark.asyncio
async def test_generation_bumps_are_best_effort(monkeypatch):
    cache = FakeCache()
    monkeypatch.setattr(task_status_cache, "get_cache", lambda: cache)
    await task_status_cache.bump_cache_generations("analysis", "dashboard")
    assert cache.generations == ["analysis", "dashboard"]
