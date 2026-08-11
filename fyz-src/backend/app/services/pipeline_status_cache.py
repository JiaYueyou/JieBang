"""Redis projection for the admin pipeline polling endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.cache import get_cache
from app.core.config import (
    CACHE_TASK_ACTIVE_TTL_SECONDS,
    CACHE_TASK_TERMINAL_TTL_SECONDS,
)

TERMINAL_PIPELINE_STATUSES = frozenset({"succeeded", "partial", "failed", "cancelled"})


class PipelineStatusSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    status: str
    stage: str
    progress: int = Field(ge=0, le=100)


def _key(run_id: str) -> str:
    return f"pipeline-status:v1:{run_id}"


async def publish_pipeline_status(snapshot: dict[str, Any]) -> bool:
    try:
        validated = PipelineStatusSnapshot.model_validate(snapshot)
    except ValidationError:
        return False
    snapshot = validated.model_dump(mode="json")
    run_id = validated.id
    status = validated.status
    payload = {
        "_cache_meta": {
            "terminal": status in TERMINAL_PIPELINE_STATUSES,
            "progress": validated.progress,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": snapshot,
    }
    ttl = (
        CACHE_TASK_TERMINAL_TTL_SECONDS
        if status in TERMINAL_PIPELINE_STATUSES
        else CACHE_TASK_ACTIVE_TTL_SECONDS
    )
    return await get_cache().set_monotonic_json(_key(run_id), payload, ttl_seconds=ttl)


async def get_cached_pipeline_status(run_id: str) -> dict[str, Any] | None:
    payload = await get_cache().get_json(_key(run_id))
    if not isinstance(payload, dict) or not isinstance(payload.get("pipeline"), dict):
        return None
    try:
        return PipelineStatusSnapshot.model_validate(payload["pipeline"]).model_dump(
            mode="json"
        )
    except ValidationError:
        await get_cache().delete(_key(run_id))
        return None
