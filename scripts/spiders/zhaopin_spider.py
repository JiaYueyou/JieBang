# -*- coding: utf-8 -*-
"""
智联招聘 — 爬虫（重构版）

使用 BaseSpider 框架 + Playwright 浏览器自动化
配置：configs/zhaopin.yaml
"""

import json
import datetime
import re
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spider_framework import BaseSpider, SpiderConfig, validate_all


class ZhaopinSpider(BaseSpider):
    """智联招聘爬虫（Playwright 驱动）"""

    name = "zhaopin"
    source_name = "智联招聘"

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "..", "configs", "zhaopin.yaml"
            )
        self.config = SpiderConfig.load(config_path)
        self.default_config = self.config.to_dict()
        super().__init__()

        self._browser = None
        self._context = None
        self._page = None

        # 近三个月过滤
        self.three_months_ago = datetime.datetime.now() - datetime.timedelta(days=90)

    # ============================================================
    # 重写 run() — Playwright 特殊流程
    # ============================================================

    def run(self):
        """智联爬虫主流程：使用 Playwright 逐页访问"""
        from playwright.sync_api import sync_playwright

        logger = self._get_logger()
        logger.info("===== 智联招聘爬虫启动 =====")

        with sync_playwright() as p:
            self._browser = p.chromium.launch(headless=True)
            self._context = self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/148.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            self._page = self._context.new_page()

            # 拦截 API 响应
            self._page.on("response", self._handle_response)

            total_pages = self.config.total_pages
            for page_num in range(1, total_pages + 1):
                logger.info("正在采集第 %d/%d 页...", page_num, total_pages)
                url = self.config.to_dict().get(
                    "page_url_template",
                    f"https://www.zhaopin.com/sou/jl489/kwF78LI9SBLUCDS/p{page_num}",
                ).format(page=page_num)

                try:
                    self._page.goto(url, timeout=self.timeout * 1000)
                    self._page.wait_for_timeout(5000)
                    self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    self._page.wait_for_timeout(2000)
                    self.stats["pages"] += 1
                except Exception as e:
                    logger.error("  第 %d 页加载失败: %s", page_num, e)
                    self.stats["errors"] += 1

            self._browser.close()

        self.print_stats()
        return self.save()

    def _handle_response(self, response):
        """拦截 API 响应并提取岗位数据"""
        if "/c/i/search/positions" not in response.url:
            return
        try:
            data = response.json()
            results = data.get("data", {}).get("list", []) or []
        except Exception:
            return

        records = self._extract_from_api(results)
        for r in records:
            self.add_job(r)
        logger = self._get_logger()
        logger.info("  本页提取 %d 条", len(records))

    def _extract_from_api(self, results: list) -> list[dict]:
        """从智联 API 结果中提取标准字段"""
        records = []

        for job in results:
            job_id = job.get("jobId")
            if not job_id:
                continue

            title = job.get("name", "")
            if not title:
                continue

            # 发布日期过滤（近三个月）
            publish_time = job.get("publishTime", "") or ""
            if publish_time:
                try:
                    pub_date = datetime.datetime.strptime(
                        publish_time, "%Y-%m-%d %H:%M:%S"
                    )
                    if pub_date < self.three_months_ago:
                        continue
                except ValueError:
                    pass

            # 城市
            work_city = job.get("workCity", "") or ""
            city_district = job.get("cityDistrict", "") or ""
            city = f"{work_city}-{city_district}" if city_district else work_city

            # JD 全文
            jd_detail = job.get("jobDetailData", {}) or {}
            position_data = jd_detail.get("position", {}) or {}
            desc_data = position_data.get("desc", {}) or {}
            jd_text = desc_data.get("description", "") or ""

            # 分离职责和任职要求
            duty, require = self._split_jd(jd_text) if jd_text else ("", "")

            # 技能标签
            skill_tags = job.get("skillLabel", []) or []
            keywords = [t.get("value", "") for t in skill_tags if t.get("value")]

            record = {
                "title": title,
                "company": job.get("companyName", "") or "未知",
                "city": city,
                "salary": job.get("salaryReal") or None,
                "experience": job.get("workingExp") or None,
                "education": job.get("education") or None,
                "jd_text": jd_text,
                "duty": duty or None,
                "require": require or None,
                "keywords": keywords,
                "post_date": publish_time,
                "url": job.get("positionURL") or job.get("positionUrl") or "",
                "source": self.source_name,
                "crawled_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            records.append(record)

        return records

    # ============================================================
    # JD 分离工具
    # ============================================================

    @staticmethod
    def _split_jd(jd_text: str) -> tuple:
        """将 JD 文本分离为 duty 和 require"""
        separators = [
            r"(?:任职要求|岗位要求|职位要求|任职资格|资格要求)[：:\s]",
            r"(?:我们希望你)[：:\s]",
        ]
        req_match = None
        for pat in separators:
            m = re.search(pat, jd_text)
            if m:
                req_match = m
                break

        if req_match:
            duty_text = jd_text[:req_match.start()].strip()
            # 去掉职责标题
            for p in [r"(?:【岗位职责】|【职责描述】|【工作职责】|职位描述)[：:\s]?"]:
                duty_text = re.sub(p, "", duty_text).strip()
            require_text = jd_text[req_match.start():].strip()
            for p in separators:
                require_text = re.sub(p, "", require_text).strip()
            return duty_text, require_text

        # 没找到分隔，按换行分半
        lines = jd_text.strip().split("\n")
        mid = len(lines) // 2
        return "\n".join(lines[:mid]).strip(), "\n".join(lines[mid:]).strip()

    # ============================================================
    # 不继承 run() 的默认实现，用上面的重写版本
    # 但提供 parse() 以免基类报错
    # ============================================================

    def parse(self, page_num: int) -> list[dict]:
        """智联爬虫不走 parse() 流程，请使用 run()"""
        return []

    @staticmethod
    def _get_logger():
        import logging
        return logging.getLogger("spider.zhaopin")


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="智联招聘爬虫")
    parser.add_argument("--output-dir", default=None, help="输出目录（默认当前目录）")
    args = parser.parse_args()

    spider = ZhaopinSpider()
    if args.output_dir:
        spider.save_output_dir = args.output_dir
    filepath = spider.run()

    if filepath and os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = validate_all(data)
        print(f"\nSchema 校验: 通过 {result['passed']}/{result['total']} 条"
              f" ({result['pass_rate']})")
        if result["failed"] > 0:
            print(f"失败 {result['failed']} 条，详情见日志")
