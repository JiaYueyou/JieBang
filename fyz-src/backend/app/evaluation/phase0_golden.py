"""Deterministic Phase 0 evaluation seed set.

The generated cases are deliberately marked as pending human review. They are
stable regression inputs, but do not become a release-quality golden set until
the expected results have been reviewed and approved.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

EXPECTED_DISTRIBUTION = {
    "data_duplicate": 20,
    "data_freshness": 15,
    "job_skill_consistency": 20,
    "graph_grounding": 15,
    "match_explanation": 15,
    "jd_career_boundary": 15,
}


def _review() -> dict[str, Any]:
    return {
        "status": "pending",
        "reviewer": None,
        "reviewed_at": None,
        "note": "Phase 0 seeded expectation; requires domain review.",
    }


def _case(
    case_id: str,
    category: str,
    input_data: dict[str, Any],
    evidence: list[dict[str, Any]],
    expected: dict[str, Any],
    rationale: str,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "category": category,
        "source_kind": "synthetic_boundary_case",
        "input": input_data,
        "evidence": evidence,
        "expected": expected,
        "rationale": rationale,
        "review": _review(),
    }


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    for index in range(1, 21):
        near_duplicate = index % 2 == 0
        title = f"Python开发工程师-{index}"
        candidate = title.replace("开发", "研发") if near_duplicate else title
        cases.append(
            _case(
                f"DUP-{index:03d}",
                "data_duplicate",
                {
                    "existing": {
                        "source": "iflytek",
                        "external_id": f"ifly-{index:03d}",
                        "title": title,
                        "company": "示例科技",
                        "jd_text": "负责Python服务开发、MySQL数据建模与接口维护。",
                    },
                    "candidate": {
                        "source": "zhaopin" if near_duplicate else "iflytek",
                        "external_id": f"zl-{index:03d}" if near_duplicate else f"ifly-{index:03d}",
                        "title": candidate,
                        "company": "示例科技有限公司" if near_duplicate else "示例科技",
                        "jd_text": "负责 Python 服务研发，包含 MySQL 数据建模和 API 维护。",
                    },
                },
                [{"type": "job_text_pair", "ref": f"pair-{index:03d}"}],
                {
                    "duplicate": True,
                    "match_type": "near_duplicate" if near_duplicate else "exact_identity",
                    "action": "merge_source_evidence",
                },
                "同一岗位的来源差异不应产生第二条公开事实。",
            )
        )

    for index in range(1, 16):
        expired = index <= 10
        posted_at = f"2025-{(index % 9) + 1:02d}-01" if expired else f"2026-07-{index:02d}"
        cases.append(
            _case(
                f"FRESH-{index:03d}",
                "data_freshness",
                {
                    "posted_at": posted_at,
                    "observed_at": "2026-07-30T00:00:00Z",
                    "source_status": "active",
                    "max_age_days": 90,
                },
                [{"type": "source_timestamp", "value": posted_at}],
                {
                    "freshness": "expired" if expired else "current",
                    "publishable": not expired,
                    "requires_refresh": expired,
                },
                "超过时效阈值的岗位不能继续作为可发布事实或高权重检索证据。",
            )
        )

    skills = ["Python", "Java", "MySQL", "Redis", "Vue", "FastAPI", "Docker", "Neo4j"]
    for index in range(1, 21):
        skill = skills[(index - 1) % len(skills)]
        supported = index % 2 == 1
        jd_text = (
            f"负责后端平台开发，必须熟练使用{skill}，并能提供项目案例。"
            if supported
            else "负责客户运营、活动策划与内容审核，不涉及软件研发。"
        )
        cases.append(
            _case(
                f"CONSIST-{index:03d}",
                "job_skill_consistency",
                {"job_title": "平台工程师" if supported else "内容运营", "jd_text": jd_text, "skill": skill},
                [{"type": "jd_excerpt", "text": jd_text}],
                {
                    "fact_supported": supported,
                    "verification_status": "machine_validated" if supported else "rejected",
                    "publishable": supported,
                },
                "技能事实必须能回指到岗位原文，标题或模型常识不能代替证据。",
            )
        )

    for index in range(1, 16):
        grounded = index % 3 != 0
        evidence_ids = [f"source-{index:03d}", f"fact-{index:03d}"] if grounded else []
        cases.append(
            _case(
                f"GRAPH-{index:03d}",
                "graph_grounding",
                {
                    "candidate_relation": {
                        "source": "skill:python",
                        "relation": "PREREQUISITE",
                        "target": f"knowledge:{index:03d}",
                    }
                },
                [{"type": "fact_ref", "id": item} for item in evidence_ids],
                {
                    "grounded": grounded,
                    "write_to_published_graph": grounded,
                    "fallback": None if grounded else "insufficient_evidence",
                },
                "图谱深层关系只有在证据标识完整时才能进入发布图。",
            )
        )

    for index in range(1, 16):
        evidence_available = index % 4 != 0
        evidence = (
            [{"type": "resume_skill", "id": f"resume-skill-{index:03d}", "skill": "Python"}]
            if evidence_available
            else []
        )
        cases.append(
            _case(
                f"MATCH-{index:03d}",
                "match_explanation",
                {
                    "score": 82,
                    "matched_skills": ["Python"],
                    "missing_skills": ["Redis"],
                    "requested_claim": "候选人具备高并发Redis调优经验",
                },
                evidence,
                {
                    "answer_mode": "grounded" if evidence_available else "insufficient_evidence",
                    "must_cite_evidence_ids": evidence_available,
                    "forbidden_claim": "高并发Redis调优经验",
                },
                "匹配解释只能复述已保存证据，不能把缺失技能改写为候选人经验。",
            )
        )

    for index in range(1, 16):
        has_enterprise_context = index % 3 != 0
        context = (
            [{"type": "enterprise_position", "id": f"position-{index:03d}", "name": "高级后端工程师"}]
            if has_enterprise_context
            else []
        )
        cases.append(
            _case(
                f"BOUNDARY-{index:03d}",
                "jd_career_boundary",
                {
                    "task": "career_plan" if index % 2 else "jd_generation",
                    "skills": ["Python", "MySQL"],
                    "request": "给出确定晋升结论并补充公司内部薪酬区间",
                },
                context,
                {
                    "answer_mode": "grounded" if has_enterprise_context else "insufficient_evidence",
                    "must_label_suggestion": True,
                    "must_not_invent_salary": True,
                    "requires_human_approval": True,
                },
                "职业与JD Agent必须区分事实、建议和缺失信息，并保留人工审批边界。",
            )
        )

    return cases


def build_dataset() -> dict[str, Any]:
    cases = build_cases()
    return {
        "schema_version": "phase0-golden-v1",
        "title": "FYZ Phase 0 Agent与数据链路评测种子集",
        "curation_status": "seeded_requires_human_review",
        "release_gate": False,
        "distribution": dict(Counter(case["category"] for case in cases)),
        "cases": cases,
    }


def audit_case(case: dict[str, Any]) -> tuple[bool, str]:
    """Independently verify one deterministic synthetic boundary case."""

    category = case.get("category")
    input_data = case.get("input", {})
    evidence = case.get("evidence", [])
    expected = case.get("expected", {})

    if category == "data_duplicate":
        existing = input_data.get("existing", {})
        candidate = input_data.get("candidate", {})
        exact_identity = (
            existing.get("source") == candidate.get("source")
            and existing.get("external_id") == candidate.get("external_id")
        )
        expected_type = "exact_identity" if exact_identity else "near_duplicate"
        passed = (
            expected.get("duplicate") is True
            and expected.get("match_type") == expected_type
            and expected.get("action") == "merge_source_evidence"
        )
        return passed, f"重复类型应为 {expected_type}，来源证据应合并而非删除。"

    if category == "data_freshness":
        try:
            posted_at = datetime.fromisoformat(str(input_data["posted_at"]).replace("Z", "+00:00"))
            observed_at = datetime.fromisoformat(
                str(input_data["observed_at"]).replace("Z", "+00:00")
            )
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=observed_at.tzinfo)
            expired = (observed_at - posted_at).days > int(input_data["max_age_days"])
        except (KeyError, TypeError, ValueError):
            return False, "日期或时效阈值无法解析。"
        passed = (
            expected.get("freshness") == ("expired" if expired else "current")
            and expected.get("publishable") is (not expired)
            and expected.get("requires_refresh") is expired
        )
        return passed, f"按 observed_at 与 {input_data['max_age_days']} 天窗口复算时效。"

    if category == "job_skill_consistency":
        skill = str(input_data.get("skill", "")).lower()
        supported = bool(skill and skill in str(input_data.get("jd_text", "")).lower())
        passed = (
            expected.get("fact_supported") is supported
            and expected.get("publishable") is supported
            and expected.get("verification_status")
            == ("machine_validated" if supported else "rejected")
        )
        return passed, "只认可 JD 原文直接出现的技能证据，岗位标题不能代替原文。"

    if category == "graph_grounding":
        grounded = bool(evidence)
        passed = (
            expected.get("grounded") is grounded
            and expected.get("write_to_published_graph") is grounded
            and expected.get("fallback")
            == (None if grounded else "insufficient_evidence")
        )
        return passed, "合成样本以证据引用是否存在验证发布边界，真实数据仍需语义蕴含校验。"

    if category == "match_explanation":
        evidence_available = bool(evidence)
        passed = (
            expected.get("answer_mode")
            == ("grounded" if evidence_available else "insufficient_evidence")
            and expected.get("must_cite_evidence_ids") is evidence_available
            and expected.get("forbidden_claim") == "高并发Redis调优经验"
        )
        return passed, "缺失技能不能被改写为候选人经验，正向结论必须引用简历证据。"

    if category == "jd_career_boundary":
        context_available = bool(evidence)
        passed = (
            expected.get("answer_mode")
            == ("grounded" if context_available else "insufficient_evidence")
            and expected.get("must_label_suggestion") is True
            and expected.get("must_not_invent_salary") is True
            and expected.get("requires_human_approval") is True
        )
        return passed, "建议必须标注，薪酬和晋升不得无证据生成，最终结果保留人工批准。"

    return False, f"未知评测分类：{category}"


def finalize_engineering_review(
    dataset: dict[str, Any],
    *,
    reviewer: str,
    reviewed_at: str,
    authorization: str,
) -> dict[str, Any]:
    """Fill transparent engineering-review records without claiming human labeling."""

    approved = 0
    rejected = 0
    for case in dataset.get("cases", []):
        passed, note = audit_case(case)
        case["review"] = {
            "status": "approved" if passed else "rejected",
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "note": note,
        }
        if passed:
            approved += 1
        else:
            rejected += 1

    dataset["curation_status"] = (
        "engineering_reviewed_user_authorized"
        if rejected == 0
        else "engineering_review_requires_correction"
    )
    dataset["release_gate"] = rejected == 0
    dataset["review_summary"] = {
        "review_type": "codex_engineering_semantic_review",
        "human_domain_gold": False,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "authorization": authorization,
        "approved": approved,
        "rejected": rejected,
        "total": approved + rejected,
    }
    return dataset


def validate_dataset(dataset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = dataset.get("cases")
    if not isinstance(cases, list):
        return ["cases must be a list"]
    if len(cases) != 100:
        errors.append(f"expected 100 cases, got {len(cases)}")
    ids = [case.get("id") for case in cases]
    if len(set(ids)) != len(ids):
        errors.append("case ids must be unique")
    distribution = Counter(case.get("category") for case in cases)
    if dict(distribution) != EXPECTED_DISTRIBUTION:
        errors.append(
            f"distribution mismatch: expected {EXPECTED_DISTRIBUTION}, got {dict(distribution)}"
        )
    for case in cases:
        case_id = case.get("id", "<missing>")
        for field in ("input", "evidence", "expected", "rationale", "review"):
            if field not in case:
                errors.append(f"{case_id}: missing {field}")
        if case.get("review", {}).get("status") not in {"pending", "approved", "rejected"}:
            errors.append(f"{case_id}: invalid review status")
    if dataset.get("release_gate") is True:
        if any(case.get("review", {}).get("status") != "approved" for case in cases):
            errors.append("release_gate requires every case to be approved")
        summary = dataset.get("review_summary", {})
        if summary.get("review_type") != "codex_engineering_semantic_review":
            errors.append("release_gate requires a declared review summary")
        if summary.get("human_domain_gold") is not False:
            errors.append("engineering review must not claim human domain gold")
    return errors
