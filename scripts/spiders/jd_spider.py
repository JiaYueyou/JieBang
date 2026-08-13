"""Collect public JD social-recruitment technical positions."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_framework import BaseSpider
from spider_framework.tech_scope import classify_tech_scope


LOGGER = logging.getLogger("spider.jd")
CHINA_STANDARD_TIME = timezone(timedelta(hours=8), name="Asia/Shanghai")


def timestamp_to_local(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            # JD publishes epoch milliseconds for its China recruitment portal.
            # Converting to the host's local timezone makes dates differ between
            # developer machines (UTC+8) and GitHub Actions runners (UTC).
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).astimezone(
                CHINA_STANDARD_TIME
            )
        except (ValueError, OSError, OverflowError):
            return None
    return None


class JdSpider(BaseSpider):
    name = "jd"
    source_name = "京东官方社会招聘门户（zhaopin.jd.com）"
    default_config = {"request_interval": 0.5, "retry_times": 3, "timeout": 30}
    api_url = "https://zhaopin.jd.com/web/job/job_list"
    entry_url = "https://zhaopin.jd.com/web/job/job_info_list/3"

    def __init__(self, *, start_date: date, end_date: date, max_pages: int = 200) -> None:
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.max_pages = max(1, max_pages)
        self._last_page_size = 0

    def parse(self, page_num: int) -> list[dict]:
        response = self.fetch(
            self.api_url,
            method="POST",
            data={
                "pageIndex": page_num,
                "pageSize": 50,
                "workCityJson": "[]",
                "jobTypeJson": json.dumps(["YANFA"], ensure_ascii=False),
                "jobSearch": "",
                "depTypeJson": "[]",
            },
            headers={"Referer": self.entry_url},
        )
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("JD public jobs endpoint returned a non-list payload")
        self._last_page_size = len(payload)
        crawled_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        records = []
        for item in payload:
            record = self.normalize_job(item, crawled_at=crawled_at)
            if record:
                records.append(record)
        return records

    def normalize_job(self, item: dict, *, crawled_at: str) -> dict | None:
        title = str(item.get("positionNameOpen") or item.get("positionName") or "").strip()
        responsibilities = str(item.get("workContent") or "").strip()
        requirements = str(item.get("qualification") or "").strip()
        description = "\n\n".join(value for value in (responsibilities, requirements) if value)
        category = str(item.get("jobType") or "").strip()
        department = str(item.get("positionDeptName") or "").strip()
        decision = classify_tech_scope(
            title=title,
            category=category,
            department=department,
            description=description,
        )
        published = timestamp_to_local(item.get("publishTime"))
        if published is None and item.get("formatPublishTime"):
            try:
                published = datetime.fromisoformat(str(item["formatPublishTime"]))
            except ValueError:
                published = None
        if (
            not decision.in_scope
            or not title
            or len(description) < 10
            or published is None
            or not (self.start_date <= published.date() <= self.end_date)
        ):
            return None
        external_id = str(item.get("positionId") or item.get("positionCode") or "").strip()
        if not external_id:
            return None
        return {
            "title": title,
            "company": department or "京东",
            "city": str(item.get("workCity") or "").strip() or None,
            "salary": None,
            "experience": None,
            "education": None,
            "jd_text": "【岗位职责】\n" + responsibilities + "\n\n【任职要求】\n" + requirements,
            "responsibilities": responsibilities or None,
            "requirements": requirements or None,
            "keywords": list(decision.matched_terms),
            "posted_at": published.isoformat(timespec="seconds"),
            # JD does not expose a stable, verified public detail route for every
            # record.  Point users at the verified public R&D listing instead of
            # manufacturing a detail URL that may redirect or return 404.
            "url": self.entry_url,
            "external_id": external_id,
            "source": self.source_name,
            "source_type": "official_careers_site",
            "crawled_at": crawled_at,
            "source_meta": {
                "portal_key": "jd_official_social",
                "portal_host": "zhaopin.jd.com",
                "portal_entry_url": self.entry_url,
                "collector": "jd_public_job_list",
                "position_code": item.get("positionCode"),
                "requirement_id": item.get("requirementId"),
                "request_number": item.get("reqNumber"),
                "category": category,
                "department": department,
                "scope_reason": decision.reason,
                "scope_evidence": list(decision.matched_terms),
                "date_semantics": "published_at",
            },
        }

    def run(self):
        for page_num in range(1, self.max_pages + 1):
            LOGGER.info("正在采集第 %s/%s 页...", page_num, self.max_pages)
            records = self.parse(page_num)
            self.stats["pages"] += 1
            for record in records:
                self.add_job(record)
            if self._last_page_size < 50:
                break
        self.print_stats()
        return self.save()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect public JD technical jobs")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--max-pages", type=int, default=200)
    args = parser.parse_args()
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    if start_date > end_date:
        raise SystemExit("--start-date must not be after --end-date")
    spider = JdSpider(start_date=start_date, end_date=end_date, max_pages=args.max_pages)
    spider.save_output_dir = args.output_dir
    spider.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main()
