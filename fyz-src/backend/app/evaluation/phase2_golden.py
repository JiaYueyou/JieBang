"""Build and validate the Phase 2 retrieval engineering seed set."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from itertools import cycle
from typing import Any

from app.core.time import utc_isoformat, utc_now

RETRIEVAL_DISTRIBUTION = {
    "skill_exact": 25,
    "responsibility_paraphrase": 25,
    "job_skill_filter": 20,
    "source_quality_filter": 15,
    "conflict_filter_no_answer": 15,
    "out_of_scope_no_answer": 20,
}

SKILL_PARAPHRASES = {
    "Git": "代码版本管理、分支协作与变更追踪能力",
    "Java": "面向对象的服务端编程语言与工程化能力",
    "MyBatis": "持久层对象映射与数据库访问框架能力",
    "MySQL": "关系型数据库设计、查询和性能调优能力",
    "Redis": "高并发缓存与键值数据存储能力",
    "Spring": "企业级依赖注入和应用容器框架能力",
    "Spring Boot": "微服务快速启动、自动配置和工程脚手架能力",
    "技术文档": "接口说明、研发规范和交付材料编写能力",
    "需求分析": "理解业务场景并拆解软件功能要求的能力",
}

SPLIT_ORDER = ("development", "validation", "test")


def _balanced_evidence_rows(
    evidence_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Round-robin jobs so every split receives representative cases."""

    grouped: dict[int, deque[dict[str, Any]]] = defaultdict(deque)
    for row in sorted(
        evidence_rows,
        key=lambda item: (
            item["standard_job_id"],
            item["skill_name"],
            -float(item["quality_score"]),
            item["evidence_id"],
        ),
    ):
        grouped[row["standard_job_id"]].append(row)

    ordered: list[dict[str, Any]] = []
    while any(grouped.values()):
        for job_id in sorted(grouped):
            if grouped[job_id]:
                ordered.append(grouped[job_id].popleft())
    return ordered


