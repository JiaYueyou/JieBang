"""Unit tests for the browser-driven ByteDance public-careers normalizer."""

import datetime as dt
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from spiders.bytedance_spider import ByteDanceSpider


def test_normalize_job_keeps_in_range_public_post():
    spider = ByteDanceSpider(
        start_date=dt.date(2026, 1, 1),
        end_date=dt.date(2026, 8, 8),
    )
    published = int(dt.datetime(2026, 7, 15, tzinfo=dt.timezone.utc).timestamp() * 1000)
    record = spider.normalize_job({
        "id": "12345",
        "title": "大模型算法工程师",
        "description": "负责大模型训练和推理优化。",
        "requirement": "熟悉 Python 和机器学习。",
        "publish_time": published,
        "city_list": [{"name": "北京"}, {"name": "上海"}],
        "job_category": {"name": "研发"},
        "code": "A12345",
    })

    assert record is not None
    assert record["posted_at"].startswith("2026-07-15")
    assert record["city"] == "北京、上海"
    assert record["source"] == spider.source_name
    assert record["source_type"] == "official_careers_site"
    assert record["source_meta"]["source_type"] == "official_careers_site"


def test_normalize_job_rejects_records_outside_requested_period():
    spider = ByteDanceSpider(
        start_date=dt.date(2026, 1, 1),
        end_date=dt.date(2026, 8, 8),
    )
    published = int(dt.datetime(2025, 12, 31, tzinfo=dt.timezone.utc).timestamp() * 1000)

    assert spider.normalize_job({
        "id": "12345",
        "title": "算法工程师",
        "description": "岗位职责",
        "publish_time": published,
    }) is None
