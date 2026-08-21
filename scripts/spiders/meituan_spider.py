"""Collect public Meituan social-recruitment technical positions."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import logging
from pathlib import Path
import sys
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_framework import BaseSpider
from spider_framework.tech_scope import classify_tech_scope


LOGGER = logging.getLogger("spider.meituan")


def timestamp_to_local(value: Any) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).astimezone()
    except (ValueError, OSError, OverflowError):
        return None


def names(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [
        str(item.get("name") or "").strip()
        for item in items
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]


class MeituanSpider(BaseSpider):
    name = "meituan"
    source_name = "美团官方社会招聘门户（zhaopin.meituan.com）"
    default_config = {"request_interval": 0.5, "retry_times": 3, "timeout": 30}
    list_api = "https://zhaopin.meituan.com/api/official/job/getJobList"
    detail_api = "https://zhaopin.meituan.com/api/official/job/getJobDetail"
    entry_url = "https://zhaopin.meituan.com/web/social"

    def __init__(self, *, start_date: date, end_date: date, max_pages: int = 100) -> None:
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.snapshot_scope = {
            "collector": self.name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "job_family": "technology",
        }
        self.max_pages = max(1, max_pages)
        self._last_page_size = 0
        self._last_total_pages = 0

    def parse(self, page_num: int) -> list[dict]:
        response = self.fetch(
            self.list_api,
            method="POST",
            json_data={
                "page": {"pageNo": page_num, "pageSize": 50},
                "jobShareType": "1",
                "keywords": "",
                "cityList": [],
                "department": [],
                "jfJgList": [{"code": "11001", "subCode": []}],
                "jobType": [{"code": "3", "subCode": []}],
                "typeCode": [],
                "specialCode": [],
            },
            headers={"Referer": self.entry_url},
        )
        body = response.json()
        data = body.get("data") or {}
        rows = data.get("list") or []
        page = data.get("page") or {}
        if not isinstance(rows, list):
            raise ValueError("Meituan public jobs endpoint returned a non-list payload")
        self._last_page_size = len(rows)
        self._last_total_pages = int(page.get("totalPage") or 0)
        crawled_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        records = []
        for row in rows:
            job_id = str(row.get("jobUnionId") or "").strip()
            if not job_id:
                continue
            detail_response = self.fetch(
                self.detail_api,
                method="POST",
                json_data={"jobUnionId": job_id, "jobShareType": "1"},
                headers={"Referer": self.entry_url},
            )
            detail = (detail_response.json().get("data") or row)
            record = self.normalize_job(detail, crawled_at=crawled_at)
            if record:
                records.append(record)
        return records

    def normalize_job(self, item: dict, *, crawled_at: str) -> dict | None:
        title = str(item.get("name") or "").strip()
        responsibilities = str(item.get("jobDuty") or "").strip()
        requirements = str(item.get("jobRequirement") or "").strip()
        highlights = str(item.get("highLight") or "").strip()
        description = "\n\n".join(value for value in (responsibilities, requirements, highlights) if value)
        category = str(item.get("jobFamily") or "").strip()
        group = str(item.get("jobFamilyGroup") or "").strip()
        departments = names(item.get("department"))
        decision = classify_tech_scope(
            title=title,
            category=f"{category} {group}",
            department=" ".join(departments),
            description=description,
        )
        published = timestamp_to_local(item.get("firstPostTime"))
        if (
            not decision.in_scope
            or not title
            or len(description) < 10
            or published is None
            or not (self.start_date <= published.date() <= self.end_date)
        ):
            return None
        job_id = str(item.get("jobUnionId") or "").strip()
        if not job_id:
            return None
        refreshed = timestamp_to_local(item.get("refreshTime"))
        return {
            "title": title,
            "company": "美团",
            "city": "、".join(names(item.get("cityList"))) or None,
            "salary": None,
            "experience": str(item.get("workYear") or "").strip() or None,
            "education": None,
            "jd_text": "【岗位职责】\n" + responsibilities + "\n\n【任职要求】\n" + requirements,
            "responsibilities": responsibilities or None,
            "requirements": requirements or None,
            "keywords": list(dict.fromkeys([category, group, *decision.matched_terms])) ,
            "posted_at": published.isoformat(timespec="seconds"),
            "url": f"https://zhaopin.meituan.com/web/position/detail?highlightType=social&jobUnionId={job_id}",
            "external_id": job_id,
            "source": self.source_name,
            "source_type": "official_careers_site",
            "crawled_at": crawled_at,
            "source_meta": {
                "portal_key": "meituan_official_social",
                "portal_host": "zhaopin.meituan.com",
                "collector": "meituan_public_job_api",
                "category": category,
                "category_group": group,
                "departments": departments,
                "scope_reason": decision.reason,
                "scope_evidence": list(decision.matched_terms),
                "source_updated_at": refreshed.isoformat(timespec="seconds") if refreshed else None,
                "date_semantics": "published_at",
            },
        }

    def run(self):
        exhausted = False
        for page_num in range(1, self.max_pages + 1):
            LOGGER.info("正在采集第 %s/%s 页...", page_num, self.max_pages)
            records = self.parse(page_num)
            self.stats["pages"] += 1
            for record in records:
                self.add_job(record)
            if self._last_page_size == 0 or (
                self._last_total_pages and page_num >= self._last_total_pages
            ):
                exhausted = True
                break
        self.snapshot_complete = (
            exhausted
            and self.stats["errors"] == 0
            and not (self.max_records and len(self.observed_data) >= self.max_records)
        )
        self.print_stats()
        return self.save()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect public Meituan technical jobs")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    if start_date > end_date:
        raise SystemExit("--start-date must not be after --end-date")
    spider = MeituanSpider(start_date=start_date, end_date=end_date, max_pages=args.max_pages)
    spider.save_output_dir = args.output_dir
    spider.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main()
