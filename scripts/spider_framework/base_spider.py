# -*- coding: utf-8 -*-
"""
爬虫基类 — BaseSpider

职责：
  1. 请求配置（UA 轮换、超时、重试、限速）
  2. 统一的数据保存与自动编号
  3. 提供 parse() 接口供子类实现
  4. 输出前自动通过 Schema 校验

用法：
  class MySpider(BaseSpider):
      def parse(self, page_num: int) -> list[dict]:
          # 返回符合 job-v1 schema 的字典列表
          ...
"""

import json
import os
import re
import random
import time
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from .schema import validate_all
from .checkpoint import (
    CrawlerCheckpoint,
    ExclusiveFileLock,
    content_version,
    identity_fingerprint,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("spider")


# ============================================================
# User-Agent 池（浏览器轮换）
# ============================================================
USER_AGENTS = [
    # Chrome 系列
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    # Edge 系列
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
    # Firefox 系列
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
]


class BaseSpider:
    """爬虫基类 —— 所有爬虫应继承此基类"""

    # === 子类必须定义 ===
    name: str = ""                # 爬虫名称，用于文件名、日志
    source_name: str = ""         # 数据来源名称（写入 source 字段）
    default_config: dict = {}     # 默认配置（会被 YAML 配置覆盖）

    def __init__(self):
        # ---------- 输出目录（可通过 CLI --output-dir 设置） ----------
        self.save_output_dir: str | None = None

        # ---------- 限速 ----------
        self.request_interval = self.default_config.get("request_interval", 1.0)
        self._last_request_time = 0.0

        # ---------- 重试 ----------
        self.retry_times = int(os.getenv(
            "JIEBANG_SPIDER_RETRY_COUNT", self.default_config.get("retry_times", 3)
        ))
        self.retry_delay = self.default_config.get("retry_delay", 2)

        # ---------- 请求配置 ----------
        self.timeout = int(os.getenv(
            "JIEBANG_SPIDER_TIMEOUT", self.default_config.get("timeout", 30)
        ))
        self.default_headers = self.default_config.get("headers", {})

        # ---------- 数据收集 ----------
        self.total_data = []
        # A complete observation set is kept independently from changed rows.
        # Checkpoints suppress expensive downstream work, not proof that a job
        # was still visible during this source run.
        self.observed_data = []
        # Absence is only meaningful when the source traversal reached its end.
        # Individual spiders set this after confirming pagination completeness.
        self.snapshot_complete = False
        self.snapshot_scope = {"collector": self.name}
        self.max_records = max(0, int(os.getenv("JIEBANG_SPIDER_MAX_RECORDS", "0")))
        self.seen_ids = set()  # 去重用
        checkpoint_path = os.getenv("JIEBANG_SPIDER_CHECKPOINT")
        self.checkpoint = (
            CrawlerCheckpoint(Path(checkpoint_path)) if checkpoint_path else None
        )
        self.acknowledged_versions = self.checkpoint.read() if self.checkpoint else {}
        self.seen_versions: set[tuple[str, str]] = set()

        # ---------- 运行时统计 ----------
        self.stats = {
            "fetched": 0,       # 已抓取条数
            "duplicates": 0,    # 去重跳过
            "errors": 0,        # 错误次数
            "pages": 0,         # 已爬页数
            "checkpoint_duplicates": 0,
        }

    # ============================================================
    # 公共方法
    # ============================================================

    def fetch(self, url: str, method: str = "GET",
              headers: Optional[dict] = None,
              json_data: Optional[dict] = None,
              data: Optional[dict] = None,
              params: Optional[dict] = None) -> requests.Response:
        """
        统一的请求方法 —— 自带 UA 轮换、限速、重试

        参数：
          url: 请求 URL
          method: GET / POST
          headers: 额外请求头（会合并到默认头 + UA）
          json_data: POST 的 JSON body
          params: URL 查询参数
        """
        # 限速：确保两次请求间隔足够
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)

        # 合并请求头
        merged_headers = dict(self.default_headers)
        merged_headers["User-Agent"] = random.choice(USER_AGENTS)
        if headers:
            merged_headers.update(headers)

        # 发起请求 + 自动重试
        last_error = None
        for attempt in range(1, self.retry_times + 1):
            try:
                if method.upper() == "GET":
                    resp = requests.get(
                        url, headers=merged_headers, params=params,
                        timeout=self.timeout
                    )
                else:
                    resp = requests.post(
                        url, headers=merged_headers, json=json_data, data=data,
                        params=params, timeout=self.timeout
                    )
                resp.raise_for_status()
                self._last_request_time = time.time()
                return resp
            except Exception as e:
                last_error = e
                logger.warning("  请求失败 (尝试 %d/%d): %s", attempt, self.retry_times, e)
                if attempt < self.retry_times:
                    time.sleep(self.retry_delay * attempt)
                self.stats["errors"] += 1

        raise RuntimeError(f"请求失败已达最大重试次数: {url} — {last_error}")

    def add_job(self, record: dict) -> bool:
        """
        添加一条岗位记录，自动去重（基于 URL + 标题指纹）

        返回：True=新记录, False=重复跳过
        """
        if self.max_records and len(self.observed_data) >= self.max_records:
            return False

        # 生成指纹
        record.setdefault("source", self.source_name)
        fp = identity_fingerprint(record)
        version = content_version(record)
        if (fp, version) in self.seen_versions:
            self.stats["duplicates"] += 1
            return False
        self.seen_ids.add(fp)
        self.seen_versions.add((fp, version))
        self.observed_data.append(record)

        if self.acknowledged_versions.get(fp) == version:
            self.stats["duplicates"] += 1
            self.stats["checkpoint_duplicates"] += 1
            return False

        # 补充默认字段
        self.total_data.append(record)
        self.stats["fetched"] += 1
        return True

    def save(self, output_dir: Optional[str] = None) -> str:
        """
        保存数据到 JSON 文件（自动编号，业务内容相同时复用最新快照）

        参数：
          output_dir: 输出目录，默认当前目录

        返回：本次可用的文件路径
        """
        data = self.observed_data or self.total_data
        if not data and not self.snapshot_complete:
            logger.warning("⚠️ 没有数据可保存")
            return ""

        for record in data:
            source_meta = record.get("source_meta")
            if not isinstance(source_meta, dict):
                source_meta = {}
            record["source_meta"] = {
                **source_meta,
                "snapshot_type": "full" if self.snapshot_complete else "delta",
                "snapshot_complete": self.snapshot_complete,
                "snapshot_observed_at": record.get("crawled_at"),
            }

        validation = validate_all(data, verbose=False)
        if validation["failed"]:
            first = validation["errors"][0]
            raise ValueError(
                "job-v1 schema validation failed before snapshot write: "
                f"record={first['index']} errors={first['errors']}"
            )

        output_dir = output_dir or self.save_output_dir or os.getcwd()
        return self._publish_snapshot(data, Path(output_dir))

    def _publish_snapshot(self, data: list[dict], output_dir: Path) -> str:
        """Publish a complete sequential snapshot under a per-source lock."""
        output_dir.mkdir(parents=True, exist_ok=True)
        lock_path = output_dir / f".{self.name}.snapshot.lock"
        with ExclusiveFileLock(lock_path, timeout=30.0):
            # Re-scan inside the lock; a previous process may have published
            # while this process was waiting.
            pattern = re.compile(rf"^{re.escape(self.name)}_(\d+)\.json$")
            numbered = []
            for candidate in output_dir.iterdir():
                match = pattern.match(candidate.name)
                if match:
                    numbered.append((int(match.group(1)), candidate))
            max_num = max((number for number, _ in numbered), default=0)
            new_digest = self._content_digest(data)
            if numbered:
                latest_path = max(numbered, key=lambda item: item[0])[1]
                try:
                    existing_data = json.loads(latest_path.read_text(encoding="utf-8"))
                    if data and (
                        self._content_digest(existing_data) == new_digest
                        and self._observation_day(existing_data)
                        == self._observation_day(data)
                    ):
                        logger.info("CRAWLER_OUTPUT_PATH=%s", latest_path.resolve())
                        return str(latest_path)
                except (json.JSONDecodeError, OSError):
                    pass

            filename = f"{self.name}_{max_num + 1}.json"
            filepath = output_dir / filename
            temporary = output_dir / (
                f".{filename}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
            )
            manifest_path = filepath.with_name(filepath.name + ".manifest")
            manifest_temporary = output_dir / (
                f".{manifest_path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
            )
            data.sort(
                key=lambda item: item.get("posted_at") or item.get("post_date") or "",
                reverse=True,
            )
            try:
                with temporary.open("x", encoding="utf-8") as stream:
                    json.dump(data, stream, ensure_ascii=False, indent=4)
                    stream.flush()
                    os.fsync(stream.fileno())
                manifest = self._snapshot_manifest(
                    data,
                    payload_sha256=self._file_sha256(temporary),
                )
                with manifest_temporary.open("x", encoding="utf-8") as stream:
                    json.dump(manifest, stream, ensure_ascii=False, indent=2)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(manifest_temporary, manifest_path)
                os.replace(temporary, filepath)
            finally:
                temporary.unlink(missing_ok=True)
                manifest_temporary.unlink(missing_ok=True)

        logger.info(
            "snapshot saved: %s (%d records, %d fields)",
            filepath,
            len(data),
            len(data[0]) if data else 0,
        )
        logger.info("CRAWLER_OUTPUT_PATH=%s", filepath.resolve())
        return str(filepath)

    def _snapshot_manifest(self, data: list[dict], *, payload_sha256: str) -> dict:
        scope = dict(self.snapshot_scope or {})
        scope_payload = json.dumps(
            scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        observed_values = sorted(
            str(record.get("crawled_at") or "") for record in data
            if record.get("crawled_at")
        )
        return {
            "schema_version": "crawler-snapshot-manifest-v1",
            "source": self.source_name,
            "snapshot_type": "full" if self.snapshot_complete else "delta",
            "snapshot_complete": self.snapshot_complete,
            "observed_at": (
                observed_values[-1]
                if observed_values
                else datetime.now(timezone.utc).isoformat(timespec="seconds")
            ),
            "scope": scope,
            "scope_hash": hashlib.sha256(scope_payload.encode("utf-8")).hexdigest(),
            "record_count": len(data),
            "business_checksum": self._content_digest(data),
            "payload_sha256": payload_sha256,
        }

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def print_stats(self):
        """打印运行时统计"""
        logger.info("=" * 40)
        logger.info("爬虫统计 [%s]", self.name)
        logger.info("  抓取成功: %d 条", self.stats["fetched"])
        logger.info("  去重跳过: %d 条", self.stats["duplicates"])
        logger.info("  错误次数: %d 次", self.stats["errors"])
        logger.info("  已爬页数: %d 页", self.stats["pages"])
        logger.info(
            "  历史检查点去重: %d 条", self.stats["checkpoint_duplicates"]
        )
        logger.info("=" * 40)

    # ============================================================
    # 子类需实现的接口
    # ============================================================

    def parse(self, page_num: int) -> list[dict]:
        """
        解析一页数据 —— 子类必须实现

        参数：
          page_num: 页码（从 0 或 1 开始）

        返回：
          符合 job-v1 schema 的字典列表
        """
        raise NotImplementedError("子类必须实现 parse() 方法")

    def run(self):
        """
        主流程 —— 子类可以按需重写

        默认逻辑：遍历 1~N 页，每页调用 parse()
        """
        total_pages = self.default_config.get("total_pages", 5)
        configured_max_pages = int(os.getenv("JIEBANG_SPIDER_MAX_PAGES", "0"))
        if configured_max_pages > 0:
            total_pages = min(total_pages, configured_max_pages)
        logger.info("===== %s 爬虫启动 =====", self.name)

        exhausted = False
        for page_num in range(1, total_pages + 1):
            logger.info("正在采集第 %d/%d 页...", page_num, total_pages)
            try:
                records = self.parse(page_num)
                self.stats["pages"] += 1
                if not records:
                    exhausted = True
                    break
                for r in records:
                    self.add_job(r)
                logger.info("  本页提取 %d 条", len(records))
                if self.max_records and len(self.observed_data) >= self.max_records:
                    break
            except Exception as e:
                logger.error("  第 %d 页出错: %s", page_num, e)
                self.stats["errors"] += 1

        self.snapshot_complete = (
            exhausted
            and self.stats["errors"] == 0
            and not (self.max_records and len(self.observed_data) >= self.max_records)
        )
        self.print_stats()
        return self.save()

    # ============================================================
    # 辅助方法
    # ============================================================

    @staticmethod
    def _fingerprint(record: dict) -> str:
        """生成记录的去重指纹（URL + 标题）"""
        return identity_fingerprint(record)

    @staticmethod
    def _content_digest(records: list[dict]) -> str:
        """生成与顺序、抓取时间无关的业务内容指纹。"""
        normalized = []
        for record in records:
            item = {key: value for key, value in record.items() if key != "crawled_at"}
            source_meta = item.get("source_meta")
            if isinstance(source_meta, dict):
                item["source_meta"] = {
                    key: value for key, value in source_meta.items()
                    if key != "snapshot_observed_at"
                }
            normalized.append(item)
        normalized.sort(
            key=lambda item: (
                str(item.get("url") or ""),
                str(item.get("title") or ""),
                json.dumps(item, ensure_ascii=False, sort_keys=True),
            )
        )
        payload = json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _observation_day(records: list[dict]) -> str:
        """Return the snapshot day used for daily observation versioning."""
        days = sorted({
            str(record.get("crawled_at") or "")[:10]
            for record in records
            if str(record.get("crawled_at") or "")[:10]
        })
        return days[-1] if days else ""
