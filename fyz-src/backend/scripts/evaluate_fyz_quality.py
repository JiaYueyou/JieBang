"""Run reproducible FYZ extraction and matching quality gates.

The JD slice uses 100 crawled records from two checked-in sources.  Their
``keywords`` fields are positive-only anchors, so the JD metric is explicitly
reported as anchor recall rather than a fully-labelled precision/F1 score.

Resume and matching cases are deterministic synthetic boundary cases.  They
exercise the production ``RuleSkillExtractor`` and the same
``calculate_skill_coverage`` function used by ``MatchingService``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.matching_service import calculate_skill_coverage  # noqa: E402
from app.services.skill_extractor import RuleSkillExtractor  # noqa: E402
from scripts.evaluate_skill_extraction import evaluate as evaluate_jd  # noqa: E402


DATASET_VERSION = "fyz-quality-v1"
JD_FILES = ("jd_crawl_ifly.json", "jd_crawl_zl.json", "jd_crawl2.json")
QUALITY_THRESHOLDS = {
    "jd_anchor_recall": 0.90,
    "resume_micro_f1": 0.90,
    "matching_exact_accuracy": 0.90,
}

# Canonical terms are deliberately selected from different dictionary groups
# and avoid ambiguous natural-language tokens.  Aliases cover normalization.
CASE_SKILLS = (
    "Python",
    "Java",
    "TypeScript",
    "Go",
    "Rust",
    "FastAPI",
    "Django",
    "React",
    "Angular",
    "Docker",
    "Kubernetes",
    "Git",
    "Jenkins",
    "MySQL",
    "PostgreSQL",
    "MongoDB",
    "Redis",
    "Neo4j",
    "Kafka",
    "GraphQL",
    "Elasticsearch",
    "TensorFlow",
    "PyTorch",
    "RabbitMQ",
)
ALIASES = {
    "TypeScript": "TS",
    "Go": "Golang",
    "React": "React.js",
    "Kubernetes": "K8s",
    "PostgreSQL": "Postgres",
    "MongoDB": "Mongo",
    "Elasticsearch": "ES",
    "TensorFlow": "TF",
}


def _render_skill(skill: str, case_index: int, position: int) -> str:
    if (case_index + position) % 3 == 0:
        return ALIASES.get(skill, skill)
    return skill


def build_resume_cases(count: int = 60) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    size = len(CASE_SKILLS)
    for index in range(count):
        expected = [
            CASE_SKILLS[index % size],
            CASE_SKILLS[(index + 5) % size],
            CASE_SKILLS[(index + 11) % size],
        ]
        rendered = [
            _render_skill(skill, index, position)
            for position, skill in enumerate(expected)
        ]
        cases.append(
            {
                "id": f"resume-{index + 1:03d}",
                "text": (
                    "Candidate delivered two production projects using "
                    + ", ".join(rendered)
                    + ". Results and responsibilities are documented."
                ),
                "expected_skills": expected,
            }
        )
    return cases


def build_matching_cases(count: int = 60) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    size = len(CASE_SKILLS)
    for index in range(count):
        job_skills = [CASE_SKILLS[(index + offset) % size] for offset in range(5)]
        matched_count = index % 6
        resume_skills = job_skills[:matched_count]
        if matched_count < 5:
            resume_skills.append(CASE_SKILLS[(index + 12) % size])
        cases.append(
            {
                "id": f"match-{index + 1:03d}",
                "job_text": "Required stack: "
                + ", ".join(
                    _render_skill(skill, index, position)
                    for position, skill in enumerate(job_skills)
                ),
                "resume_text": (
                    "Candidate stack: "
                    + ", ".join(
                        _render_skill(skill, index + 1, position)
                        for position, skill in enumerate(resume_skills)
                    )
                    if resume_skills
                    else "Candidate has no relevant stack evidence."
                ),
                "expected_job_skills": job_skills,
                "expected_resume_skills": resume_skills,
            }
        )
    return cases


def _micro_metrics(rows: list[tuple[set[str], set[str]]]) -> dict[str, Any]:
    true_positive = sum(len(predicted & expected) for predicted, expected in rows)
    false_positive = sum(len(predicted - expected) for predicted, expected in rows)
    false_negative = sum(len(expected - predicted) for predicted, expected in rows)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    exact = sum(predicted == expected for predicted, expected in rows) / len(rows)
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "micro_precision": round(precision, 6),
        "micro_recall": round(recall, 6),
        "micro_f1": round(f1, 6),
        "exact_case_accuracy": round(exact, 6),
    }


def evaluate_resume_extraction(count: int = 60) -> dict[str, Any]:
    extractor = RuleSkillExtractor()
    cases = build_resume_cases(count)
    rows: list[tuple[set[str], set[str]]] = []
    failures: list[dict[str, Any]] = []
    for case in cases:
        predicted = {item.name for item in extractor.extract(jd_text=case["text"]).skills}
        expected = set(case["expected_skills"])
        rows.append((predicted, expected))
        if predicted != expected:
            failures.append(
                {
                    "id": case["id"],
                    "predicted": sorted(predicted),
                    "expected": sorted(expected),
                }
            )
    return {
        "dataset": "deterministic labelled resume skill boundary cases",
        "records": len(cases),
        **_micro_metrics(rows),
        "failure_count": len(failures),
        "failures": failures[:20],
    }


def evaluate_matching(count: int = 60) -> dict[str, Any]:
    extractor = RuleSkillExtractor()
    cases = build_matching_cases(count)
    exact_scores = 0
    exact_skill_sets = 0
    absolute_errors: list[int] = []
    failures: list[dict[str, Any]] = []
    for case in cases:
        predicted_job = [
            item.name for item in extractor.extract(jd_text=case["job_text"]).skills
        ]
        predicted_resume = [
            item.name for item in extractor.extract(jd_text=case["resume_text"]).skills
        ]
        expected_score, expected_matched, _ = calculate_skill_coverage(
            case["expected_resume_skills"], case["expected_job_skills"]
        )
        predicted_score, predicted_matched, _ = calculate_skill_coverage(
            predicted_resume, predicted_job
        )
        score_ok = predicted_score == expected_score
        set_ok = set(predicted_matched) == set(expected_matched)
        exact_scores += int(score_ok)
        exact_skill_sets += int(set_ok)
        absolute_errors.append(abs(predicted_score - expected_score))
        if not score_ok or not set_ok:
            failures.append(
                {
                    "id": case["id"],
                    "predicted_score": predicted_score,
                    "expected_score": expected_score,
                    "predicted_matched": sorted(predicted_matched),
                    "expected_matched": sorted(expected_matched),
                }
            )
    return {
        "dataset": "deterministic labelled end-to-end skill coverage cases",
        "records": len(cases),
        "exact_score_accuracy": round(exact_scores / len(cases), 6),
        "exact_matched_set_accuracy": round(exact_skill_sets / len(cases), 6),
        "mean_absolute_score_error": round(mean(absolute_errors), 6),
        "failure_count": len(failures),
        "failures": failures[:20],
    }


def load_jd_records(limit: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    sources: dict[str, int] = {}
    for filename in JD_FILES:
        path = PROJECT_DIR / "data" / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON array")
        remaining = max(0, limit - len(records))
        selected = payload[:remaining]
        records.extend(selected)
        if selected:
            sources[filename] = len(selected)
        if len(records) >= limit:
            break
    if len(records) < limit:
        raise ValueError(f"only {len(records)} JD records available; expected {limit}")
    return records, sources


def run_evaluation(*, jd_limit: int = 100, case_count: int = 60) -> dict[str, Any]:
    if jd_limit < 100:
        raise ValueError("jd_limit must be at least 100")
    records, sources = load_jd_records(jd_limit)
    jd_result = evaluate_jd(records, jd_limit)
    jd = {
        "dataset": "checked-in crawled JD positive keyword anchors",
        "records": jd_result["records"],
        "source_distribution": sources,
        "records_with_recognized_anchors": jd_result["labeled_records"],
        "anchor_true_positive": jd_result["true_positive"],
        "anchor_false_negative": jd_result["false_negative"],
        "anchor_recall": jd_result["recall"],
        "anchor_proxy_f1": jd_result["f1"],
        "limitation": (
            "Source keywords are positive-only and incomplete; false-positive "
            "rate and fully-labelled JD precision cannot be inferred."
        ),
    }
    resume = evaluate_resume_extraction(case_count)
    matching = evaluate_matching(case_count)
    gates = {
        "jd_anchor_recall": jd["anchor_recall"] >= QUALITY_THRESHOLDS["jd_anchor_recall"],
        "resume_micro_f1": resume["micro_f1"] >= QUALITY_THRESHOLDS["resume_micro_f1"],
        "matching_exact_accuracy": matching["exact_score_accuracy"]
        >= QUALITY_THRESHOLDS["matching_exact_accuracy"],
    }
    return {
        "dataset_version": DATASET_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "FYZ backend only",
        "thresholds": QUALITY_THRESHOLDS,
        "jd_extraction": jd,
        "resume_extraction": resume,
        "matching": matching,
        "gates": gates,
        "all_quality_gates_passed": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jd-limit", type=int, default=100)
    parser.add_argument("--case-count", type=int, default=60)
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_DIR / "evaluation" / "fyz_quality_metrics.json",
    )
    args = parser.parse_args()
    result = run_evaluation(jd_limit=args.jd_limit, case_count=args.case_count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_quality_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
