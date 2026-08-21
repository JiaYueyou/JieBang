from app.evaluation.standardization import (
    JOB_CASES,
    SKILL_CASES,
    THRESHOLDS,
    evaluate_standardization,
)


def test_standardization_golden_set_is_versioned_and_has_boundary_coverage():
    assert len(JOB_CASES) >= 20
    assert len(SKILL_CASES) >= 20
    assert any(case[1] is None for case in SKILL_CASES)
    assert {case["expected"]["work_mode"] for case in JOB_CASES} >= {
        "onsite", "remote", "hybrid"
    }


def test_standardization_metrics_pass_declared_release_thresholds():
    report = evaluate_standardization()

    assert report["dataset_version"] == "standardization-golden-v1"
    assert report["passed"] is True
    for metric, threshold in THRESHOLDS.items():
        assert report["metrics"][metric] >= threshold
