"""Crawler snapshot versioning tests."""

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from spider_framework.base_spider import BaseSpider


def make_spider(records: list[dict]) -> BaseSpider:
    spider = BaseSpider()
    spider.name = "testsource"
    spider.total_data = records
    return spider


def test_same_count_changed_content_creates_new_snapshot():
    with tempfile.TemporaryDirectory(dir="test") as directory:
        output_dir = Path(directory)
        first = make_spider([
            {"title": "岗位 A", "url": "https://example/1", "crawled_at": "2026-07-28"}
        ])
        second = make_spider([
            {"title": "岗位 B", "url": "https://example/1", "crawled_at": "2026-07-29"}
        ])

        assert Path(first.save(str(output_dir))).name == "testsource_1.json"
        assert Path(second.save(str(output_dir))).name == "testsource_2.json"


def test_only_crawl_time_changed_reuses_snapshot():
    with tempfile.TemporaryDirectory(dir="test") as directory:
        output_dir = Path(directory)
        first = make_spider([
            {"title": "岗位 A", "url": "https://example/1", "crawled_at": "2026-07-28"}
        ])
        second = make_spider([
            {"title": "岗位 A", "url": "https://example/1", "crawled_at": "2026-07-29"}
        ])

        first_path = first.save(str(output_dir))
        second_path = second.save(str(output_dir))

        assert second_path == first_path
        assert len(list(output_dir.glob("testsource_*.json"))) == 1
