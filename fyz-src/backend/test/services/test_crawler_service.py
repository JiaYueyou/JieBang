"""CrawlerService 采集结果结构化分类单元测试。"""

import json
import os
import time

from app.services.crawler_service import (
    CRAWLER_STATUS_NO_DATA,
    CRAWLER_STATUS_OK,
    CRAWLER_STATUS_RUN_FAILED,
    CrawlerService,
    REGISTERED_SPIDERS,
    SpiderMeta,
)


def test_registered_official_portals_have_unique_ids_and_scripts():
    ids = [meta.id for meta in REGISTERED_SPIDERS]
    modules = {meta.module_name for meta in REGISTERED_SPIDERS}
    assert len(ids) == len(set(ids))
    assert modules == {"iflytek_spider", "jd_spider", "meituan_spider", "deepseek_spider"}
    assert all(meta.exists() for meta in REGISTERED_SPIDERS)
    assert set(CrawlerService()._enabled) == set(ids)


class FakeProc:
    """模拟已结束的 subprocess.Popen 对象。"""

    def __init__(self, returncode: int):
        self.returncode = returncode

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return None


def _stats_lines(fetched=0, duplicates=0, errors=0, pages=0) -> list[str]:
    return [
        f"抓取成功: {fetched} 条",
        f"去重跳过: {duplicates} 条",
        f"错误次数: {errors} 次",
        f"已爬页数: {pages} 页",
    ]


def _service_with_proc(
    returncode: int,
    stderr_lines: list[str],
    spider_id: int = 2,
) -> CrawlerService:
    service = CrawlerService()
    service._running_tasks[spider_id] = FakeProc(returncode)
    service._running_since[spider_id] = time.time() - 10
    service._stderr[spider_id] = stderr_lines
    service._stdout[spider_id] = []
    return service


def test_parse_spider_stats_empty():
    assert CrawlerService._parse_spider_stats("") == {
        "fetched": 0,
        "duplicates": 0,
        "checkpoint_duplicates": 0,
        "errors": 0,
        "pages": 0,
    }


def test_parse_spider_stats_full():
    text = "\n".join(_stats_lines(fetched=12, duplicates=3, errors=2, pages=4))
    assert CrawlerService._parse_spider_stats(text) == {
        "fetched": 12,
        "duplicates": 3,
        "checkpoint_duplicates": 0,
        "errors": 2,
        "pages": 4,
    }


def test_parse_spider_stats_includes_restart_safe_deduplication():
    stats = CrawlerService._parse_spider_stats("历史检查点去重: 9 条")
    assert stats["checkpoint_duplicates"] == 9


def test_parse_spider_stats_chinese_colon():
    text = "抓取成功：7 条\n错误次数：1 次"
    stats = CrawlerService._parse_spider_stats(text)
    assert stats["fetched"] == 7
    assert stats["errors"] == 1


def test_poll_run_failed(monkeypatch):
    monkeypatch.setattr(SpiderMeta, "_latest_output", lambda self: None)
    service = _service_with_proc(returncode=1, stderr_lines=["boom"])
    result = service.poll_spider(2)
    assert result["error_category"] == CRAWLER_STATUS_RUN_FAILED
    assert result["error_reason"] == "exception"
    assert "异常退出" in result["message"]
    assert result["returncode"] == 1


def test_poll_no_data_network(monkeypatch):
    monkeypatch.setattr(SpiderMeta, "_latest_output", lambda self: None)
    service = _service_with_proc(
        returncode=0, stderr_lines=_stats_lines(fetched=0, errors=3)
    )
    result = service.poll_spider(2)
    assert result["error_category"] == CRAWLER_STATUS_NO_DATA
    assert result["error_reason"] == "network"
    assert result["stats"]["errors"] == 3
    assert "反爬" in result["message"] or "网络" in result["message"]


