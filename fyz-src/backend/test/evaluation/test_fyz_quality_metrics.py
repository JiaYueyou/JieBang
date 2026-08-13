from __future__ import annotations

from app.services.matching_service import calculate_skill_coverage
from scripts.evaluate_fyz_quality import (
    QUALITY_THRESHOLDS,
    build_matching_cases,
    build_resume_cases,
    evaluate_matching,
    evaluate_resume_extraction,
    run_evaluation,
)


def test_quality_case_sets_are_large_versioned_and_unique():
    resume_cases = build_resume_cases()
    matching_cases = build_matching_cases()

    assert len(resume_cases) >= 50
    assert len(matching_cases) >= 50
    assert len({case["id"] for case in resume_cases}) == len(resume_cases)
    assert len({case["id"] for case in matching_cases}) == len(matching_cases)


def test_production_skill_coverage_normalizes_aliases_and_duplicates():
    score, matched, missing = calculate_skill_coverage(
        ["K8s", "Postgres", "Kubernetes"],
        ["Kubernetes", "PostgreSQL", "Redis", "Redis"],
    )

    assert score == 67
    assert matched == ["Kubernetes", "PostgreSQL"]
    assert missing == ["Redis"]


def test_resume_and_matching_quality_gates_use_production_code():
    resume = evaluate_resume_extraction()
    matching = evaluate_matching()

    assert resume["records"] >= 50
    assert resume["micro_f1"] >= QUALITY_THRESHOLDS["resume_micro_f1"]
    assert matching["records"] >= 50
    assert (
        matching["exact_score_accuracy"]
        >= QUALITY_THRESHOLDS["matching_exact_accuracy"]
    )


def test_full_fyz_quality_evaluation_uses_100_real_jds():
    result = run_evaluation(jd_limit=100, case_count=60)

    assert result["scope"] == "FYZ backend only"
    assert result["jd_extraction"]["records"] == 100
    assert result["jd_extraction"]["source_distribution"] == {
        "jd_crawl_ifly.json": 50,
        "jd_crawl_zl.json": 50,
    }
    assert (
        result["jd_extraction"]["anchor_recall"]
        >= QUALITY_THRESHOLDS["jd_anchor_recall"]
    )
    assert "positive-only" in result["jd_extraction"]["limitation"]
    assert result["all_quality_gates_passed"] is True
