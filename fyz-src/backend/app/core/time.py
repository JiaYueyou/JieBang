"""UTC helpers for current naive database columns and future aware APIs."""

from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for APIs and aware columns."""

    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    """Return UTC without tzinfo for the repository's current naive columns.

    The value is still semantically UTC. This compatibility helper prevents
    local server time from being mixed with UTC before the Phase 1 migration.
    """

    return utc_now().replace(tzinfo=None)


def ensure_utc(value: datetime) -> datetime:
    """Normalize a datetime to aware UTC, assuming naive values are UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    """Attach UTC to legacy naive values and normalize aware values."""

    if value is None:
        return None
    return ensure_utc(value)


def utc_isoformat(value: datetime) -> str:
    """Serialize a datetime in canonical RFC 3339 UTC form."""

    return ensure_utc(value).isoformat().replace("+00:00", "Z")
