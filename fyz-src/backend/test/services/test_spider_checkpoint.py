import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from spider_framework.base_spider import BaseSpider  # noqa: E402
import spider_framework.base_spider as base_module  # noqa: E402
from spider_framework.checkpoint import (  # noqa: E402
    CrawlerCheckpoint,
    content_version,
    identity_fingerprint,
)


class CheckpointSpider(BaseSpider):
    name = "checkpoint_test"
    source_name = "test-source"


def _job(external_id: str, *, jd_text: str = "v1", source: str = "test-source") -> dict:
    return {
        "external_id": external_id,
        "source": source,
        "title": "Python Engineer",
        "jd_text": jd_text,
    }


def test_discovery_is_replayable_until_import_ack(monkeypatch, tmp_path):
    checkpoint_path = tmp_path / "state" / "checkpoint.json"
    monkeypatch.setenv("JIEBANG_SPIDER_CHECKPOINT", str(checkpoint_path))

    first_attempt = CheckpointSpider()
    assert first_attempt.add_job(_job("job-1")) is True
    # Simulate snapshot generation followed by an ImportService failure: no ack.
    retry = CheckpointSpider()
    assert retry.add_job(_job("job-1")) is True

    CrawlerCheckpoint(checkpoint_path).acknowledge(
        [_job("job-1")], batch="checkpoint_test_1.json"
    )
    after_successful_import = CheckpointSpider()
    assert after_successful_import.add_job(_job("job-1")) is False
    assert after_successful_import.stats["checkpoint_duplicates"] == 1


def test_identity_and_content_version_allow_job_updates(monkeypatch, tmp_path):
    checkpoint_path = tmp_path / "checkpoint.json"
    monkeypatch.setenv("JIEBANG_SPIDER_CHECKPOINT", str(checkpoint_path))
    original = _job("job-1", jd_text="salary 20k; active")
    updated = _job("job-1", jd_text="salary 25k; closed")

    assert identity_fingerprint(original) == identity_fingerprint(updated)
    assert content_version(original) != content_version(updated)
    CrawlerCheckpoint(checkpoint_path).acknowledge([original], batch="batch-1.json")

    spider = CheckpointSpider()
    spider.snapshot_complete = True
    assert spider.add_job(original) is False
    assert spider.add_job(updated) is True


def test_unchanged_checkpoint_job_is_still_published_as_daily_full_observation(
    monkeypatch, tmp_path
):
    checkpoint_path = tmp_path / "checkpoint.json"
    monkeypatch.setenv("JIEBANG_SPIDER_CHECKPOINT", str(checkpoint_path))
    monkeypatch.setattr(
        base_module, "validate_all", lambda rows, verbose=False: {"failed": 0}
    )
    yesterday = {
        **_job("job-1"),
        "crawled_at": "2026-08-19T10:00:00+08:00",
    }
    CrawlerCheckpoint(checkpoint_path).acknowledge(
        [yesterday], batch="checkpoint_test_1.json"
    )
    today = {**yesterday, "crawled_at": "2026-08-20T10:00:00+08:00"}

    spider = CheckpointSpider()
    spider.snapshot_complete = True
    assert spider.add_job(today) is False
    assert spider.total_data == []
    assert len(spider.observed_data) == 1

    published = Path(spider.save(str(tmp_path)))
    payload = json.loads(published.read_text(encoding="utf-8"))
    assert payload[0]["external_id"] == "job-1"
    assert payload[0]["source_meta"]["snapshot_type"] == "full"
    assert payload[0]["source_meta"]["snapshot_complete"] is True


def test_default_source_is_applied_before_identity_and_content_hash(monkeypatch, tmp_path):
    monkeypatch.setenv("JIEBANG_SPIDER_CHECKPOINT", str(tmp_path / "checkpoint.json"))
    without_source = {"external_id": "job-1", "title": "Python Engineer", "jd_text": "v1"}
    expected = {**without_source, "source": "test-source"}

    spider = CheckpointSpider()
    assert spider.add_job(without_source) is True

    assert spider.total_data[0]["source"] == "test-source"
    assert identity_fingerprint(spider.total_data[0]) == identity_fingerprint(expected)
    assert content_version(spider.total_data[0]) == content_version(expected)


