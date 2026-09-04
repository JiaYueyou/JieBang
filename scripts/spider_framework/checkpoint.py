"""Restart-safe crawler acknowledgement state with cross-process locking."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = "crawler-checkpoint-v2"
_VOLATILE_FIELDS = {"crawled_at", "snapshot_observed_at"}


def identity_fingerprint(record: dict) -> str:
    external_id = str(record.get("external_id") or "").strip()
    source = str(record.get("source") or "").strip()
    if external_id:
        raw = f"external:{source}|{external_id}"
    else:
        raw = "fallback:{url}|{title}".format(
            url=str(record.get("url") or "").strip(),
            title=str(record.get("title") or "").strip(),
        )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def content_version(record: dict) -> str:
    """Hash mutable business content separately from stable requisition identity."""
    normalized = {
        key: value for key, value in record.items() if key not in _VOLATILE_FIELDS
    }
    source_meta = normalized.get("source_meta")
    if isinstance(source_meta, dict):
        normalized["source_meta"] = {
            key: value
            for key, value in source_meta.items()
            if key not in _VOLATILE_FIELDS
        }
    payload = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ExclusiveFileLock:
    """Small Windows-compatible lock based on exclusive file creation."""

    def __init__(self, path: Path, *, timeout: float = 10.0, stale_after: float = 60.0):
        self.path = path
        self.timeout = timeout
        self.stale_after = stale_after
        self._owned = False

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                descriptor = os.open(
                    self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                with os.fdopen(descriptor, "w", encoding="ascii") as stream:
                    stream.write(f"pid={os.getpid()} created={time.time()}\n")
                self._owned = True
                return self
            except FileExistsError:
                try:
                    stale = time.time() - self.path.stat().st_mtime > self.stale_after
                    if stale:
                        self.path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"crawler checkpoint lock timeout: {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type, exc, traceback):
        if self._owned:
            try:
                self.path.unlink(missing_ok=True)
            finally:
                self._owned = False


class CrawlerCheckpoint:
    """Acknowledged identity/content versions; discovery alone never advances it."""

    def __init__(self, path: Path):
        self.path = path
        self.lock_path = path.with_suffix(path.suffix + ".lock")

    def read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != SCHEMA_VERSION:
                # v1 stored identity only and cannot prove which content was
                # imported. Replay once rather than silently losing updates.
                return {}
            versions = payload.get("acknowledged_versions") or {}
            if not isinstance(versions, dict):
                return {}
            return {
                str(identity): str(version)
                for identity, version in versions.items()
                if identity and version
            }
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return {}

    def acknowledge(self, records: Iterable[dict], *, batch: str) -> dict:
        additions = {
            identity_fingerprint(record): content_version(record)
            for record in records
        }
        with ExclusiveFileLock(self.lock_path):
            merged = self.read()
            merged.update(additions)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "acknowledged_versions": dict(sorted(merged.items())),
                "record_count": len(merged),
                "last_acknowledged_batch": batch,
                "updated_at_epoch": int(time.time()),
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(
                f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
            )
            try:
                with temporary.open("w", encoding="utf-8") as stream:
                    json.dump(payload, stream, ensure_ascii=False, indent=2)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
        return payload


def acknowledge_snapshot(checkpoint_path: Path, snapshot_path: Path) -> dict:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("crawler snapshot must contain a JSON array")
    return CrawlerCheckpoint(checkpoint_path).acknowledge(
        payload, batch=snapshot_path.name
    )


def run_checkpoint_self_check() -> dict:
    """Exercise replay, mutable content and concurrent merge semantics."""
    with tempfile.TemporaryDirectory(prefix="jiebang-crawler-check-") as directory:
        path = Path(directory) / "checkpoint.json"
        original = {
            "source": "official", "external_id": "job-1",
            "title": "Engineer", "jd_text": "salary=20k status=active",
        }
        updated = {**original, "jd_text": "salary=25k status=closed"}
        before_ack_replayable = CrawlerCheckpoint(path).read() == {}
        CrawlerCheckpoint(path).acknowledge([original], batch="batch-1.json")
        acknowledged = CrawlerCheckpoint(path).read()
        update_detected = (
            identity_fingerprint(original) == identity_fingerprint(updated)
            and content_version(original) != content_version(updated)
            and acknowledged.get(identity_fingerprint(updated))
            != content_version(updated)
        )

        def ack(index: int):
            CrawlerCheckpoint(path).acknowledge(
                [{
                    "source": "official", "external_id": f"concurrent-{index}",
                    "title": "Engineer", "jd_text": f"version-{index}",
                }],
                batch=f"batch-{index}.json",
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(ack, range(8)))
        merged = CrawlerCheckpoint(path).read()
        concurrent_merge = len(merged) == 9
        checks = {
            "unacknowledged_batch_replayable": before_ack_replayable,
            "identity_content_versions_separated": update_detected,
            "concurrent_ack_merge_preserved": concurrent_merge,
        }
        return {"checks": checks, "passed": all(checks.values())}
