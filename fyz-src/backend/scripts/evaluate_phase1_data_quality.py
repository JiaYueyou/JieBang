"""Evaluate Phase 1 duplicate classification and freshness rules."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.data_quality import (
    normalize_job_body,
    parse_source_datetime,
    simhash64,
    simhash_similarity,
)
from app.core.time import utc_isoformat, utc_now

GOLDEN_PATH = BACKEND_ROOT / "evaluation" / "phase0_golden_set.json"
REPORT_JSON = BACKEND_ROOT / "evaluation" / "phase1_data_quality_report.json"
REPORT_MD = BACKEND_ROOT / "evaluation" / "phase1_data_quality_report.md"
NEAR_DUPLICATE_THRESHOLD = 0.9


def _duplicate_prediction(case: dict) -> tuple[str, float]:
    existing = case["input"]["existing"]
    candidate = case["input"]["candidate"]
    same_identity = (
        existing.get("source") == candidate.get("source")
        and existing.get("external_id")
        and existing.get("external_id") == candidate.get("external_id")
    )
    similarity = simhash_similarity(
        simhash64(normalize_job_body(existing.get("jd_text", ""))),
        simhash64(normalize_job_body(candidate.get("jd_text", ""))),
    )
    if same_identity:
        return "exact_identity", similarity
    if similarity >= NEAR_DUPLICATE_THRESHOLD:
        return "near_duplicate", similarity
    return "distinct", similarity


def _freshness_prediction(case: dict) -> str:
    payload = case["input"]
    observed_at = parse_source_datetime(payload.get("observed_at"))
    posted_at = parse_source_datetime(
        payload.get("posted_at"),
        observed_at=observed_at,
    )
    if not observed_at or not posted_at:
        return "expired"
    age_days = (observed_at - posted_at).total_seconds() / 86400
    return "current" if 0 <= age_days <= payload["max_age_days"] else "expired"


def evaluate() -> dict:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    duplicate_rows = []
    freshness_rows = []
    for case in golden["cases"]:
        if case["category"] == "data_duplicate":
            prediction, similarity = _duplicate_prediction(case)
            expected = case["expected"]["match_type"]
            duplicate_rows.append(
                {
                    "id": case["id"],
                    "expected": expected,
                    "predicted": prediction,
                    "similarity": similarity,
                    "passed": prediction == expected,
                }
            )
        elif case["category"] == "data_freshness":
            prediction = _freshness_prediction(case)
            expected = case["expected"]["freshness"]
            freshness_rows.append(
                {
                    "id": case["id"],
                    "expected": expected,
                    "predicted": prediction,
                    "passed": prediction == expected,
                }
            )

    duplicate_passed = sum(row["passed"] for row in duplicate_rows)
    freshness_passed = sum(row["passed"] for row in freshness_rows)
    report = {
        "schema_version": "phase1-data-quality-eval-v1",
        "generated_at": utc_isoformat(utc_now()),
        "golden_set": str(GOLDEN_PATH.relative_to(BACKEND_ROOT)),
        "review_summary": golden.get("review_summary"),
        "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
        "metrics": {
            "duplicate_type_accuracy": round(
                duplicate_passed / len(duplicate_rows),
                4,
            ),
            "freshness_accuracy": round(
                freshness_passed / len(freshness_rows),
                4,
            ),
        },
        "duplicate_cases": duplicate_rows,
        "freshness_cases": freshness_rows,
        "limitations": [
            "The duplicate seed set contains exact and near-duplicate positives but no broad negative corpus.",
            "The set was transparently engineering-reviewed and is not human domain gold.",
        ],
    }
    return report


def _markdown(report: dict) -> str:
    duplicate = report["metrics"]["duplicate_type_accuracy"]
    freshness = report["metrics"]["freshness_accuracy"]
    failed = [
        row
        for row in report["duplicate_cases"] + report["freshness_cases"]
        if not row["passed"]
    ]
    return "\n".join(
        [
            "# FYZ Phase 1 数据质量评测",
            "",
            f"- 生成时间：`{report['generated_at']}`",
            f"- 重复类型分类准确率：`{duplicate:.2%}`",
            f"- 时效分类准确率：`{freshness:.2%}`",
            f"- 失败样本：`{len(failed)}`",
            f"- 近重复阈值：`{report['near_duplicate_threshold']}`",
            "",
            "## 解释边界",
            "",
            "- 当前重复集覆盖精确身份重复与近重复正样本，没有覆盖大规模负样本，不能据此宣称生产精确率。",
            "- 评测集为经用户授权的工程审核种子集，不是业务专家人工金标集。",
            "",
        ]
    )


def main() -> int:
    report = evaluate()
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    REPORT_MD.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "duplicate_type_accuracy": report["metrics"]["duplicate_type_accuracy"],
                "freshness_accuracy": report["metrics"]["freshness_accuracy"],
                "json": str(REPORT_JSON),
                "markdown": str(REPORT_MD),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
