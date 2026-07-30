from datetime import datetime, timezone

from app.domain.data_quality import (
    QualityPolicy,
    evaluate_job_quality,
    parse_source_datetime,
    simhash64,
    simhash_similarity,
)


def test_parse_source_datetime_normalizes_common_formats_to_utc():
    assert parse_source_datetime("2026-07-30T10:00:00+08:00") == datetime(
        2026, 7, 30, 2, 0, tzinfo=timezone.utc
    )
    assert parse_source_datetime("2026年7月30日") == datetime(
        2026, 7, 29, 16, 0, tzinfo=timezone.utc
    )
    assert parse_source_datetime("not-a-date") is None


def test_relative_source_datetime_uses_explicit_observation_time():
    observed_at = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)

    assert parse_source_datetime("2天前", observed_at=observed_at) == datetime(
        2026, 7, 27, 16, 0, tzinfo=timezone.utc
    )
    assert parse_source_datetime("更新于 6月3日", observed_at=observed_at) == datetime(
        2026, 6, 2, 16, 0, tzinfo=timezone.utc
    )
    assert parse_source_datetime(
        "更新于 今天 代招公司：示例公司",
        observed_at=observed_at,
    ) == datetime(2026, 7, 29, 16, 0, tzinfo=timezone.utc)


def test_quality_evaluation_is_deterministic_and_flags_invalid_dates():
    record = {
        "title": "Python 工程师",
        "company": "示例公司",
        "source": "示例来源",
        "url": "https://example.test/jobs/1",
        "jd_text": "负责 Python 服务开发、MySQL 数据建模、接口测试和线上问题排查。",
        "posted_at": "invalid",
        "crawled_at": "2026-07-30T10:00:00+08:00",
    }
    evaluated_at = datetime(2026, 7, 30, 4, 0, tzinfo=timezone.utc)

    first = evaluate_job_quality(
        record,
        policy=QualityPolicy(source_trust_score=0.8),
        evaluated_at=evaluated_at,
    )
    second = evaluate_job_quality(
        record,
        policy=QualityPolicy(source_trust_score=0.8),
        evaluated_at=evaluated_at,
    )

    assert first == second
    assert "invalid_posted_at" in first.quality_flags
    assert first.quality_status == "warning"


def test_simhash_detects_rewrite_but_not_unrelated_job():
    original = "负责 Python 服务开发，使用 MySQL 建模并维护 FastAPI 接口。"
    rewrite = "承担 Python 后端服务研发、MySQL 数据建模和 FastAPI API 维护。"
    unrelated = "负责市场活动策划、客户运营、品牌文案和线下渠道拓展。"

    exact_hash = simhash64(original)
    assert simhash_similarity(exact_hash, exact_hash) == 1
    assert simhash_similarity(exact_hash, simhash64(rewrite)) > simhash_similarity(
        exact_hash,
        simhash64(unrelated),
    )


def test_simhash_canonicalizes_common_recruitment_paraphrases():
    original = "负责Python服务开发、MySQL数据建模与接口维护。"
    rewrite = "负责 Python 服务研发，包含 MySQL 数据建模和 API 维护。"

    assert simhash_similarity(simhash64(original), simhash64(rewrite)) >= 0.9
