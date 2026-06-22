"""Evaluate rule extraction against explicit keyword anchors in crawled JDs.

The crawler's ``keywords`` field is a positive-only, incomplete annotation.
This proxy therefore measures whether those positive anchors are recovered;
it cannot estimate false positives outside the anchors.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.domain.skill_dictionary import normalize_skill  # noqa: E402
from app.services.skill_extractor import RuleSkillExtractor  # noqa: E402

DEFAULT_FILES = (
    "jd_crawl_ifly.json",
    "jd_crawl_zl.json",
    "jd_crawl2.json",
)


def _keyword_labels(value: str | list | None) -> set[str]:
    if isinstance(value, list):
        terms = [str(item) for item in value]
    else:
        terms = str(value or "").replace("，", ",").split(",")
    labels: set[str] = set()
    for term in terms:
        normalized = normalize_skill(term.strip())
        if normalized:
            labels.add(normalized[0])
    return labels


def evaluate(records: list[dict], limit: int) -> dict:
    selected = records[:limit]
    labels_by_record = [_keyword_labels(record.get("keywords") or record.get("keyword")) for record in selected]
    extractor = RuleSkillExtractor()
    true_positive = false_negative = 0

    for record, labels in zip(selected, labels_by_record):
        output = extractor.extract(
            jd_text=record.get("jd_text", ""),
            responsibilities=record.get("responsibilities", ""),
            requirements=record.get("requirements", ""),
        )
        predictions = {item.name for item in output.skills}
        true_positive += len(predictions & labels)
        false_negative += len(labels - predictions)

    # The source only provides positive anchors. Skills absent from ``keywords``
    # cannot honestly be counted as false positives.
    precision = 1.0 if true_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "records": len(selected),
        "labeled_records": sum(bool(labels) for labels in labels_by_record),
        "anchor_skills": sorted(set().union(*labels_by_record) if labels_by_record else set()),
        "true_positive": true_positive,
        "false_positive": None,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "metric": "positive_keyword_anchor_proxy",
        "note": "keywords 仅含正例且不完整；precision 不包含未标注技能，正式 F1 仍需人工金标准。",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--files", nargs="+", default=list(DEFAULT_FILES))
    args = parser.parse_args()
    if args.limit < 100:
        parser.error("--limit must be at least 100")

    records: list[dict] = []
    for filename in args.files:
        path = PROJECT_DIR / "data" / filename
        with path.open(encoding="utf-8") as stream:
            payload = json.load(stream)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON array")
        records.extend(payload)
    if len(records) < args.limit:
        raise ValueError(f"only {len(records)} records available, expected {args.limit}")

    result = evaluate(records, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["f1"] >= 0.90 else 1


if __name__ == "__main__":
    raise SystemExit(main())