def test_poll_no_data_no_response(monkeypatch):
    monkeypatch.setattr(SpiderMeta, "_latest_output", lambda self: None)
    service = _service_with_proc(
        returncode=0, stderr_lines=_stats_lines(fetched=0, errors=0)
    )
    result = service.poll_spider(2)
    assert result["error_category"] == CRAWLER_STATUS_NO_DATA
    assert result["error_reason"] == "no_response"
    assert "页面结构变更" in result["message"] or "登录" in result["message"]


def test_poll_no_data_checkpoint_duplicates_are_unchanged(monkeypatch):
    monkeypatch.setattr(SpiderMeta, "_latest_output", lambda self: None)
    service = _service_with_proc(
        returncode=0,
        stderr_lines=_stats_lines(fetched=0, duplicates=5)
        + ["历史检查点去重: 5 条"],
    )
    result = service.poll_spider(2)
    assert result["error_category"] == CRAWLER_STATUS_NO_DATA
    assert result["error_reason"] == "unchanged"
    assert result["stats"]["checkpoint_duplicates"] == 5


def test_poll_no_data_unchanged(monkeypatch, tmp_path):
    # 旧文件（mtime 早于本次运行）且 fetched>0 → 业务内容无变化，复用快照
    old_file = tmp_path / "iflytek_1.json"
    old_file.write_text(json.dumps([{"title": "t"}]), encoding="utf-8")
    past = time.time() - 3600
    os.utime(old_file, (past, past))
    monkeypatch.setattr(SpiderMeta, "_latest_output", lambda self: old_file)
    service = _service_with_proc(
        returncode=0, stderr_lines=_stats_lines(fetched=5)
    )
    result = service.poll_spider(2)
    assert result["error_category"] == CRAWLER_STATUS_NO_DATA
    assert result["error_reason"] == "unchanged"
    assert result["filename"] == "iflytek_1.json"
    assert "内容一致" in result["message"]


def test_poll_ok(monkeypatch, tmp_path):
    new_file = tmp_path / "iflytek_2.json"
    new_file.write_text(
        json.dumps([{"title": "a"}, {"title": "b"}]), encoding="utf-8"
    )
    monkeypatch.setattr(SpiderMeta, "_latest_output", lambda self: new_file)
    service = _service_with_proc(
        returncode=0, stderr_lines=_stats_lines(fetched=2)
    )
    result = service.poll_spider(2)
    assert result["error_category"] == CRAWLER_STATUS_OK
    assert result["error_reason"] == ""
    assert result["records_count"] == 2
    assert result["output_changed"] is True


def test_acknowledge_import_advances_only_the_matching_source(monkeypatch, tmp_path):
    import app.services.crawler_service as crawler_module

    data_dir = tmp_path / "data"
    state_dir = data_dir / ".crawler_state"
    data_dir.mkdir()
    snapshot = data_dir / "iflytek_1.json"
    snapshot.write_text(
        json.dumps([{
            "external_id": "job-1", "source": "iflytek",
            "title": "Python Engineer", "jd_text": "version one",
        }]),
        encoding="utf-8",
    )
    monkeypatch.setattr(crawler_module, "DATA_DIR", data_dir)
    monkeypatch.setattr(crawler_module, "CRAWLER_STATE_DIR", state_dir)

    result = CrawlerService().acknowledge_import(2, snapshot.name)

    assert result["schema_version"] == "crawler-checkpoint-v2"
    assert result["record_count"] == 1
    assert (state_dir / "iflytek_spider.json").is_file()


def test_output_marker_selects_this_process_snapshot_not_latest(monkeypatch, tmp_path):
    import app.services.crawler_service as crawler_module

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    own = data_dir / "iflytek_1.json"
    other = data_dir / "iflytek_2.json"
    own.write_text(json.dumps([{"external_id": "own"}]), encoding="utf-8")
    other.write_text(json.dumps([{"external_id": "other"}]), encoding="utf-8")
    monkeypatch.setattr(crawler_module, "DATA_DIR", data_dir)

    selected = CrawlerService._output_from_logs(
        f"log\nCRAWLER_OUTPUT_PATH={own.resolve()}\n"
    )

    assert selected == own.resolve()
