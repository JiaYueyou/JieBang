from datetime import datetime, timedelta, timezone

from app.core.time import ensure_utc, utc_isoformat, utc_now, utc_now_naive


def test_utc_now_contracts():
    aware = utc_now()
    naive = utc_now_naive()

    assert aware.tzinfo == timezone.utc
    assert naive.tzinfo is None
    assert abs((aware.replace(tzinfo=None) - naive).total_seconds()) < 1


def test_ensure_utc_assumes_naive_database_values_are_utc():
    naive = datetime(2026, 7, 30, 12, 0, 0)
    normalized = ensure_utc(naive)

    assert normalized == datetime(2026, 7, 30, 12, 0, 0, tzinfo=timezone.utc)


def test_ensure_utc_converts_offsets_and_serializes_z():
    value = datetime(
        2026,
        7,
        30,
        20,
        0,
        0,
        tzinfo=timezone(timedelta(hours=8)),
    )

    assert utc_isoformat(value) == "2026-07-30T12:00:00Z"
