from app.evaluation.phase0_golden import (
    EXPECTED_DISTRIBUTION,
    build_dataset,
    finalize_engineering_review,
    validate_dataset,
)


def test_phase0_golden_seed_has_required_distribution():
    dataset = build_dataset()

    assert len(dataset["cases"]) == 100
    assert dataset["distribution"] == EXPECTED_DISTRIBUTION
    assert dataset["curation_status"] == "seeded_requires_human_review"
    assert dataset["release_gate"] is False
    assert validate_dataset(dataset) == []


def test_phase0_golden_seed_has_traceable_expected_results():
    dataset = build_dataset()

    assert all(case["evidence"] is not None for case in dataset["cases"])
    assert all(case["expected"] for case in dataset["cases"])
    assert all(case["review"]["status"] == "pending" for case in dataset["cases"])


def test_phase0_golden_validator_rejects_duplicate_ids():
    dataset = build_dataset()
    dataset["cases"][1]["id"] = dataset["cases"][0]["id"]

    assert "case ids must be unique" in validate_dataset(dataset)


def test_phase0_engineering_review_is_transparent_and_releasable():
    dataset = finalize_engineering_review(
        build_dataset(),
        reviewer="test-reviewer",
        reviewed_at="2026-07-30T15:00:00Z",
        authorization="test-user-authorization",
    )

    assert dataset["release_gate"] is True
    assert dataset["review_summary"]["approved"] == 100
    assert dataset["review_summary"]["rejected"] == 0
    assert dataset["review_summary"]["human_domain_gold"] is False
    assert validate_dataset(dataset) == []
