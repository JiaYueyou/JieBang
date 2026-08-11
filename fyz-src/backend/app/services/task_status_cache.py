"""Best-effort Redis projection for persisted asynchronous task status.

MySQL remains the source of truth.  This module only keeps a short-lived
projection used by the polling API, so every operation deliberately degrades
to a cache miss when Redis is unavailable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.core.cache import get_cache
from app.core.config import (
    CACHE_TASK_ACTIVE_TTL_SECONDS,
    CACHE_TASK_TERMINAL_TTL_SECONDS,
)
from app.models import AsyncTask
from app.schemas.skill import TaskStatusResponse


logger = logging.getLogger(__name__)

ACTIVE_TASK_TTL_SECONDS = CACHE_TASK_ACTIVE_TTL_SECONDS
TERMINAL_TASK_TTL_SECONDS = CACHE_TASK_TERMINAL_TTL_SECONDS
TERMINAL_STATUSES = frozenset({"succeeded", "failed", "cancelled"})


def _task_key(task_id: str) -> str:
    return f"task-status:v1:{task_id}"


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _response_payload(value: dict[str, Any]) -> dict[str, Any]:
    """Restore datetimes before the project's strict UTC field validator."""
    restored = dict(value)
    for field in ("created_at", "started_at", "finished_at"):
        timestamp = restored.get(field)
        if isinstance(timestamp, str):
            restored[field] = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return restored


def _payload(task: AsyncTask, *, updated_at: str | None = None) -> dict[str, Any]:
    """Build the public task projection without persisting request_data."""
    return {
        "_cache_meta": {
            "terminal": _status_value(task.status) in TERMINAL_STATUSES,
            "progress": int(task.progress),
        },
        "created_by": task.created_by,
        "updated_at": updated_at or _now_iso(),
        "task": {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": _status_value(task.status),
            "progress": task.progress,
            "result": task.result,
            "error_code": task.error_code,
            "error_message": task.error_message,
            "created_at": _timestamp(task.created_at),
            "started_at": _timestamp(task.started_at),
            "finished_at": _timestamp(task.finished_at),
        },
    }


def _should_replace(cached: dict[str, Any], incoming: dict[str, Any]) -> bool:
    cached_task = cached.get("task") if isinstance(cached, dict) else None
    incoming_task = incoming.get("task") if isinstance(incoming, dict) else None
    if not isinstance(cached_task, dict) or not isinstance(incoming_task, dict):
        return True

    cached_status = _status_value(cached_task.get("status"))
    incoming_status = _status_value(incoming_task.get("status"))
    # A delayed progress callback or redelivered worker must never move a task
    # from a terminal state back to queued/running.
    if cached_status in TERMINAL_STATUSES and incoming_status not in TERMINAL_STATUSES:
        return False

    cached_updated = str(cached.get("updated_at") or "")
    incoming_updated = str(incoming.get("updated_at") or "")
    return not cached_updated or not incoming_updated or incoming_updated >= cached_updated


async def publish_task_status(task: AsyncTask) -> bool:
    """Publish a committed ORM task snapshot to Redis, best effort."""
    cache = get_cache()
    key = _task_key(task.id)
    incoming = _payload(task)
    try:
        monotonic_set = getattr(cache, "set_monotonic_json", None)
        if monotonic_set is not None:
            status = _status_value(task.status)
            ttl = (
                TERMINAL_TASK_TTL_SECONDS
                if status in TERMINAL_STATUSES
                else ACTIVE_TASK_TTL_SECONDS
            )
            return await monotonic_set(key, incoming, ttl_seconds=ttl)
        cached = await cache.get_json(key)
        if isinstance(cached, dict) and not _should_replace(cached, incoming):
            return False
        status = _status_value(task.status)
        ttl = (
            TERMINAL_TASK_TTL_SECONDS
            if status in TERMINAL_STATUSES
            else ACTIVE_TASK_TTL_SECONDS
        )
        return await cache.set_json(key, incoming, ttl_seconds=ttl)
    except Exception:
        logger.warning("task_status_cache_publish_failed task_id=%s", task.id, exc_info=True)
        return False


async def get_cached_task_status(
    task_id: str,
) -> tuple[TaskStatusResponse, int | None] | None:
    """Return a validated cached response and its owner, or a cache miss."""
    cache = get_cache()
    key = _task_key(task_id)
    try:
        payload = await cache.get_json(key)
        if not isinstance(payload, dict) or not isinstance(payload.get("task"), dict):
            return None
        owner = payload.get("created_by")
        if owner is not None and not isinstance(owner, int):
            owner = int(owner)
        return TaskStatusResponse.model_validate(_response_payload(payload["task"])), owner
    except (TypeError, ValueError, ValidationError):
        logger.info("task_status_cache_invalid task_id=%s", task_id, exc_info=True)
        try:
            await cache.delete(key)
        except Exception:
            pass
        return None
    except Exception:
        logger.warning("task_status_cache_read_failed task_id=%s", task_id, exc_info=True)
        return None


async def bump_cache_generations(*namespaces: str) -> None:
    """Invalidate versioned query caches after a committed business mutation."""
    cache = get_cache()
    for namespace in namespaces:
        try:
            await cache.bump_generation(namespace)
        except Exception:
            logger.warning(
                "cache_generation_bump_failed namespace=%s", namespace, exc_info=True
            )
