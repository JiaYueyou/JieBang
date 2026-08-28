"""Best-effort asynchronous Redis JSON cache.

MySQL and Neo4j remain the sources of truth. Every public operation therefore
fails open: a Redis outage becomes a cache miss instead of an API outage.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Mapping
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis

from app.core.config import (
    CACHE_CONNECT_TIMEOUT_SECONDS,
    CACHE_DEFAULT_TTL_SECONDS,
    CACHE_ENABLED,
    CACHE_KEY_PREFIX,
    CACHE_SOCKET_TIMEOUT_SECONDS,
    REDIS_CACHE_URL,
)

logger = logging.getLogger(__name__)
_SAFE_KEY_PART = re.compile(r"[^a-zA-Z0-9:_-]+")
_RECOVERY_INVALIDATION_NAMESPACES = ("analysis", "dashboard", "graph")
_MONOTONIC_JSON_SCRIPT = """
local incoming = cjson.decode(ARGV[1])
local current_raw = redis.call('GET', KEYS[1])
if current_raw then
    local ok, current = pcall(cjson.decode, current_raw)
    if ok and type(current) == 'table' then
        local current_meta = current['_cache_meta'] or {}
        local incoming_meta = incoming['_cache_meta'] or {}
        local current_terminal = current_meta['terminal'] == true
        local incoming_terminal = incoming_meta['terminal'] == true
        if current_terminal and not incoming_terminal then
            return 0
        end
        local current_progress = tonumber(current_meta['progress']) or -1
        local incoming_progress = tonumber(incoming_meta['progress']) or -1
        if not current_terminal and not incoming_terminal and current_progress > incoming_progress then
            return 0
        end
    end
