"""Evaluate 100 real crawled JD records with auditable per-case outputs.

The benchmark separates three measurable questions instead of presenting the
source's incomplete ``keywords`` labels as a fully annotated gold standard:

1. canonical field preservation and schema validation;
2. responsibility/requirement section consistency with the original JD body;
3. positive skill-anchor recall using the production rule extractor.

The case artifact retains the original input, normalized output, extracted
skills, source URL, and per-case checks so reviewers can reproduce every row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.domain.skill_dictionary import normalize_skill  # noqa: E402
from app.services.job_import_schema import (  # noqa: E402
    normalize_job_record,
    validate_job_record,
)
from app.services.skill_extractor import RuleSkillExtractor  # noqa: E402


DATASET_VERSION = "competition-jd-real-100-v1"
SOURCE_FILES = ("jd_crawl_ifly.json", "jd_crawl_zl.json")
EXACT_FIELDS = (
    "title",
    "company",
    "city",
    "salary",
    "experience",
    "education",
    "responsibilities",
    "requirements",
    "jd_text",
    "posted_at",
    "url",
    "source",
    "crawled_at",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _anchors(value: str | list[Any] | None) -> set[str]:
    raw = value if isinstance(value, list) else str(value or "").replace("，", ",").split(",")
    labels: set[str] = set()
    for item in raw:
        normalized = normalize_skill(str(item).strip())
        if normalized:
            labels.add(normalized[0])
    return labels


def _same(left: Any, right: Any) -> bool:
    return str(left or "").strip() == str(right or "").strip()


def run(limit: int = 100) -> dict[str, Any]:
    if limit < 100:
        raise ValueError("limit must be at least 100")

    records: list[tuple[str, int, dict[str, Any]]] = []
    sources: list[dict[str, Any]] = []
    for filename in SOURCE_FILES:
        path = PROJECT_DIR / "data" / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON array")
        sources.append(
            {
                "file": str(path.relative_to(PROJECT_DIR)),
                "sha256": _sha256(path),
                "records": len(payload),
            }
        )
        for index, record in enumerate(payload):
            records.append((filename, index, record))
    selected = records[:limit]
    if len(selected) < limit:
        raise ValueError(f"only {len(selected)} real JD records available")

    extractor = RuleSkillExtractor()
    cases: list[dict[str, Any]] = []
    exact_correct = exact_total = 0
    section_correct = section_total = 0
    anchor_tp = anchor_fn = 0
    schema_passed = 0

    for case_index, (filename, source_index, raw) in enumerate(selected, start=1):
        normalized = normalize_job_record(raw)
        schema_errors = validate_job_record(normalized)
        schema_ok = not schema_errors
        schema_passed += int(schema_ok)

        field_checks: dict[str, bool | None] = {}
        for field in EXACT_FIELDS:
            expected = raw.get(field)
            if expected in (None, ""):
                field_checks[field] = None
                continue
            passed = _same(normalized.get(field), expected)
            field_checks[field] = passed
            exact_correct += int(passed)
            exact_total += 1

        section_checks: dict[str, bool | None] = {}
        body = str(raw.get("jd_text") or "")
        for field in ("responsibilities", "requirements"):
            expected = str(raw.get(field) or "").strip()
            if not expected:
                section_checks[field] = None
                continue
            passed = expected in body
            section_checks[field] = passed
            section_correct += int(passed)
            section_total += 1

        expected_anchors = _anchors(raw.get("keywords") or raw.get("keyword"))
        extracted = extractor.extract(
            jd_text=str(normalized.get("jd_text") or ""),
            responsibilities=str(normalized.get("responsibilities") or ""),
            requirements=str(normalized.get("requirements") or ""),
        )
        predicted = {item.name for item in extracted.skills}
        recovered = expected_anchors & predicted
        missing = expected_anchors - predicted
        anchor_tp += len(recovered)
        anchor_fn += len(missing)

        cases.append(
            {
                "case_id": f"JD-{case_index:03d}",
                "source_file": filename,
                "source_index": source_index,
                "source_url": raw.get("url"),
                "input_sha256": hashlib.sha256(
                    json.dumps(raw, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest(),
                "input": raw,
                "output": {
                    "normalized": normalized,
                    "extracted_skills": [item.model_dump() for item in extracted.skills],
                },
                "expected": {"positive_skill_anchors": sorted(expected_anchors)},
                "checks": {
                    "schema_valid": schema_ok,
                    "schema_errors": schema_errors,
                    "exact_field_preservation": field_checks,
                    "section_consistency": section_checks,
                    "recovered_skill_anchors": sorted(recovered),
                    "missing_skill_anchors": sorted(missing),
                },
            }
        )

    field_accuracy = exact_correct / exact_total if exact_total else 0.0
    section_accuracy = section_correct / section_total if section_total else 0.0
    anchor_recall = anchor_tp / (anchor_tp + anchor_fn) if anchor_tp + anchor_fn else 0.0
    labelled_correct = exact_correct + section_correct + anchor_tp
    labelled_total = exact_total + section_total + anchor_tp + anchor_fn
    labelled_unit_accuracy = labelled_correct / labelled_total if labelled_total else 0.0
    metrics = {
        "records": len(cases),
        "unique_source_urls": len({case["source_url"] for case in cases}),
        "schema_valid_rate": round(schema_passed / len(cases), 6),
        "field_exact_correct": exact_correct,
        "field_exact_total": exact_total,
        "field_exact_accuracy": round(field_accuracy, 6),
        "section_consistency_correct": section_correct,
        "section_consistency_total": section_total,
        "section_consistency_accuracy": round(section_accuracy, 6),
        "anchor_true_positive": anchor_tp,
        "anchor_false_negative": anchor_fn,
        "positive_skill_anchor_recall": round(anchor_recall, 6),
        "labelled_unit_correct": labelled_correct,
        "labelled_unit_total": labelled_total,
        "jd_parse_labelled_unit_accuracy": round(labelled_unit_accuracy, 6),
    }
    gates = {
        "at_least_100_real_jds": len(cases) >= 100,
        "all_urls_unique": metrics["unique_source_urls"] == len(cases),
        "schema_valid_rate_at_least_90_percent": metrics["schema_valid_rate"] >= 0.90,
        "field_exact_accuracy_at_least_90_percent": metrics["field_exact_accuracy"] >= 0.90,
        "section_consistency_at_least_90_percent": metrics["section_consistency_accuracy"] >= 0.90,
        "positive_skill_anchor_recall_at_least_90_percent": metrics["positive_skill_anchor_recall"] >= 0.90,
        "jd_parse_labelled_unit_accuracy_at_least_90_percent": metrics["jd_parse_labelled_unit_accuracy"] >= 0.90,
    }
    return {
        "dataset_version": DATASET_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "100 real crawled JD records from two independent recruitment sources",
        "metric_definition": {
            "jd_parse_labelled_unit_accuracy": (
                "(exact source-labelled fields + consistent labelled sections + recovered positive skill anchors) "
                "/ all eligible labelled units"
            ),
            "positive_skill_anchor_recall": "recovered source keyword anchors / all source keyword anchors",
        },
        "limitations": [
            "The source keyword field contains positive-only, incomplete labels; skill precision and full skill-set F1 are not inferred.",
            "Field preservation measures the production crawler-to-import contract, not OCR or free-form HTML scraping accuracy.",
            "The two source slices contain 50 records each and are a fixed competition benchmark, not a population estimate.",
        ],
        "sources": sources,
        "metrics": metrics,
        "gates": gates,
        "passed": all(gates.values()),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_DIR / "evaluation" / "competition_jd_test_cases.json",
    )
    args = parser.parse_args()
    report = run(args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"metrics": report["metrics"], "gates": report["gates"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
