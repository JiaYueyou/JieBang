from app.domain.data_quality import (
    normalize_job_body,
    simhash64,
    simhash_similarity,
)
from app.evaluation.phase2_golden import (
    RETRIEVAL_DISTRIBUTION,
    SKILL_PARAPHRASES,
    build_dataset,
    validate_dataset,
)


def _evidence_rows() -> list[dict]:
    return [
        {
            "evidence_id": "ev-java-1",
            "standard_job_id": 1,
            "standard_job_name": "Java开发工程师",
            "skill_id": 11,
            "skill_name": "Java",
            "source_platform": "iflytek",
            "quality_score": 0.91,
            "verification_status": "human_approved",
            "posted_at": "2026-07-01T00:00:00",
        },
        {
            "evidence_id": "ev-spring-1",
            "standard_job_id": 1,
            "standard_job_name": "Java开发工程师",
            "skill_id": 12,
            "skill_name": "Spring",
            "source_platform": "zhaopin",
            "quality_score": 0.88,
            "verification_status": "machine_validated",
            "posted_at": "2026-07-02T00:00:00",
        },
    ]


def test_phase2_dataset_has_required_scale_and_review_boundary():
    dataset = build_dataset(_evidence_rows())

    validate_dataset(dataset)

    assert len(dataset["duplicate_negative_cases"]) == 50
    assert len(dataset["retrieval_cases"]) == sum(RETRIEVAL_DISTRIBUTION.values())
    assert dataset["distribution"] == {
        "near_duplicate_negative": 50,
        **RETRIEVAL_DISTRIBUTION,
    }
    assert dataset["coverage_gate"] is False
    assert dataset["release_gate"] is False
    assert dataset["human_domain_gold"] is False
    assert {
        case["split"] for case in dataset["retrieval_cases"]
    } == {"development"}
    assert dataset["split_policy"] == {
        "strategy": "group_by_standard_job",
        "labels_frozen": True,
        "holdout_status": "not_available",
        "development": sum(RETRIEVAL_DISTRIBUTION.values()),
        "validation": 0,
        "test": 0,
        "standard_job_ids": {
            "development": [1],
            "validation": [],
            "test": [],
        },
        "reason": (
            "当前标准岗位不足 5 个，按岗位分组无法形成"
            "有代表性的验证集和冻结测试集。"
        ),
    }
    assert dataset["review_summary"]["approved"] == (
        50 + sum(RETRIEVAL_DISTRIBUTION.values())
    )


def test_coverage_ready_dataset_is_grouped_by_standard_job():
    skill_names = list(SKILL_PARAPHRASES)
    rows = [
        {
            "evidence_id": f"ev-{index:02d}",
            "standard_job_id": (index % 5) + 1,
            "standard_job_name": f"标准岗位{(index % 5) + 1}",
            "skill_id": index + 1,
            "skill_name": skill_names[index % len(skill_names)],
            "source_platform": (
                "iflytek" if index % 2 == 0 else "zhaopin"
            ),
            "quality_score": 0.9,
            "verification_status": "machine_validated",
            "posted_at": "2026-07-01T00:00:00",
        }
        for index in range(20)
    ]

    dataset = build_dataset(rows)
    validate_dataset(dataset)

    assert dataset["coverage_gate"] is True
    assert {
        case["split"] for case in dataset["retrieval_cases"]
    } == {"development", "validation", "test"}
    assert dataset["split_policy"]["standard_job_ids"] == {
        "development": [1, 2, 3],
        "validation": [4],
        "test": [5],
    }
    assert (
        dataset["split_policy"]["holdout_status"]
        == "frozen_after_retriever_tuning"
    )
    observed: dict[int, set[str]] = {}
    for case in dataset["retrieval_cases"]:
        job_id = case["evaluation_group"]["standard_job_id"]
        if job_id is not None:
            observed.setdefault(job_id, set()).add(case["split"])
    assert all(len(splits) == 1 for splits in observed.values())


def test_duplicate_negative_cases_stay_below_phase1_threshold():
    dataset = build_dataset(_evidence_rows())

    similarities = []
    for case in dataset["duplicate_negative_cases"]:
        existing = case["input"]["existing"]
        candidate = case["input"]["candidate"]
        similarities.append(
            simhash_similarity(
                simhash64(normalize_job_body(existing["jd_text"])),
                simhash64(normalize_job_body(candidate["jd_text"])),
            )
        )

    assert max(similarities) < 0.9
