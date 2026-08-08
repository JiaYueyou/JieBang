"""Read public Zhipu recruiting cards exposed by its official careers link.

This is deliberately narrow: it never signs in, submits an application, or
attempts to bypass a challenge.  It uses the existing Playwright CLI session to
read the rendered public job-list cards, after the robots checks recorded in the
companion report.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "official_group_b_20260809.json"
SESSION = "official_group_b"
# Keep the fragment free of ``&`` because the Windows ``npx.cmd`` launcher
# forwards its arguments through cmd.exe.  The page number alone selects the
# same public results page.
BASE = "https://app.mokahr.com/social-recruitment/zphz/148983?locale=zh-CN#/jobs?page={page}"
# The collection uses the project's Windows Node installation.  ``npx.ps1``
# works interactively in PowerShell but cannot be spawned directly by Python.
CLI = [
    r"E:\Computer_tools\Nodejs\download\npx.cmd",
    "--yes",
    "--package",
    "@playwright/cli",
    "playwright-cli",
    "--session",
    SESSION,
]

# Retain the technical/product roles requested for this collection.  The public
# list also contains HR, finance, procurement, and pure commercial roles.
TECH_RE = re.compile(
    r"算法|工程师|开发|研发|AI|大模型|数据|产品|架构|设计|运维|测试|技术|智能|"
    r"Code|Agent|Infra|MaaS|平台|客户端|模型|机器人|交付",
    re.IGNORECASE,
)


def cli(*args: str) -> str:
    result = subprocess.run(
        [*CLI, "--raw", *args],
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    return result.stdout.strip()


def page_cards(page: int) -> list[dict[str, str]]:
    cli("goto", BASE.format(page=page))
    # A snapshot is a normal, read-only wait for the SPA to finish rendering.
    subprocess.run([*CLI, "snapshot"], cwd=ROOT, check=True, capture_output=True)
    expression = (
        "() => JSON.stringify(Array.from(document.querySelectorAll(\"a\"))"
        ".map(a => ({href: a.href, text: a.innerText}))"
        ".filter(x => x.text && x.text.includes('发布于')))"
    )
    raw = cli("eval", expression)
    return json.loads(json.loads(raw))


def normalize(card: dict[str, str], crawled_at: str) -> dict[str, str] | None:
    text = re.sub(r"\n{3,}", "\n\n", card["text"]).strip()
    match = re.search(r"发布于\s*(\d{4}-\d{2}-\d{2})", text)
    if not match:
        return None
    posted_at = match.group(1)
    if posted_at < "2026-01-01":
        return None
    prefix = text[: match.start()].strip()
    title_lines = [line.strip() for line in prefix.splitlines() if line.strip() and line.strip() != "急"]
    if not title_lines:
        return None
    title = title_lines[-1]
    if not TECH_RE.search(title):
        return None
    # The rendered card exposes the complete public JD and requirements.  Keep
    # it intact so downstream importers can perform their own structured split.
    description = re.sub(r"\s*立即投递\s*$", "", text).strip()
    return {
        "source": "智谱AI官网招聘（官网加入我们页跳转的Moka招聘站）",
        "url": card["href"],
        "title": title,
        "company": "北京智谱华章科技股份有限公司",
        "jd_requirements": description,
        "posted_at": posted_at,
        "crawled_at": crawled_at,
    }


def main() -> int:
    crawled_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    seen: set[str] = set()
    records: list[dict[str, str]] = []
    for page in range(1, 6):
        for card in page_cards(page):
            if card["href"] in seen:
                continue
            seen.add(card["href"])
            record = normalize(card, crawled_at)
            if record:
                records.append(record)
    records.sort(key=lambda item: (item["posted_at"], item["title"]), reverse=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(records), "path": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
