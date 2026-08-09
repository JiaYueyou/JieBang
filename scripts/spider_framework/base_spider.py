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
from typing import Optional

import requests

from .schema import validate_all

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
        self.max_records = max(0, int(os.getenv("JIEBANG_SPIDER_MAX_RECORDS", "0")))
        self.seen_ids = set()  # 去重用

        # ---------- 运行时统计 ----------
        self.stats = {
            "fetched": 0,       # 已抓取条数
            "duplicates": 0,    # 去重跳过
            "errors": 0,        # 错误次数
            "pages": 0,         # 已爬页数
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
        if self.max_records and len(self.total_data) >= self.max_records:
            return False

        # 生成指纹
        fp = self._fingerprint(record)
        if fp in self.seen_ids:
            self.stats["duplicates"] += 1
            return False
        self.seen_ids.add(fp)

        # 补充默认字段
        record.setdefault("source", self.source_name)
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
        data = self.total_data
        if not data:
            logger.warning("⚠️ 没有数据可保存")
            return ""

        validation = validate_all(data, verbose=False)
        if validation["failed"]:
            first = validation["errors"][0]
            raise ValueError(
                "job-v1 schema validation failed before snapshot write: "
                f"record={first['index']} errors={first['errors']}"
            )

        output_dir = output_dir or self.save_output_dir or os.getcwd()
        new_count = len(data)
        new_digest = self._content_digest(data)

        # 自动编号
        pattern = re.compile(rf"^{re.escape(self.name)}_(\d+)\.json$")
        max_num = 0
        for fname in os.listdir(output_dir):
            m = pattern.match(fname)
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num

        # 比较业务内容而不是记录数，避免“数量相同但岗位内容变化”被漏掉。
        # crawled_at 属于本次运行元数据，不参与业务内容指纹。
        if max_num > 0:
            latest_path = os.path.join(output_dir, f"{self.name}_{max_num}.json")
            try:
                with open(latest_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                if (
                    self._content_digest(existing_data) == new_digest
                    and self._observation_day(existing_data)
                    == self._observation_day(data)
                ):
                    logger.info("业务内容无变化 (%d 条)，复用快照 %s",
                                new_count, f"{self.name}_{max_num}.json")
                    return latest_path
            except (json.JSONDecodeError, OSError):
                pass  # 文件损坏则正常保存

        filename = f"{self.name}_{max_num + 1}.json"
        filepath = os.path.join(output_dir, filename)

        # 按发布时间从新到旧排序
        data.sort(
            key=lambda x: x.get("posted_at") or x.get("post_date") or "",
            reverse=True,
        )

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        logger.info("已保存: %s (%d 条, %d 字段)",
                    filepath, new_count, len(data[0]) if data else 0)
        return filepath

    def print_stats(self):
        """打印运行时统计"""
        logger.info("=" * 40)
        logger.info("爬虫统计 [%s]", self.name)
        logger.info("  抓取成功: %d 条", self.stats["fetched"])
        logger.info("  去重跳过: %d 条", self.stats["duplicates"])
        logger.info("  错误次数: %d 次", self.stats["errors"])
        logger.info("  已爬页数: %d 页", self.stats["pages"])
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

        for page_num in range(1, total_pages + 1):
            logger.info("正在采集第 %d/%d 页...", page_num, total_pages)
            try:
                records = self.parse(page_num)
                self.stats["pages"] += 1
                for r in records:
                    self.add_job(r)
                logger.info("  本页提取 %d 条", len(records))
                if self.max_records and len(self.total_data) >= self.max_records:
                    break
            except Exception as e:
                logger.error("  第 %d 页出错: %s", page_num, e)
                self.stats["errors"] += 1

        self.print_stats()
        return self.save()

    # ============================================================
    # 辅助方法
    # ============================================================

    @staticmethod
    def _fingerprint(record: dict) -> str:
        """生成记录的去重指纹（URL + 标题）"""
        external_id = str(record.get("external_id") or "").strip()
        source = str(record.get("source") or "").strip()
        if external_id:
            # Listing URLs and titles are not unique requisition identities.
            raw = f"external:{source}|{external_id}"
            return hashlib.md5(raw.encode("utf-8")).hexdigest()
        url = (record.get("url") or "").strip()
        title = (record.get("title") or "").strip()
        raw = f"fallback:{url}|{title}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _content_digest(records: list[dict]) -> str:
        """生成与顺序、抓取时间无关的业务内容指纹。"""
        normalized = []
        for record in records:
            item = {key: value for key, value in record.items() if key != "crawled_at"}
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
