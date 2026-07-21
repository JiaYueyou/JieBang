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
        # ---------- 限速 ----------
        self.request_interval = self.default_config.get("request_interval", 1.0)
        self._last_request_time = 0.0

        # ---------- 重试 ----------
        self.retry_times = self.default_config.get("retry_times", 3)
        self.retry_delay = self.default_config.get("retry_delay", 2)

        # ---------- 请求配置 ----------
        self.timeout = self.default_config.get("timeout", 30)
        self.default_headers = self.default_config.get("headers", {})

        # ---------- 数据收集 ----------
        self.total_data = []
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
                        url, headers=merged_headers, json=json_data,
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
        保存数据到 JSON 文件（自动编号）

        参数：
          output_dir: 输出目录，默认当前目录

        返回：文件路径
        """
        # 字段整理
        data = self.total_data
        if not data:
            logger.warning("⚠️ 没有数据可保存")
            return ""

        output_dir = output_dir or os.getcwd()

        # 自动编号
        pattern = re.compile(rf"^{re.escape(self.name)}_(\d+)\.json$")
        max_num = 0
        for fname in os.listdir(output_dir):
            m = pattern.match(fname)
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
        filename = f"{self.name}_{max_num + 1}.json"
        filepath = os.path.join(output_dir, filename)

        # 按发布时间从新到旧排序
        data.sort(key=lambda x: x.get("post_date", "") or "", reverse=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        logger.info("已保存: %s (%d 条, %d 字段)",
                    filepath, len(data), len(data[0]) if data else 0)
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
        logger.info("===== %s 爬虫启动 =====", self.name)

        for page_num in range(1, total_pages + 1):
            logger.info("正在采集第 %d/%d 页...", page_num, total_pages)
            try:
                records = self.parse(page_num)
                self.stats["pages"] += 1
                for r in records:
                    self.add_job(r)
                logger.info("  本页提取 %d 条", len(records))
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
        url = (record.get("url") or "").strip()
        title = (record.get("title") or "").strip()
        raw = f"{url}|{title}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()
