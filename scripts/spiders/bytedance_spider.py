# -*- coding: utf-8 -*-
"""Collect a bounded set of public ByteDance careers listings via its normal UI.

The collector navigates the public ``/experienced/position`` result pages in a
browser.  It does not call the signed backend directly, use a login state, or
handle CAPTCHA / other access controls.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from playwright.sync_api import Response, sync_playwright


LOGGER = logging.getLogger("spider.bytedance")
BASE_URL = "https://jobs.bytedance.com/experienced/position"
SEARCH_PATH = "/api/v1/search/job/posts"
DEFAULT_KEYWORDS = ("人工智能", "大模型", "算法", "机器学习", "AIGC", "推荐")


class ByteDanceSpider:
    """Use ordinary official-careers search pages to collect technical roles."""

    name = "bytedance_official"
    # Keep the established source key so records deduplicate by public detail URL.
    # The record metadata below preserves that this is an official careers site.
    source_name = "字节跳动招聘"

    def __init__(
        self,
        *,
        start_date: dt.date,
        end_date: dt.date,
        keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
        pages_per_keyword: int = 2,
        request_interval: float = 2.0,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.keywords = keywords
        self.pages_per_keyword = max(1, pages_per_keyword)
        self.request_interval = max(1.0, request_interval)
        self.records: list[dict[str, Any]] = []
        self._seen_ids: set[str] = set()

    def run(self) -> list[dict[str, Any]]:
        """Navigate public results, without a login or access-control bypass."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(locale="zh-CN", viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("response", self._handle_response)

            for keyword in self.keywords:
                for page_number in range(1, self.pages_per_keyword + 1):
                    LOGGER.info("Collecting ByteDance careers: keyword=%s page=%s", keyword, page_number)
                    page.goto(self._build_search_url(keyword, page_number), wait_until="networkidle", timeout=45_000)
                    page.wait_for_timeout(1_000)
                    time.sleep(self.request_interval)
            browser.close()
        return self.records

    @staticmethod
    def _build_search_url(keyword: str, page_number: int) -> str:
        return f"{BASE_URL}?{urlencode({'keywords': keyword, 'category': '', 'location': '', 'project': '', 'type': '', 'job_hot_flag': '', 'current': page_number, 'limit': 10, 'functionCategory': '', 'tag': ''})}"

    def _handle_response(self, response: Response) -> None:
        if SEARCH_PATH not in response.url or response.status != 200:
            return
        try:
            jobs = response.json().get("data", {}).get("job_post_list", [])
        except Exception as exc:
            LOGGER.warning("Ignoring an unreadable public jobs response: %s", exc)
            return
        for job in jobs:
            record = self.normalize_job(job)
            if record is None:
                continue
            job_id = str(job.get("id") or record["url"])
            if job_id not in self._seen_ids:
                self._seen_ids.add(job_id)
                self.records.append(record)

    def normalize_job(self, job: dict[str, Any]) -> dict[str, Any] | None:
        posted_at = self._to_datetime(job.get("publish_time"))
        if posted_at is None or not (self.start_date <= posted_at.date() <= self.end_date):
            return None
        title = str(job.get("title") or "").strip()
        description = str(job.get("description") or "").strip()
        requirement = str(job.get("requirement") or "").strip()
        job_id = str(job.get("id") or "").strip()
        if not title or not job_id or not (description or requirement):
            return None

        city_list = job.get("city_list") or []
        cities = [str(item.get("name") or "").strip() for item in city_list if isinstance(item, dict)]
        if not cities and isinstance(job.get("city_info"), dict):
            cities = [str(job["city_info"].get("name") or "").strip()]
        category = job.get("job_category") or {}
        category_name = str(category.get("name") or "").strip()
        jd_text = "\n\n".join(part for part in (
            f"【岗位职责】\n{description}" if description else "",
            f"【任职要求】\n{requirement}" if requirement else "",
        ) if part)
        return {
            "title": title,
            "company": "字节跳动",
            "city": "、".join(city for city in cities if city) or "未注明",
            "salary": None,
            "experience": None,
            "education": None,
            "jd_text": jd_text,
            "responsibilities": description or None,
            "requirements": requirement or None,
            "keywords": [category_name] if category_name else [],
            "posted_at": posted_at.strftime("%Y-%m-%d %H:%M:%S"),
            "url": f"https://jobs.bytedance.com/experienced/position/{job_id}/detail",
            "external_id": job_id,
            "source": self.source_name,
            "source_type": "official_careers_site",
            "crawled_at": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
            "source_meta": {
                "source_type": "official_careers_site",
                "collector": self.name,
                "job_code": job.get("code"),
                "category": category_name or None,
            },
        }

    @staticmethod
    def _to_datetime(value: Any) -> dt.datetime | None:
        if not isinstance(value, (int, float)):
            return None
        try:
            return dt.datetime.fromtimestamp(value / 1000, tz=dt.timezone.utc).astimezone()
        except (OverflowError, OSError, ValueError):
            return None


def save_records(records: list[dict[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"bytedance_official_{dt.datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect public ByteDance AI/internet job listings")
    parser.add_argument("--start-date", default="2026-01-01")
    parser.add_argument("--end-date", default=dt.date.today().isoformat())
    parser.add_argument("--pages-per-keyword", type=int, default=2)
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()
    start_date, end_date = dt.date.fromisoformat(args.start_date), dt.date.fromisoformat(args.end_date)
    if start_date > end_date:
        raise SystemExit("--start-date must not be after --end-date")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    records = ByteDanceSpider(start_date=start_date, end_date=end_date, pages_per_keyword=args.pages_per_keyword).run()
    output_path = save_records(records, Path(args.output_dir))
    LOGGER.info("Saved %s public ByteDance records to %s", len(records), output_path)


if __name__ == "__main__":
    main()
