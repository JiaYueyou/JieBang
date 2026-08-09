"""DeepSeek official-talent collector.

The public page embeds its reviewed job snapshot in the hashed application
bundle.  No login, application endpoint, or encrypted Moka detail API is used.
The bundle snapshot time is retained as observation metadata; it is not
misrepresented as a per-job publication date.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import logging
from pathlib import Path
import re
import sys
from urllib.parse import urljoin


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_framework import BaseSpider
from spider_framework.tech_scope import classify_tech_scope


LOGGER = logging.getLogger("spider.deepseek")


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


def extract_embedded_snapshot(bundle_text: str) -> dict:
    marker = 'JSON.parse(\'{"crawledAt":'
    marker_at = bundle_text.find(marker)
    if marker_at < 0:
        raise ValueError("DeepSeek bundle does not contain the expected jobs snapshot")
    literal_start = marker_at + len("JSON.parse(")
    escaped = False
    literal_end = None
    for index in range(literal_start + 1, len(bundle_text)):
        char = bundle_text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and bundle_text[index + 1:index + 2] == ")":
            literal_end = index + 1
            break
    if literal_end is None:
        raise ValueError("DeepSeek jobs snapshot string is not terminated")
    payload = ast.literal_eval(bundle_text[literal_start:literal_end])
    data = json.loads(payload)
    expected_source = "https://app.mokahr.com/social-recruitment/high-flyer/140576#/"
    if data.get("sourceUrl") != expected_source or not isinstance(data.get("jobs"), list):
        raise ValueError("DeepSeek jobs snapshot provenance is unexpected")
    if int(data.get("total", -1)) != len(data["jobs"]):
        raise ValueError("DeepSeek jobs snapshot count does not match its payload")
    return data


class DeepSeekSpider(BaseSpider):
    name = "deepseek"
    source_name = "DeepSeek官方招聘门户（talent.deepseek.com）"
    default_config = {"request_interval": 1.0, "retry_times": 3, "timeout": 30}
    entry_url = "https://talent.deepseek.com/"

    def parse(self, page_num: int) -> list[dict]:
        if page_num != 1:
            return []
        home = self.fetch(self.entry_url).text
        scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)', home)
        bundle_path = next((value for value in scripts if "/static/main." in value), None)
        if not bundle_path:
            raise ValueError("DeepSeek hashed application bundle was not found")
        bundle_url = urljoin(self.entry_url, bundle_path)
        response = self.fetch(bundle_url)
        response.encoding = "utf-8"
        snapshot = extract_embedded_snapshot(response.text)
        crawled_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        records = []
        for item in snapshot["jobs"]:
            record = self.normalize_job(
                item,
                crawled_at=crawled_at,
                snapshot_at=snapshot.get("crawledAt"),
                bundle_url=bundle_url,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )
            if record:
                records.append(record)
        return records

    def normalize_job(
        self,
        item: dict,
        *,
        crawled_at: str,
        snapshot_at: str | None,
        bundle_url: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> dict | None:
        title = str(item.get("title") or "").strip()
        description = html_to_text(str(item.get("descriptionHtml") or ""))
        category = str(item.get("functionName") or "").strip()
        decision = classify_tech_scope(
            title=title,
            category=category,
            description=description,
        )
        if not decision.in_scope or not title or len(description) < 10:
            return None
        locations = item.get("locations") or []
        return {
            "title": title,
            "company": "DeepSeek",
            "city": "、".join(str(value) for value in locations if value) or None,
            "salary": None,
            "experience": None,
            "education": None,
            "jd_text": description,
            "responsibilities": description,
            "requirements": None,
            "keywords": list(decision.matched_terms),
            "posted_at": None,
            "url": str(item.get("detailUrl") or self.entry_url),
            "external_id": str(item.get("id") or ""),
            "source": self.source_name,
            "source_type": "official_careers_site",
            "crawled_at": crawled_at,
            "source_meta": {
                "portal_key": "deepseek_official_talent",
                "portal_host": "talent.deepseek.com",
                "collector": "deepseek_bundle_snapshot",
                "category": category,
                "scope_reason": decision.reason,
                "scope_evidence": list(decision.matched_terms),
                "snapshot_observed_at": snapshot_at,
                "date_semantics": "snapshot_observed_at",
                "bundle_url": bundle_url,
                "bundle_etag": etag,
                "bundle_last_modified": last_modified,
            },
        }

    def run(self):
        for record in self.parse(1):
            self.add_job(record)
        self.stats["pages"] = 1
        self.print_stats()
        return self.save()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect public DeepSeek technical jobs")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--max-pages", type=int, default=1)
    args = parser.parse_args()
    spider = DeepSeekSpider()
    spider.save_output_dir = args.output_dir
    spider.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    main()