def test_concurrent_acknowledgements_lock_reread_and_merge(tmp_path):
    checkpoint_path = tmp_path / "checkpoint.json"

    def acknowledge(index: int):
        return CrawlerCheckpoint(checkpoint_path).acknowledge(
            [_job(f"job-{index}")], batch=f"batch-{index}.json"
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(acknowledge, range(20)))

    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "crawler-checkpoint-v2"
    assert payload["record_count"] == 20
    assert len(payload["acknowledged_versions"]) == 20
    assert not checkpoint_path.with_suffix(".json.lock").exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_corrupt_or_legacy_checkpoint_fails_open_for_recovery(monkeypatch, tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text("not-json", encoding="utf-8")
    monkeypatch.setenv("JIEBANG_SPIDER_CHECKPOINT", str(checkpoint))
    assert CheckpointSpider().add_job(_job("retry-corrupt")) is True

    checkpoint.write_text(
        json.dumps({"schema_version": "crawler-checkpoint-v1", "fingerprints": ["x"]}),
        encoding="utf-8",
    )
    assert CheckpointSpider().add_job(_job("retry-legacy")) is True


def test_concurrent_snapshot_publish_uses_distinct_complete_files(monkeypatch, tmp_path):
    monkeypatch.delenv("JIEBANG_SPIDER_CHECKPOINT", raising=False)
    monkeypatch.setattr(
        base_module, "validate_all", lambda rows, verbose=False: {"failed": 0}
    )

    def save(index: int) -> str:
        spider = CheckpointSpider()
        spider.total_data = [_job(f"job-{index}", jd_text=f"content-{index}")]
        return spider.save(str(tmp_path))

    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(save, range(12)))

    assert len(set(paths)) == 12
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]
    assert {rows[0]["external_id"] for rows in payloads} == {
        f"job-{index}" for index in range(12)
    }
    assert list(tmp_path.glob("*.tmp")) == []


def test_snapshot_final_path_is_invisible_until_fsync_and_replace(monkeypatch, tmp_path):
    monkeypatch.delenv("JIEBANG_SPIDER_CHECKPOINT", raising=False)
    monkeypatch.setattr(
        base_module, "validate_all", lambda rows, verbose=False: {"failed": 0}
    )
    entered = threading.Event()
    release = threading.Event()
    real_dump = json.dump

    def blocking_dump(payload, stream, **kwargs):
        entered.set()
        assert release.wait(timeout=5)
        return real_dump(payload, stream, **kwargs)

    monkeypatch.setattr(base_module.json, "dump", blocking_dump)
    spider = CheckpointSpider()
    spider.total_data = [_job("job-blocked")]
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(spider.save, str(tmp_path))
        assert entered.wait(timeout=5)
        assert list(tmp_path.glob("checkpoint_test_*.json")) == []
        release.set()
        published = Path(future.result(timeout=5))

    assert published.is_file()
    assert json.loads(published.read_text(encoding="utf-8"))[0]["external_id"] == "job-blocked"


def test_snapshot_write_exception_leaves_no_empty_final_json(monkeypatch, tmp_path):
    monkeypatch.delenv("JIEBANG_SPIDER_CHECKPOINT", raising=False)
    monkeypatch.setattr(
        base_module, "validate_all", lambda rows, verbose=False: {"failed": 0}
    )
    monkeypatch.setattr(
        base_module.json, "dump", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full"))
    )
    spider = CheckpointSpider()
    spider.total_data = [_job("job-failed")]

    try:
        spider.save(str(tmp_path))
    except OSError as exc:
        assert "disk full" in str(exc)
    else:
        raise AssertionError("snapshot write should fail")

    assert list(tmp_path.glob("checkpoint_test_*.json")) == []
    assert list(tmp_path.glob("*.tmp")) == []
