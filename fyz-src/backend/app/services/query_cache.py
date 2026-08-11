"""Cache-aside helpers for the expensive read-only FYZ queries.

The cache stores JSON-compatible service results, never request principals or
database objects. Generation numbers make invalidation constant-time: writers
only bump a domain generation and old parameterized entries expire naturally.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.cache import get_cache, stable_query_key


ANALYSIS_CACHE_NAMESPACE = "analysis"
DASHBOARD_CACHE_NAMESPACE = "dashboard"
GRAPH_CACHE_NAMESPACE = "graph"

ANALYSIS_OVERVIEW_TTL_SECONDS = 120
ANALYSIS_JOB_INSIGHTS_TTL_SECONDS = 90
DASHBOARD_OVERVIEW_TTL_SECONDS = 45
GRAPH_QUERY_TTL_SECONDS = 600

# Bound individual entries even when the cache runs on its own Redis instance;
# large panoramas are cheaper to recompute than to monopolize cache memory.
MAX_QUERY_CACHE_BYTES = 1024 * 1024

ModelT = TypeVar("ModelT", bound=BaseModel)
ResultT = TypeVar("ResultT")


def _payload_size(payload: Any) -> int:
    return len(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    )


async def _cache_key(
    generation_namespace: str,
    operation: str,
    params: Mapping[str, Any],
) -> str:
    cache = get_cache()
    generation = await cache.get_generation(generation_namespace)
    return stable_query_key(
        f"{generation_namespace}:{operation}",
        params,
        generation=generation,
    )


async def _get_or_load(
    *,
    generation_namespace: str,
    operation: str,
    params: Mapping[str, Any],
    ttl_seconds: int,
    loader: Callable[[], Awaitable[ResultT]],
    serialize: Callable[[ResultT], Any],
    restore: Callable[[Any], ResultT],
    force_refresh: bool,
) -> ResultT:
    cache = get_cache()
    key = await _cache_key(generation_namespace, operation, params)
    if not force_refresh:
        cached = await cache.get_json(key)
        if cached is not None:
            try:
                return restore(cached)
            except (TypeError, ValueError, ValidationError):
                # Schema changes or a manually written key must not break the
                # API. Loading the source of truth replaces the bad value.
                await cache.delete(key)

    value = await loader()
    payload = serialize(value)
    if _payload_size(payload) <= MAX_QUERY_CACHE_BYTES:
        await cache.set_json(key, payload, ttl_seconds=ttl_seconds)
    return value


async def cached_dict_query(
    *,
    generation_namespace: str,
    operation: str,
    params: Mapping[str, Any],
    ttl_seconds: int,
    loader: Callable[[], Awaitable[dict]],
    force_refresh: bool = False,
) -> dict:
    """Return a cached JSON object or populate it from ``loader``."""

    def restore(payload: Any) -> dict:
        if not isinstance(payload, dict):
            raise TypeError("cached query result is not an object")
        return payload

    return await _get_or_load(
        generation_namespace=generation_namespace,
        operation=operation,
        params=params,
        ttl_seconds=ttl_seconds,
        loader=loader,
        serialize=lambda value: value,
        restore=restore,
        force_refresh=force_refresh,
    )


async def cached_model_query(
    *,
    generation_namespace: str,
    operation: str,
    params: Mapping[str, Any],
    ttl_seconds: int,
    model_type: type[ModelT],
    loader: Callable[[], Awaitable[ModelT]],
    force_refresh: bool = False,
) -> ModelT:
    """Cache a Pydantic result and restore its exact model type on a hit."""

    return await _get_or_load(
        generation_namespace=generation_namespace,
        operation=operation,
        params=params,
        ttl_seconds=ttl_seconds,
        loader=loader,
        serialize=lambda value: value.model_dump(mode="json"),
        restore=model_type.model_validate,
        force_refresh=force_refresh,
    )


async def bump_analysis_generation() -> None:
    await get_cache().bump_generation(ANALYSIS_CACHE_NAMESPACE)
