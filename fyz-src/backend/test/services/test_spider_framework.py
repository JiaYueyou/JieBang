"""Crawler snapshot versioning tests."""

import sys
import json
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from spider_framework.base_spider import BaseSpider


def make_spider(records: list[dict]) -> BaseSpider:
    spider = BaseSpider()
    spider.name = "testsource"
    defaults = {
        "company": "测试公司",
        "city": "北京",
        "salary": "",
        "experience": "",
        "education": "",
        "jd_text": "这是一段满足最小长度要求的岗位说明文本。",
        "responsibilities": "",
        "requirements": "",
        "keywords": [],
        "posted_at": None,
        "source": "测试来源",
    }
    spider.total_data = [{**defaults, **record} for record in records]
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


def test_same_business_content_on_next_day_creates_observation_snapshot():
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

        assert second_path != first_path
        assert Path(second_path).name == "testsource_2.json"
        assert len(list(output_dir.glob("testsource_*.json"))) == 2


def test_same_day_crawl_time_changed_reuses_snapshot():
    with tempfile.TemporaryDirectory(dir="test") as directory:
        output_dir = Path(directory)
        first = make_spider([{
            "title": "Job A", "url": "https://example/1",
            "crawled_at": "2026-07-28T01:00:00Z",
        }])
        second = make_spider([{
            "title": "Job A", "url": "https://example/1",
            "crawled_at": "2026-07-28T15:00:00Z",
        }])

        first_path = first.save(str(output_dir))
        second_path = second.save(str(output_dir))

        assert second_path == first_path
        assert len(list(output_dir.glob("testsource_*.json"))) == 1


def test_external_id_keeps_same_title_and_listing_url_as_distinct_jobs():
    spider = BaseSpider()
    spider.source_name = "official-portal"

    assert spider.add_job({
        "external_id": "REQ-1",
        "title": "后端开发工程师",
        "url": "https://example/jobs",
    })
    assert spider.add_job({
        "external_id": "REQ-2",
        "title": "后端开发工程师",
        "url": "https://example/jobs",
    })
    assert len(spider.total_data) == 2


def test_invalid_snapshot_is_rejected_before_write():
    with tempfile.TemporaryDirectory(dir="test") as directory:
        spider = BaseSpider()
        spider.name = "invalid"
        spider.total_data = [{"title": "缺字段岗位"}]

        try:
            spider.save(directory)
        except ValueError as exc:
            assert "job-v1 schema validation failed" in str(exc)
        else:
            raise AssertionError("invalid snapshot should not be written")


def test_complete_empty_snapshot_writes_manifest_and_json_array():
    with tempfile.TemporaryDirectory(dir="test") as directory:
        spider = BaseSpider()
        spider.name = "empty-source"
        spider.source_name = "空岗位测试源"
        spider.snapshot_complete = True
        spider.snapshot_scope = {"collector": "empty-source", "city": "all"}

        path = Path(spider.save(directory))
        manifest_path = path.with_name(path.name + ".manifest")

        assert json.loads(path.read_text(encoding="utf-8")) == []
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["snapshot_complete"] is True
        assert manifest["record_count"] == 0
        assert manifest["scope"] == {"collector": "empty-source", "city": "all"}
