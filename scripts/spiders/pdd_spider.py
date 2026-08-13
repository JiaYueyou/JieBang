"""Collect public PDD social-recruitment technical positions in a browser.

The site generates its request integrity field in the normal page runtime.  We
only click the public technical filter and read the resulting public responses;
the collector never generates, decodes, or bypasses that field itself.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import logging
from pathlib import Path
import re
import sys
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_framework import BaseSpider
from spider_framework.tech_scope import classify_tech_scope


LOGGER = logging.getLogger("spider.pdd")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"p", "br", "li", "div"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self.parts)).strip()


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    return parser.text()


def parse_portal_date(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).astimezone()
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("/", "-")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


class PddSpider(BaseSpider):
    name = "pdd"
    source_name = "拼多多官方社会招聘门户（careers.pddglobalhr.com）"
    default_config = {"request_interval": 1.0, "retry_times": 1, "timeout": 60}
    entry_url = "https://careers.pddglobalhr.com/jobs"
    list_path = "/api/recruit/position/list"
    detail_path = "/api/recruit/position/detail"

    def __init__(
        self,
        *,
        start_date: date,
        end_date: date,
        max_pages: int = 60,
        headed: bool = False,
    ) -> None:
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.max_pages = max(1, max_pages)
        self.headed = headed

    def parse(self, page_num: int) -> list[dict]:
        raise RuntimeError("PDD collection uses the browser-driven run() workflow")

    @staticmethod
    def _response_payload(response) -> dict:
        if response.status != 200:
            raise RuntimeError(
                "PDD public page rejected its generated request; stop without "
                "attempting to reproduce or bypass the site's integrity field"
            )
        body = response.json()
        if not body.get("success") or not isinstance(body.get("result"), dict):
            raise RuntimeError("PDD public jobs response does not contain a usable result")
        return body["result"]

    def run(self):
        from playwright.sync_api import sync_playwright

        list_items: list[dict] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=not self.headed)
            context = browser.new_context(locale="zh-CN", viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.goto(self.entry_url, wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(2_000)

            with page.expect_response(
                lambda response: self.list_path in response.url,
                timeout=30_000,
            ) as response_info:
                page.get_by_text("技术", exact=True).click()
            result = self._response_payload(response_info.value)
            list_items.extend(result.get("list") or [])
            total = int(result.get("total") or len(list_items))
            total_pages = min(self.max_pages, max(1, (total + 9) // 10))
            self.stats["pages"] = 1

            for page_number in range(2, total_pages + 1):
                LOGGER.info("正在采集第 %s/%s 页...", page_number, total_pages)
                next_button = page.locator(".ant-pagination-next")
                if next_button.count() == 0 or "ant-pagination-disabled" in (next_button.get_attribute("class") or ""):
                    break
                with page.expect_response(
                    lambda response: self.list_path in response.url,
                    timeout=30_000,
                ) as response_info:
                    next_button.click()
                page_result = self._response_payload(response_info.value)
                list_items.extend(page_result.get("list") or [])
                self.stats["pages"] += 1

            detail_page = context.new_page()
            crawled_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
            for index, item in enumerate(list_items, start=1):
                code = str(item.get("code") or "").strip()
                if not code:
                    continue
                LOGGER.info("正在读取岗位详情 %s/%s: %s", index, len(list_items), code)
                detail_url = f"{self.entry_url}/detail?code={code}"
                try:
                    with detail_page.expect_response(
                        lambda response: self.detail_path in response.url,
                        timeout=30_000,
                    ) as response_info:
                        detail_page.goto(detail_url, wait_until="networkidle", timeout=60_000)
                    detail = self._response_payload(response_info.value)
                    record = self.normalize_job(detail, crawled_at=crawled_at, detail_url=detail_url)
                    if record:
                        self.add_job(record)
                except Exception as exc:
                    LOGGER.warning("跳过无法读取的 PDD 岗位 %s: %s", code, exc)
                    self.stats["errors"] += 1
            browser.close()
        self.print_stats()
        return self.save()

    def normalize_job(self, item: dict, *, crawled_at: str, detail_url: str) -> dict | None:
        title = str(item.get("name") or "").strip()
        responsibilities = html_to_text(str(item.get("jobDuty") or ""))
        requirements = html_to_text(str(item.get("serveRequirement") or ""))
        bonus = html_to_text(str(item.get("bonus") or ""))
        description = "\n\n".join(value for value in (responsibilities, requirements, bonus) if value)
        category = str(item.get("job") or "").strip()
        decision = classify_tech_scope(title=title, category=category, description=description)
        updated = parse_portal_date(item.get("updateTime") or item.get("updateDate"))
        if (
            not decision.in_scope
            or not title
            or len(description) < 10
            or updated is None
            or not (self.start_date <= updated.date() <= self.end_date)
        ):
            return None
        code = str(item.get("code") or "").strip()
        if not code:
            return None
        location = item.get("workLocation") or ""
        if isinstance(location, list):
            location = "、".join(str(value) for value in location if value)
        return {
            "title": title,
            "company": "拼多多",
            "city": str(location).strip() or None,
            "salary": None,
            "experience": None,
            "education": None,
            "jd_text": "【岗位职责】\n" + responsibilities + "\n\n【任职要求】\n" + requirements,
            "responsibilities": responsibilities or None,
            "requirements": requirements or None,
            "keywords": list(decision.matched_terms),
            # PDD publishes an update time, not a first-post time.  Keep the
            # canonical publication field empty and retain the real semantics.
            "posted_at": None,
            "url": detail_url,
            "external_id": code,
            "source": self.source_name,
            "source_type": "official_careers_site",
            "crawled_at": crawled_at,
            "source_meta": {
                "portal_key": "pdd_official_social",
                "portal_host": "careers.pddglobalhr.com",
                "collector": "pdd_public_browser",
                "category": category,
                "recruit_type": item.get("recruitType"),
                "scope_reason": decision.reason,
                "scope_evidence": list(decision.matched_terms),
                "source_updated_at": updated.isoformat(timespec="seconds"),
                "date_semantics": "updated_at",
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect public PDD technical jobs")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--max-pages", type=int, default=60)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    if start_date > end_date:
        raise SystemExit("--start-date must not be after --end-date")
    spider = PddSpider(
        start_date=start_date,
        end_date=end_date,
        max_pages=args.max_pages,
        headed=args.headed,
    )
    spider.save_output_dir = args.output_dir
    spider.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main()
