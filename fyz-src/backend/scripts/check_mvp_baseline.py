"""Read-only stage-0 check for the two FYZ MVP crawler datasets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.job_import_schema import normalize_and_validate_records  # noqa: E402


def latest_file(prefix: str) -> Path:
    candidates: list[tuple[int, Path]] = []
    for path in (PROJECT_DIR / "data").glob(f"{prefix}_*.json"):
        match = re.fullmatch(rf"{re.escape(prefix)}_(\d+)\.json", path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        raise FileNotFoundError(f"未找到 {prefix}_N.json")
    return max(candidates, key=lambda item: item[0])[1]


def main() -> int:
    reports = []
    for prefix in ("iflytek", "zhaopin"):
        path = latest_file(prefix)
        payload = json.loads(path.read_text(encoding="utf-8"))
        _, report = normalize_and_validate_records(payload, filename=path.name)
        reports.append(report)

    print(json.dumps({"schema": "job-v1", "sources": reports}, ensure_ascii=False, indent=2))
    total = sum(report["total"] for report in reports)
    failed = sum(report["failed"] for report in reports)
    if total < 100:
        print(f"MVP 基线失败：仅有 {total} 条记录，少于 100 条。", file=sys.stderr)
        return 1
    if failed:
        print(f"MVP 基线失败：{failed} 条记录未通过 job-v1。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
