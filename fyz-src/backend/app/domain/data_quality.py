"""Deterministic job-data quality, time parsing and near-duplicate rules."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.core.time import ensure_utc, utc_now

UTC = timezone.utc
DEFAULT_SOURCE_TIMEZONE = ZoneInfo("Asia/Shanghai")
POLICY_VERSION = "phase1-v1"


@dataclass(frozen=True)
class QualityPolicy:
    source_trust_score: float = 0.7
    freshness_window_days: int = 90
    accepted_threshold: float = 0.75
    warning_threshold: float = 0.55
    near_duplicate_threshold: float = 0.9
    minimum_jd_length: int = 30
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True)
class QualityEvaluation:
    posted_at: datetime | None
    crawled_at: datetime | None
    quality_score: float
    freshness_score: float
    source_trust_score: float
    quality_status: str
    quality_flags: tuple[str, ...]
    content_simhash: str
    policy_version: str
    evaluated_at: datetime


def parse_source_datetime(
    value: Any,
    *,
    observed_at: datetime | None = None,
    source_timezone: ZoneInfo = DEFAULT_SOURCE_TIMEZONE,
) -> datetime | None:
    """Parse common crawler timestamps and normalize them to aware UTC."""

    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, tz=UTC)
    else:
        text = str(value).strip()
        if not text:
            return None
        anchor = ensure_utc(observed_at or utc_now())
        if re.search(r"(?:^|\s)(?:今天|今日)(?:\s|$)", text):
            local_anchor = anchor.astimezone(source_timezone)
            parsed = datetime.combine(local_anchor.date(), time.min)
        elif re.search(r"(?:^|\s)昨天(?:\s|$)", text):
            local_anchor = anchor.astimezone(source_timezone)
            parsed = datetime.combine(local_anchor.date() - timedelta(days=1), time.min)
        elif match := re.search(r"(\d{1,3})\s*天前", text):
            local_anchor = anchor.astimezone(source_timezone)
            parsed = datetime.combine(
                local_anchor.date() - timedelta(days=int(match.group(1))),
                time.min,
            )
        elif match := re.search(r"(\d{1,2})月(\d{1,2})日", text):
            local_anchor = anchor.astimezone(source_timezone)
            month = int(match.group(1))
            day = int(match.group(2))
            try:
                candidate = datetime(
                    local_anchor.year,
                    month,
                    day,
                    tzinfo=source_timezone,
                )
            except ValueError:
                return None
            if candidate > local_anchor + timedelta(days=1):
                candidate = candidate.replace(year=candidate.year - 1)
            parsed = candidate
        else:
            normalized = (
                text.replace("年", "-")
                .replace("月", "-")
                .replace("日", "")
                .replace("/", "-")
                .replace("T", " ")
            )
            normalized = re.sub(
                r"^(\d{4})\.(\d{1,2})\.(\d{1,2})",
                r"\1-\2-\3",
                normalized,
            )
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError:
                parsed = None
                for fmt in (
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%d",
                    "%Y%m%d",
                ):
                    try:
                        parsed = datetime.strptime(normalized, fmt)
                        break
                    except ValueError:
                        continue
                if parsed is None:
                    return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=source_timezone)
    return parsed.astimezone(UTC)


def normalize_job_body(value: str) -> str:
    text = (value or "").casefold()
    for original, canonical in (
        ("研发", "开发"),
        ("api", "接口"),
        ("包含", ""),
        ("以及", "与"),
        ("和", "与"),
    ):
        text = text.replace(original, canonical)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\d+(?:\.\d+)?\s*(?:k|千|万|元|岁|年)", " <num> ", text)
    text = re.sub(r"[^\w\u4e00-\u9fff+#.]+", " ", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> list[str]:
    normalized = normalize_job_body(text)
    latin = re.findall(r"[a-z0-9+#.]{2,}", normalized)
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", normalized)
    chinese = [
        run[index : index + 2]
        for run in chinese_runs
        for index in range(max(len(run) - 1, 1))
        if run[index : index + 2]
    ]
    return latin + chinese or [normalized or "<empty>"]


def simhash64(text: str) -> str:
    vector = [0] * 64
    for token in _tokens(text):
        digest = int.from_bytes(
            hashlib.sha256(token.encode("utf-8")).digest()[:8],
            byteorder="big",
        )
        for bit in range(64):
            vector[bit] += 1 if digest & (1 << bit) else -1
    value = 0
    for bit, weight in enumerate(vector):
        if weight >= 0:
            value |= 1 << bit
    return f"{value:016x}"


def simhash_similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    try:
        distance = (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError:
        return 0.0
    return round(1 - distance / 64, 6)


def evaluate_job_quality(
    record: dict[str, Any],
    *,
    policy: QualityPolicy | None = None,
    evaluated_at: datetime | None = None,
) -> QualityEvaluation:
    policy = policy or QualityPolicy()
    now = ensure_utc(evaluated_at or utc_now())
    flags: list[str] = []

    crawled_text = record.get("crawled_at")
    crawled_at = parse_source_datetime(crawled_text, observed_at=now)
    if crawled_at is None:
        flags.append("missing_or_invalid_crawled_at")
        crawled_at = now

    posted_text = record.get("posted_at")
    posted_at = parse_source_datetime(posted_text, observed_at=crawled_at)
    if not str(posted_text or "").strip():
        flags.append("missing_posted_at")
    elif posted_at is None:
        flags.append("invalid_posted_at")

    freshness_score = 0.35
    if posted_at is not None:
        age_days = (crawled_at - posted_at).total_seconds() / 86400
        if age_days < -1:
            flags.append("future_posted_at")
            freshness_score = 0.0
        else:
            age_days = max(age_days, 0)
            freshness_score = max(
                0.0,
                1 - age_days / max(policy.freshness_window_days, 1),
            )
            if age_days > policy.freshness_window_days:
                flags.append("stale_posting")

    jd_text = normalize_job_body(str(record.get("jd_text") or ""))
    if len(jd_text) < policy.minimum_jd_length:
        flags.append("short_jd_text")
    text_score = min(len(jd_text) / max(policy.minimum_jd_length * 3, 1), 1.0)

    completeness_fields = ("title", "company", "source", "url", "jd_text")
    completeness = sum(
        bool(str(record.get(field) or "").strip()) for field in completeness_fields
    ) / len(completeness_fields)
    if completeness < 1:
        flags.append("missing_core_field")

    source_trust = min(max(policy.source_trust_score, 0.0), 1.0)
    score = (
        0.3 * completeness
        + 0.25 * text_score
        + 0.3 * freshness_score
        + 0.15 * source_trust
    )
    score = round(min(max(score, 0.0), 1.0), 4)
    if score >= policy.accepted_threshold and not {
        "future_posted_at",
        "invalid_posted_at",
    }.intersection(flags):
        status = "accepted"
    elif score >= policy.warning_threshold:
        status = "warning"
    else:
        status = "rejected"

    body = " ".join(
        str(record.get(field) or "")
        for field in ("title", "jd_text", "responsibilities", "requirements")
    )
    return QualityEvaluation(
        posted_at=posted_at,
        crawled_at=crawled_at,
        quality_score=score,
        freshness_score=round(freshness_score, 4),
        source_trust_score=round(source_trust, 4),
        quality_status=status,
        quality_flags=tuple(sorted(set(flags))),
        content_simhash=simhash64(body),
        policy_version=policy.policy_version,
        evaluated_at=now,
    )


def near_duplicate_group_id(left_fingerprint: str, right_fingerprint: str) -> str:
    seed = "|".join(sorted((left_fingerprint, right_fingerprint)))
    return "nd-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def apply_near_duplicate_penalty(score: float, similarity: float) -> float:
    """Reduce weight without deleting source evidence."""

    penalty = 0.15 * min(max((similarity - 0.85) / 0.15, 0.0), 1.0)
    return round(max(0.0, score * (1 - penalty)), 4)
