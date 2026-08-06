# -*- coding: utf-8 -*-
"""
字节跳动官网 — 爬虫

使用 BaseSpider 框架，混合方案：
  1. Playwright 引导：打开职位页拦截搜索请求，获取合法会话
     （_signature 反爬签名 + x-csrf-token + cookies）
  2. requests 分页：按岗位类别（叶子类别）分区全量抓取，
     因为接口无发布时间过滤且单次搜索最多返回 10000 条，
     必须按类别分区才能覆盖全部岗位，最后在客户端按发布时间
     过滤出近三个月的岗位。

配置：configs/bytedance.yaml
"""

import json
import datetime
import re
import os
import sys
import time
import logging
import requests
from urllib.parse import urlparse, parse_qsl

# 把项目根目录加到 path，方便直接运行
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spider_framework import BaseSpider, SpiderConfig, validate_all

logger = logging.getLogger("spider.bytedance")


class ByteDanceSpider(BaseSpider):
    """字节跳动官网社会化招聘爬虫（近三个月）"""

    name = "bytedance"
    source_name = "字节跳动招聘"

    def __init__(self, config_path: str = None):
        # 加载配置
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "..", "configs", "bytedance.yaml"
            )
        self.config = SpiderConfig.load(config_path)
        self.default_config = self.config.to_dict()
        super().__init__()

        # ---- 会话相关（Playwright 引导获取）----
        self._session_ready = False
        self._cookies = {}
        self._headers = {}
        self._signature = ""
        self._base_qs = {}

        # ---- 近三个月过滤（客户端）----
        self.months_back = (self.config.filters or {}).get("months_back", 3)
        self.cutoff_time = datetime.datetime.now() - datetime.timedelta(days=30 * self.months_back)
        self.cutoff_ms = int(self.cutoff_time.timestamp() * 1000)

        # ---- 技能关键词（从 JD 中提取 keywords）----
        self.skill_keywords = [
            "Python", "Java", "C++", "Go", "Rust", "Scala", "JavaScript",
            "TypeScript", "SQL", "Spark", "Flink", "Hadoop", "Kafka", "Redis",
            "MySQL", "Elasticsearch", "Docker", "Kubernetes", "PyTorch",
            "TensorFlow", "LLM", "NLP", "RAG", "Agent", "大模型", "机器学习",
            "深度学习", "算法", "推荐系统", "计算机视觉", "语音识别", "多模态",
            "数据分析", "数据挖掘", "大数据", "分布式", "微服务", "高并发",
            "pipeline", "模型优化", "特征工程", "预训练", "微调", "推理加速",
        ]

        # 先引导获取会话（失败则抛出）
        self._bootstrap()

    # ============================================================
    # Playwright 引导 — 获取合法会话
    # ============================================================

    def _bootstrap(self):
        """打开职位页，拦截一次成功的搜索请求，捕获签名/CSRF/cookies"""
        from playwright.sync_api import sync_playwright

        bootstrap_url = self.default_config.get("bootstrap_url") or (
            "https://jobs.bytedance.com/experienced/position"
        )
        captured = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/148.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            def on_response(resp):
                if "/search/job/posts" in resp.url and resp.status == 200 and "url" not in captured:
                    captured["url"] = resp.url
                    captured["headers"] = dict(resp.request.headers)
                    captured["post_data"] = resp.request.post_data

            page.on("response", on_response)
            page.goto(bootstrap_url, timeout=60000)
            # 等待页面加载 + 首次搜索请求（含 405->重算签名->200 的往返）
            page.wait_for_timeout(12000)
            captured["cookies"] = context.cookies()
            browser.close()

        if "url" not in captured:
            raise RuntimeError("引导失败：页面未发出成功的搜索请求（可能需要验证码）")

        parsed = urlparse(captured["url"])
        qs = dict(parse_qsl(parsed.query))
        self._signature = qs.pop("_signature", "")
        self._base_qs = qs

        self._cookies = {ck["name"]: ck["value"] for ck in captured["cookies"]}

        keep_keys = {
            "website-path", "x-csrf-token", "referer", "accept-language",
            "portal-channel", "portal-platform", "user-agent", "accept",
            "env", "content-type",
        }
        self._headers = {
            k: v for k, v in captured["headers"].items() if k in keep_keys
        }
        self._headers.setdefault("User-Agent", (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        ))
        self._session_ready = True
        logger.info("✅ 引导成功：已获取签名与会话 (_signature=%s…, cookies=%d)",
                    self._signature[:10], len(self._cookies))

    # ============================================================
    # 请求封装（签名失效时自动重新引导）
    # ============================================================

    def _api_fetch(self, body: dict, offset: int, limit: int) -> dict:
        """调用搜索接口，返回 JSON。签名失效时自动重新引导重试一次"""
        try:
            return self._do_request(body, offset, limit)
        except Exception:
            logger.warning("请求失败，尝试重新引导会话后重试...")
            self._bootstrap()
            return self._do_request(body, offset, limit)

    def _do_request(self, body: dict, offset: int, limit: int) -> dict:
        params = dict(self._base_qs)
        params["keyword"] = ""
        params["limit"] = limit
        params["offset"] = offset
        params["_signature"] = self._signature
        qs_str = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self.config.base_url}?{qs_str}"

        req_body = dict(self.config.request_body_template or {})
        req_body.update(body)
        req_body["limit"] = limit
        req_body["offset"] = offset

        # 限速
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self._last_request_time = time.time()

        resp = requests.post(
            url, headers=self._headers, cookies=self._cookies,
            json=req_body, timeout=self.config.timeout,
        )
        if resp.status_code in (401, 403, 405, 429):
            raise RuntimeError(f"接口返回 {resp.status_code}，会话可能失效")

        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"接口返回错误: {data.get('message')}")
        return data

    # ============================================================
    # 主流程（重写 run）— 类别分区全量抓取 + 近三个月过滤
    # ============================================================

    def run(self):
        logger.info("===== 字节跳动爬虫启动（并集抓取 + 近三个月过滤） =====")

        all_jobs = {}          # job_id -> raw dict（跨来源去重）

        # 1. 未过滤搜索：按排序抓取前 10000 条（新发布的岗位排名靠前，
        #    实测可完整覆盖近三个月岗位）
        logger.info("— 第 1 步：未过滤搜索抓取前 10000 条 —")
        unfiltered_total = 0
        for offset in range(0, 20000, self.config.page_size):
            jobs = self._fetch_chunk({}, offset)
            unfiltered_total += len(jobs)
            for j in jobs:
                jid = j.get("id")
                if jid and jid not in all_jobs:
                    all_jobs[jid] = j
            if len(jobs) < self.config.page_size:
                break
        logger.info("  未过滤搜索抓取 %d 条（去重后 %d）", unfiltered_total, len(all_jobs))

        # 2. 类别分区补充抓取：确保覆盖全部岗位
        logger.info("— 第 2 步：按类别分区补充抓取 —")
        categories = self._get_leaf_categories()
        logger.info("  获取到 %d 个岗位类别", len(categories))
        for cat_id, cat_name in categories:
            jobs = self._fetch_category(cat_id)
            added = 0
            for j in jobs:
                jid = j.get("id")
                if jid and jid not in all_jobs:
                    all_jobs[jid] = j
                    added += 1
            if added:
                logger.info("  [%s] 抓取 %d 条（新增 %d，累计 %d）",
                            cat_name, len(jobs), added, len(all_jobs))

        logger.info("全量抓取完成：去重后共 %d 条", len(all_jobs))

        # 3. 近三个月过滤（客户端）
        recent = []
        for j in all_jobs.values():
            pt = j.get("publish_time")
            if pt and pt >= self.cutoff_ms:
                recent.append(j)
        logger.info("近 %d 个月岗位：%d 条", self.months_back, len(recent))

        # 4. 转为标准 schema 记录
        records = []
        for j in recent:
            rec = self._build_record(j)
            if rec:
                records.append(rec)
        self.total_data = records
        self.stats["fetched"] = len(records)

        self.print_stats()
        return self.save()

    # ============================================================
    # 类别相关
    # ============================================================

    def _get_leaf_categories(self) -> list:
        """从 config/job/filters 接口获取叶子类别 (id, name)"""
        filter_url = "https://jobs.bytedance.com/api/v1/config/job/filters/"
        try:
            resp = requests.get(
                filter_url, headers=self._headers, cookies=self._cookies,
                timeout=self.config.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            self._bootstrap()
            resp = requests.get(
                filter_url, headers=self._headers, cookies=self._cookies,
                timeout=self.config.timeout,
            )
            data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"获取类别失败: {data}")

        def walk(node, path=""):
            name = node.get("name") or ""
            cur = f"{path}/{name}" if path else name
            children = node.get("children") or []
            if not children:
                return [(node.get("id"), cur)]
            result = []
            for ch in children:
                result.extend(walk(ch, cur))
            return result

        leaves = []
        for top in (data.get("data") or {}).get("job_type_list") or []:
            leaves.extend(walk(top))
        return [l for l in leaves if l[0]]

    def _fetch_chunk(self, body: dict, offset: int) -> list:
        """抓取一个分块（不附加类别过滤）"""
        data = self._api_fetch(body, offset, self.config.page_size)
        return (data.get("data") or {}).get("job_post_list") or []

    def _fetch_category(self, cat_id: str) -> list:
        """抓取某个叶子类别的全部岗位（分页直到取完）"""
        results = []
        page_size = self.config.page_size
        offset = 0
        body = {"job_category_id_list": [cat_id]}

        while True:
            data = self._api_fetch(body, offset, page_size)
            job_list = (data.get("data") or {}).get("job_post_list") or []
            results.extend(job_list)
            if len(job_list) < page_size:
                break
            offset += page_size
            if offset > 20000:   # 安全上限
                break
        return results

    # ============================================================
    # 字段构建
    # ============================================================

    def _build_record(self, job: dict) -> dict:
        title = (job.get("title") or "").strip()
        if not title:
            return None

        description = (job.get("description") or "").strip()
        requirement = (job.get("requirement") or "").strip()

        jd_parts = []
        if description:
            jd_parts.append("【工作职责】\n" + description)
        if requirement:
            jd_parts.append("【任职要求】\n" + requirement)
        jd_text = "\n\n".join(jd_parts)

        combined = f"{description} {requirement}"
        keywords = self._extract_skills(combined)

        exp = self._extract_experience(requirement)
        edu = self._extract_education(requirement)
        city = self._extract_city(job)

        post_date = self._format_post_date(job.get("publish_time"))
        job_id = job.get("id") or ""
        url = f"https://jobs.bytedance.com/experienced/position/{job_id}/detail" if job_id else ""

        return {
            "title": title,
            "company": "字节跳动",
            "city": city,
            "salary": None,  # 字节跳动不公开薪资
            "experience": exp,
            "education": edu,
            "jd_text": jd_text,
            "responsibilities": description if description else None,
            "requirements": requirement if requirement else None,
            "keywords": keywords,
            "posted_at": post_date,
            "url": url,
            "source": self.source_name,
            "crawled_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    # ============================================================
    # 辅助方法
    # ============================================================

    @staticmethod
    def _extract_city(job: dict) -> str:
        cities = []
        ci = job.get("city_info") or {}
        if ci.get("name"):
            cities.append(ci["name"])
        for c in (job.get("city_list") or []):
            if isinstance(c, dict) and c.get("name"):
                cities.append(c["name"])
        seen = set()
        uniq = []
        for c in cities:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        return "、".join(uniq)

    @staticmethod
    def _format_post_date(ms) -> str:
        if not ms:
            return ""
        try:
            return datetime.datetime.fromtimestamp(int(ms) / 1000).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except Exception:
            return ""

    def _extract_skills(self, text: str) -> list:
        if not text:
            return []
        found = []
        seen = set()
        pattern = re.compile(
            r"(" + "|".join(re.escape(k) for k in self.skill_keywords) + r")",
            re.IGNORECASE,
        )
        for match in pattern.findall(text):
            key = match.lower()
            if key not in seen:
                seen.add(key)
                found.append(match)
        return found

    @staticmethod
    def _extract_experience(text: str) -> str:
        if not text:
            return "经验不限"
        patterns = [
            r"(\d+年及以上)", r"(\d+-\d+年)", r"(\d+年以上)",
            r"(\d+年)工作经验", r"(\d+年)", r"应届生", r"不限",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                raw = m.group(1) if m.groups() else m.group()
                return raw if raw != "不限" else "经验不限"
        return "经验不限"

    @staticmethod
    def _extract_education(text: str) -> str:
        if not text:
            return "学历不限"
        levels = ["高中", "中专", "大专", "专科", "本科", "学士",
                  "硕士", "研究生", "博士"]
        matches = []
        for level in levels:
            if re.search(level, text):
                matches.append(level)
        if not matches:
            return "学历不限"
        priority = {"博士": 6, "硕士": 5, "研究生": 5, "本科": 4,
                    "学士": 4, "大专": 3, "专科": 3, "中专": 2, "高中": 1}
        matches.sort(key=lambda x: priority.get(x, 0), reverse=True)
        return matches[0]

    def parse(self, page_num: int) -> list[dict]:
        """兼容基类接口（本爬虫不走 parse 流程，见 run()）"""
        return []


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    spider = ByteDanceSpider()
    filepath = spider.run()

    # 输出后自动校验 Schema
    if filepath and os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 输出文件使用 data_analysis 流水线字段（responsibilities/requirements/posted_at），
        # 校验前临时映射到 BaseSpider schema 字段名（duty/require/post_date）
        for rec in data:
            rec.setdefault("duty", rec.get("responsibilities"))
            rec.setdefault("require", rec.get("requirements"))
            rec.setdefault("post_date", rec.get("posted_at"))
        result = validate_all(data)
        print(f"\nSchema 校验: 通过 {result['passed']}/{result['total']} 条"
              f" ({result['pass_rate']})")
        if result["failed"] > 0:
            print(f"失败 {result['failed']} 条，详情见日志")