end
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
return 1
"""


def _key_part(value: str) -> str:
    normalized = _SAFE_KEY_PART.sub("-", value.strip()).strip("-:")
    if not normalized:
        raise ValueError("cache key part must not be empty")
    return normalized


def stable_query_key(
    namespace: str,
    params: Mapping[str, Any] | None = None,
    **values: Any,
) -> str:
    """Return a bounded deterministic key for an arbitrary query."""
    payload = dict(params or {})
    payload.update(values)
    canonical = json.dumps(
        jsonable_encoder(payload),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{_key_part(namespace)}:{digest}"


class AsyncJsonCache:
    """Small Redis adapter with safe JSON serialization and degradation."""

    def __init__(
        self,
        url: str,
        *,
        enabled: bool = True,
        key_prefix: str = CACHE_KEY_PREFIX,
        default_ttl_seconds: int = CACHE_DEFAULT_TTL_SECONDS,
        connect_timeout_seconds: float = CACHE_CONNECT_TIMEOUT_SECONDS,
        socket_timeout_seconds: float = CACHE_SOCKET_TIMEOUT_SECONDS,
        client: Any | None = None,
    ) -> None:
        self.url = url
        self.enabled = enabled
        self.key_prefix = key_prefix.strip(":")
        self.default_ttl_seconds = max(1, int(default_ttl_seconds))
        self.connect_timeout_seconds = max(0.05, float(connect_timeout_seconds))
        self.socket_timeout_seconds = max(0.05, float(socket_timeout_seconds))
        self._client = client
        self._available: bool | None = False if not enabled else None
        self._last_warning_at = float("-inf")
        self._retry_after = 0.0
        self._needs_recovery_invalidation = False

    @property
    def available(self) -> bool | None:
        """Last observed connection state; ``None`` means not checked yet."""
        return self._available

    def key(self, value: str) -> str:
        logical_key = value.strip(":")
        if not logical_key:
            raise ValueError("cache key must not be empty")
        return f"{self.key_prefix}:{logical_key}" if self.key_prefix else logical_key

    def _get_client(self) -> Any | None:
        if not self.enabled:
            return None
        if self._available is False and time.monotonic() < self._retry_after:
            return None
        if self._client is None:
            self._client = Redis.from_url(
                self.url,
                decode_responses=True,
                socket_connect_timeout=self.connect_timeout_seconds,
                socket_timeout=self.socket_timeout_seconds,
                health_check_interval=30,
            )
        return self._client

    def _mark_available(self) -> None:
        self._available = True
        self._retry_after = 0.0

    def _mark_unavailable(self) -> None:
        self._available = False
        self._retry_after = time.monotonic() + 5.0
        # A MySQL commit may happen while Redis is unavailable.  Before any
        # recovered cache read, advance every query-cache generation so data
        # cached before the outage can never reappear as the current view.
        self._needs_recovery_invalidation = True

    async def _get_ready_client(self) -> Any | None:
        client = self._get_client()
        if client is None:
            return None
        if self._available is not False:
            return client
        try:
            await client.ping()
            if self._needs_recovery_invalidation:
                for namespace in _RECOVERY_INVALIDATION_NAMESPACES:
                    await client.incr(self._generation_key(namespace))
                self._needs_recovery_invalidation = False
                logger.info(
                    "Redis cache recovered; query cache generations invalidated"
                )
            self._mark_available()
            return client
        except Exception as exc:
            self._mark_unavailable()
            self._warn("recovery", exc)
            return None

    def _warn(self, operation: str, exc: Exception) -> None:
        # Prevent one Redis outage from flooding application logs.
        now = time.monotonic()
        if now - self._last_warning_at >= 30:
            logger.warning(
                "Redis cache %s failed; continuing without cache (%s: %s)",
                operation,
                type(exc).__name__,
                exc,
            )
            self._last_warning_at = now

    async def start(self) -> bool:
        """Initialize and probe Redis without making startup depend on it."""
        client = await self._get_ready_client()
        if client is None:
            return False
        try:
            await client.ping()
            self._mark_available()
            logger.info("Redis business cache initialized")
            return True
        except Exception as exc:  # Redis is explicitly an optional dependency.
            self._mark_unavailable()
            self._warn("startup", exc)
            return False

    async def close(self) -> None:
        client, self._client = self._client, None
        self._available = False if not self.enabled else None
        self._retry_after = 0.0
        self._needs_recovery_invalidation = False
        if client is None:
            return
        try:
            await client.aclose()
        except Exception as exc:
            self._warn("shutdown", exc)

    async def get_json(self, key: str) -> Any | None:
        client = await self._get_ready_client()
        if client is None:
            return None
        physical_key = self.key(key)
        try:
            raw = await client.get(physical_key)
            self._mark_available()
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except (TypeError, ValueError) as exc:
                # Corrupt or legacy values must not poison subsequent reads.
                self._warn("decode", exc)
                try:
                    await client.delete(physical_key)
                except Exception:
                    pass
                return None
        except Exception as exc:
            self._mark_unavailable()
            self._warn("get", exc)
            return None

    async def set_json(
        self,
        key: str,
        value: Any,
        *,
        ttl_seconds: int | None = None,
    ) -> bool:
        client = await self._get_ready_client()
        if client is None:
            return False
        try:
            payload = json.dumps(
                jsonable_encoder(value),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            ttl = max(1, int(ttl_seconds or self.default_ttl_seconds))
            await client.set(self.key(key), payload, ex=ttl)
            self._mark_available()
            return True
        except Exception as exc:
            self._mark_unavailable()
            self._warn("set", exc)
            return False

    async def set_monotonic_json(
        self,
        key: str,
        value: Any,
        *,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Atomically reject terminal/progress rollback for state projections."""
        client = await self._get_ready_client()
        if client is None:
            return False
        ttl = max(1, int(ttl_seconds or self.default_ttl_seconds))
        try:
            payload = json.dumps(
                jsonable_encoder(value),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            if hasattr(client, "eval"):
                written = await client.eval(
                    _MONOTONIC_JSON_SCRIPT,
                    1,
                    self.key(key),
                    payload,
                    ttl,
                )
                self._mark_available()
                return bool(written)

            # Lightweight test doubles may not implement Lua. Production
            # Redis always takes the atomic branch above.
            current = await self.get_json(key)
            if isinstance(current, dict):
                current_meta = current.get("_cache_meta") or {}
                incoming_meta = value.get("_cache_meta") or {}
                current_terminal = bool(current_meta.get("terminal"))
                incoming_terminal = bool(incoming_meta.get("terminal"))
                if current_terminal and not incoming_terminal:
                    return False
                if (
                    not current_terminal
                    and not incoming_terminal
                    and int(current_meta.get("progress", -1))
                    > int(incoming_meta.get("progress", -1))
                ):
                    return False
            return await self.set_json(key, value, ttl_seconds=ttl)
        except Exception as exc:
            self._mark_unavailable()
            self._warn("monotonic-set", exc)
            return False

    async def delete(self, *keys: str) -> bool:
        if not keys:
            return True
        client = await self._get_ready_client()
        if client is None:
            return False
        try:
            await client.delete(*(self.key(key) for key in keys))
            self._mark_available()
            return True
        except Exception as exc:
            self._mark_unavailable()
            self._warn("delete", exc)
            return False

    def _generation_key(self, namespace: str) -> str:
        return self.key(f"generation:{_key_part(namespace)}")

    async def get_generation(self, namespace: str) -> int:
        """Read a generation; missing/unavailable Redis means generation zero."""
        client = await self._get_ready_client()
        if client is None:
            return 0
        try:
            raw = await client.get(self._generation_key(namespace))
            self._mark_available()
            return max(0, int(raw)) if raw is not None else 0
        except Exception as exc:
            self._mark_unavailable()
            self._warn("generation-get", exc)
            return 0

    async def bump_generation(self, namespace: str) -> int | None:
        """Invalidate a namespace in O(1), without a Redis key scan."""
        client = await self._get_ready_client()
        if client is None:
            return None
        try:
            generation = int(await client.incr(self._generation_key(namespace)))
            self._mark_available()
            return generation
        except Exception as exc:
            self._mark_unavailable()
            self._warn("generation-bump", exc)
            return None

    async def versioned_key(self, namespace: str, query_key: str) -> str:
        generation = await self.get_generation(namespace)
        return f"{_key_part(namespace)}:g{generation}:{query_key.strip(':')}"


_cache = AsyncJsonCache(
    REDIS_CACHE_URL,
    enabled=CACHE_ENABLED,
    key_prefix=CACHE_KEY_PREFIX,
)


def get_cache() -> AsyncJsonCache:
    return _cache


async def initialize_cache() -> bool:
    return await _cache.start()


async def close_cache() -> None:
    await _cache.close()