def _job_split_map(
    evidence_rows: list[dict[str, Any]],
) -> dict[int, str]:
    job_ids = sorted(
        {int(row["standard_job_id"]) for row in evidence_rows}
    )
    if len(job_ids) < 5:
        return {job_id: "development" for job_id in job_ids}

    development_count = max(3, round(len(job_ids) * 0.6))
    development_count = min(development_count, len(job_ids) - 2)
    remaining = len(job_ids) - development_count
    validation_count = max(1, remaining // 2)
    boundaries = (
        development_count,
        development_count + validation_count,
    )
    return {
        job_id: (
            "development"
            if index < boundaries[0]
            else (
                "validation"
                if index < boundaries[1]
                else "test"
            )
        )
        for index, job_id in enumerate(job_ids)
    }


def build_duplicate_negative_cases() -> list[dict[str, Any]]:
    role_pairs = [
        (
            "Java平台开发",
            "设计Spring服务、领域模型、接口和分布式事务。",
            "Java测试开发",
            "设计接口自动化、性能压测、测试平台和质量门禁。",
        ),
        (
            "Python后端开发",
            "建设FastAPI服务、鉴权、数据库事务和线上监控。",
            "Python数据分析",
            "使用Pandas分析指标、构建报表并解释业务波动。",
        ),
        (
            "算法工程师",
            "训练推荐模型、设计特征并评估离线与在线效果。",
            "数据平台工程师",
            "建设数仓、调度、数据血缘和批流处理任务。",
        ),
        (
            "前端工程师",
            "实现Vue组件、状态管理、浏览器性能和可访问性。",
            "UI设计师",
            "维护视觉规范、交互原型、图标和设计资产。",
        ),
        (
            "DevOps工程师",
            "维护CI流水线、容器编排、发布和可观测性。",
            "安全工程师",
            "执行漏洞治理、权限审计、威胁分析和安全响应。",
        ),
        (
            "产品经理",
            "定义用户问题、产品目标、需求优先级和验收标准。",
            "项目经理",
            "管理进度、资源、风险、里程碑和跨团队协作。",
        ),
        (
            "销售顾问",
            "负责商机挖掘、方案报价、合同推进和回款。",
            "客户成功",
            "负责客户启用、使用健康度、续约和价值交付。",
        ),
        (
            "招聘专员",
            "负责职位发布、候选人寻访、面试安排和录用跟进。",
            "HRBP",
            "支持组织诊断、人才盘点、绩效和管理者发展。",
        ),
        (
            "嵌入式开发",
            "开发驱动、实时系统、通信协议和硬件接口。",
            "硬件测试",
            "设计可靠性、信号完整性、环境和量产测试。",
        ),
        (
            "用户运营",
            "设计用户分层、留存活动、社群和生命周期策略。",
            "品牌营销",
            "规划品牌定位、传播内容、媒体和市场活动。",
        ),
    ]
    boilerplates = [
        "公司提供五险一金、双休和年度体检。",
        "要求具备良好沟通能力和团队合作精神。",
        "岗位位于合肥，支持培训和内部技术分享。",
        "依法享受节假日并提供规范劳动合同。",
        "欢迎主动负责、愿意持续学习的候选人。",
    ]
    reviewed_at = utc_isoformat(utc_now())
    cases: list[dict[str, Any]] = []
    for pair_index, (
        left_title,
        left_body,
        right_title,
        right_body,
    ) in enumerate(role_pairs, start=1):
        for boilerplate_index, boilerplate in enumerate(boilerplates, start=1):
            case_id = f"NEG-{pair_index:02d}-{boilerplate_index:02d}"
            cases.append(
                {
                    "id": case_id,
                    "category": "near_duplicate_negative",
                    "source_kind": "synthetic_boundary_case",
                    "input": {
                        "existing": {
                            "title": left_title,
                            "jd_text": f"{boilerplate}{left_body}",
                        },
                        "candidate": {
                            "title": right_title,
                            "jd_text": f"{boilerplate}{right_body}",
                        },
                    },
                    "expected": {
                        "duplicate": False,
                        "action": "keep_separate",
                    },
                    "rationale": (
                        "公共福利或通用软技能相似，不能覆盖岗位职责的实质差异。"
                    ),
                    "review": {
                        "status": "approved",
                        "reviewer": "codex-engineering-review",
                        "reviewed_at": reviewed_at,
                        "note": (
                            f"{left_title}与{right_title}职责和事实粒度不同，"
                            "必须保留为独立岗位证据。"
                        ),
                    },
                }
            )
    return cases


def build_retrieval_cases(
    evidence_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not evidence_rows:
        raise ValueError("No active evidence is available")
    reviewed_at = utc_isoformat(utc_now())
    ordered = _balanced_evidence_rows(evidence_rows)
    row_cycle = cycle(ordered)
    semantic_rows = [
        row
        for row in ordered
        if row["skill_name"] in SKILL_PARAPHRASES
    ]
    if not semantic_rows:
        raise ValueError(
            "No evidence has a reviewed responsibility paraphrase"
        )
    semantic_row_cycle = cycle(semantic_rows)
    job_splits = _job_split_map(ordered)
    split_ready = len(set(job_splits.values())) == 3
    all_ids = [row["evidence_id"] for row in ordered]

    def expected(
        row: dict[str, Any],
        *,
        source_platform: str | None = None,
        minimum_quality_score: float = 0,
    ) -> list[str]:
        evidence_ids: list[str] = []
        seen_groups: set[str] = set()
        for item in ordered:
            if (
                item["standard_job_id"] != row["standard_job_id"]
                or item["skill_id"] != row["skill_id"]
                or (
                    source_platform is not None
                    and item["source_platform"] != source_platform
                )
                or float(item["quality_score"]) < minimum_quality_score
            ):
                continue
            group = item.get("near_duplicate_group_id")
            if group and group in seen_groups:
                continue
            if group:
                seen_groups.add(group)
            evidence_ids.append(item["evidence_id"])
            if len(evidence_ids) >= 5:
                break
        return evidence_ids

    cases: list[dict[str, Any]] = []

    def add_case(
        *,
        category: str,
        ordinal: int,
        row: dict[str, Any] | None,
        query: str,
        filters: dict[str, Any],
        expected_ids: list[str],
        answer_mode: str,
        note: str,
    ) -> None:
        standard_job_id = (
            int(row["standard_job_id"]) if row is not None else None
        )
        split = (
            job_splits[standard_job_id]
            if standard_job_id is not None
            else (
                (
                    "development"
                    if ordinal < 12
                    else ("validation" if ordinal < 16 else "test")
                )
                if split_ready
                else "development"
            )
        )
        cases.append(
            {
                "id": f"RET-{len(cases) + 1:03d}",
                "category": category,
                "corpus_kind": "real_mysql_evidence",
                "query": query,
                "filters": filters,
                "expected_evidence_ids": expected_ids,
                "forbidden_evidence_ids": (
                    [] if expected_ids else all_ids
                ),
                "answer_mode": answer_mode,
                "top_k": 5,
                "split": split,
                "evaluation_group": {
                    "standard_job_id": standard_job_id,
                    "standard_job_name": (
                        row["standard_job_name"]
                        if row is not None
                        else None
                    ),
                },
                "rationale": note,
                "review": {
                    "status": "approved",
                    "reviewer": "codex-engineering-review",
                    "reviewed_at": reviewed_at,
                    "note": (
                        "标签由 MySQL 标准岗位、技能事实、来源和质量外键生成，"
                        "仅作为工程检索回归。"
                    ),
                },
            }
        )

    for ordinal in range(RETRIEVAL_DISTRIBUTION["skill_exact"]):
        row = next(row_cycle)
        add_case(
            category="skill_exact",
            ordinal=ordinal,
            row=row,
            query=row["skill_name"],
            filters={
                "standard_job_id": row["standard_job_id"],
            },
            expected_ids=expected(row),
            answer_mode="grounded",
            note="技能原词应召回同一正式技能事实的原文证据。",
        )

    for ordinal in range(
        RETRIEVAL_DISTRIBUTION["responsibility_paraphrase"]
    ):
        row = next(semantic_row_cycle)
        paraphrase = SKILL_PARAPHRASES.get(row["skill_name"])
        if not paraphrase:
            raise ValueError(
                "Missing reviewed paraphrase for skill "
                f"{row['skill_name']!r}"
            )
        add_case(
            category="responsibility_paraphrase",
            ordinal=ordinal,
            row=row,
            query=f"{row['standard_job_name']}通常要求{paraphrase}",
            filters={
                "standard_job_id": row["standard_job_id"],
            },
            expected_ids=expected(row),
            answer_mode="grounded",
            note=(
                "岗位能力改写不包含技能规范名，应依靠语义或同义表达"
                "回链对应技能证据。"
            ),
        )

    for ordinal in range(RETRIEVAL_DISTRIBUTION["job_skill_filter"]):
        row = next(row_cycle)
        add_case(
            category="job_skill_filter",
            ordinal=ordinal,
            row=row,
            query=f"{row['standard_job_name']} {row['skill_name']}",
            filters={
                "standard_job_id": row["standard_job_id"],
                "skill_ids": [row["skill_id"]],
            },
            expected_ids=expected(row),
            answer_mode="grounded",
            note="岗位和技能过滤不得返回其他事实关系。",
        )

    for ordinal in range(RETRIEVAL_DISTRIBUTION["source_quality_filter"]):
        row = next(row_cycle)
        minimum_quality = max(
            0.55,
            round(float(row["quality_score"]) - 0.01, 4),
        )
        expected_ids = expected(
            row,
            source_platform=row["source_platform"],
            minimum_quality_score=minimum_quality,
        )
        add_case(
            category="source_quality_filter",
            ordinal=ordinal,
            row=row,
            query=row["skill_name"],
            filters={
                "standard_job_id": row["standard_job_id"],
                "skill_ids": [row["skill_id"]],
                "source_platforms": [row["source_platform"]],
                "minimum_quality_score": minimum_quality,
            },
            expected_ids=expected_ids,
            answer_mode="grounded",
            note="来源和质量门禁必须同时生效。",
        )

    for ordinal in range(
        RETRIEVAL_DISTRIBUTION["conflict_filter_no_answer"]
    ):
        row = next(row_cycle)
        add_case(
            category="conflict_filter_no_answer",
            ordinal=ordinal,
            row=row,
            query=row["skill_name"],
            filters={
                "standard_job_id": row["standard_job_id"],
                "source_platforms": ["不存在的数据源"],
            },
            expected_ids=[],
            answer_mode="insufficient_evidence",
            note="过滤条件排除全部来源时必须返回证据不足。",
        )

    out_of_scope_queries = [
        "quantum photolithography calibration",
        "marine coral genome sequencing",
        "medieval manuscript restoration",
        "orbital telescope mirror coating",
        "deep sea submersible ballast",
        "nuclear fusion plasma confinement",
        "archaeological pottery thermoluminescence",
        "avian migration isotope tracing",
        "volcanic ash mineral classification",
        "satellite attitude control gyroscope",
        "cryogenic superconducting magnet winding",
        "paleoclimate ice core drilling",
        "ocean salinity buoy calibration",
        "radio telescope interference mitigation",
        "plant pathology spore microscopy",
        "aerospace composite fatigue testing",
        "seismic tomography inversion",
        "ancient coin metallurgical analysis",
        "glacier mass balance surveying",
        "particle accelerator beam collimation",
    ]
    for ordinal, query in enumerate(out_of_scope_queries):
        add_case(
            category="out_of_scope_no_answer",
            ordinal=ordinal,
            row=None,
            query=query,
            filters={},
            expected_ids=[],
            answer_mode="insufficient_evidence",
            note="语料库外问题不得由无关岗位证据补答。",
        )

    if len(cases) != sum(RETRIEVAL_DISTRIBUTION.values()):
        raise AssertionError("Retrieval distribution does not total 120")
    return cases


def build_dataset(evidence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    duplicate_cases = build_duplicate_negative_cases()
    retrieval_cases = build_retrieval_cases(evidence_rows)
    coverage = {
        "evidence_count": len(evidence_rows),
        "standard_job_count": len(
            {row["standard_job_id"] for row in evidence_rows}
        ),
        "skill_count": len({row["skill_id"] for row in evidence_rows}),
        "source_platform_count": len(
            {row["source_platform"] for row in evidence_rows}
        ),
    }
    coverage_gate = (
        coverage["standard_job_count"] >= 5
        and coverage["skill_count"] >= 20
        and coverage["source_platform_count"] >= 2
    )
    split_counts = Counter(
        case["split"] for case in retrieval_cases
    )
    split_jobs = {
        split: sorted(
            {
                case["evaluation_group"]["standard_job_id"]
                for case in retrieval_cases
                if case["split"] == split
                and case["evaluation_group"]["standard_job_id"] is not None
            }
        )
        for split in SPLIT_ORDER
    }
    return {
        "schema_version": "phase2-retrieval-golden-v1",
        "title": "FYZ Phase 2 检索与近重复负样本工程评测集",
        "generated_at": utc_isoformat(utc_now()),
        "curation_status": (
            "engineering_reviewed_split_ready"
            if coverage_gate
            else "engineering_reviewed_coverage_blocked"
        ),
        "release_gate": False,
        "coverage_gate": coverage_gate,
        "human_domain_gold": False,
        "coverage": coverage,
        "split_policy": {
            "strategy": "group_by_standard_job",
            "labels_frozen": True,
            "holdout_status": (
                "frozen_after_retriever_tuning"
                if coverage_gate
                else "not_available"
            ),
            "development": split_counts.get("development", 0),
            "validation": split_counts.get("validation", 0),
            "test": split_counts.get("test", 0),
            "standard_job_ids": split_jobs,
            "reason": (
                "已按标准岗位分组形成开发、验证和冻结测试集；"
                "同一标准岗位不会跨分区。"
                if coverage_gate
                else (
                    "当前标准岗位不足 5 个，按岗位分组无法形成"
                    "有代表性的验证集和冻结测试集。"
                )
            ),
        },
        "distribution": {
            "near_duplicate_negative": len(duplicate_cases),
            **RETRIEVAL_DISTRIBUTION,
        },
        "duplicate_negative_cases": duplicate_cases,
        "retrieval_cases": retrieval_cases,
        "review_summary": {
            "review_type": "deterministic_fk_and_boundary_engineering_review",
            "reviewer": "codex-engineering-review",
            "approved": len(duplicate_cases) + len(retrieval_cases),
            "rejected": 0,
            "total": len(duplicate_cases) + len(retrieval_cases),
            "human_domain_gold": False,
            "coverage_release_blocked": not coverage_gate,
        },
    }


def validate_dataset(dataset: dict[str, Any]) -> None:
    duplicate_cases = dataset.get("duplicate_negative_cases", [])
    retrieval_cases = dataset.get("retrieval_cases", [])
    if len(duplicate_cases) != 50:
        raise ValueError("Phase 2 requires 50 near-duplicate negative cases")
    if len(retrieval_cases) != 120:
        raise ValueError("Phase 2 requires 120 retrieval cases")
    ids = [case["id"] for case in duplicate_cases + retrieval_cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Case IDs must be unique")
    distribution = Counter(case["category"] for case in retrieval_cases)
    if dict(distribution) != RETRIEVAL_DISTRIBUTION:
        raise ValueError("Retrieval distribution mismatch")
    for case in duplicate_cases + retrieval_cases:
        review = case.get("review") or {}
        if review.get("status") != "approved" or not review.get("reviewer"):
            raise ValueError(f"Case {case['id']} is not engineering reviewed")
    if dataset.get("human_domain_gold") is not False:
        raise ValueError("Engineering seed set must not claim human domain gold")
    split_policy = dataset.get("split_policy") or {}
    split_counts = Counter(case.get("split") for case in retrieval_cases)
    declared_counts = {
        split: int(split_policy.get(split, 0))
        for split in SPLIT_ORDER
    }
    if (
        split_policy.get("labels_frozen") is not True
        or declared_counts != {
            split: split_counts.get(split, 0)
            for split in SPLIT_ORDER
        }
    ):
        raise ValueError("Split policy does not match retrieval cases")

    if dataset.get("coverage_gate") is True:
        if any(declared_counts[split] <= 0 for split in SPLIT_ORDER):
            raise ValueError(
                "Coverage-ready set requires development, validation and test"
            )
        job_splits: dict[int, str] = {}
        for case in retrieval_cases:
            group = case.get("evaluation_group") or {}
            job_id = group.get("standard_job_id")
            if job_id is None:
                continue
            existing = job_splits.setdefault(job_id, case["split"])
            if existing != case["split"]:
                raise ValueError(
                    f"Standard job {job_id} crosses evaluation splits"
                )
    elif (
        declared_counts["development"] != 120
        or declared_counts["validation"] != 0
        or declared_counts["test"] != 0
    ):
        raise ValueError("Coverage-blocked set must remain development-only")
