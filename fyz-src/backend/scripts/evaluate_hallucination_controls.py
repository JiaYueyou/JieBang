"""Evaluate observable anti-hallucination controls for every AI output surface."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AGENT_SRC = ROOT / "agent-development" / "src"
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_SRC))
sys.path.insert(0, str(BACKEND_ROOT))

from jiebang_agents.career_planning import CareerPlanCandidate, CareerPlanningAgent  # noqa: E402
from jiebang_agents.career_planning.schemas import LearningStep  # noqa: E402
from jiebang_agents.graph_enrichment.acceptance import evaluate_l45_output  # noqa: E402
from jiebang_agents.graph_enrichment.schemas import GraphEnrichmentOutput, SkillGraphCompletionInput  # noqa: E402
from jiebang_agents.jd_generation import (  # noqa: E402
    GenerateJDRequest, JDGenerationAgent, JDInputSuggestionRequest,
    LLMGeneratedJDDraft, LLMJDInputSuggestion,
)
from app.services.agent_grounding_service import semantic_grounding_score  # noqa: E402
from app.services.skill_service import SkillService  # noqa: E402


class StaticProvider:
    provider_name = "benchmark"
    model_name = "controlled-output"
    enabled = True

    def __init__(self, output) -> None:
        self.output = output

    async def generate_structured(self, **kwargs):
        return kwargs["response_schema"].model_validate(
            self.output.model_dump(mode="json")
        )


class DisabledProvider:
    provider_name = "disabled"
    model_name = "none"
    enabled = False


def make_case(case_id, surface, scenario, input_data, expected_effect,
              actual_result, passed, *, unsupported=False):
    return {
        "id": case_id,
        "ai_surface": surface,
        "scenario": scenario,
        "input": input_data,
        "expected_visible_effect": expected_effect,
        "actual_result": actual_result,
        "unsupported_claim": unsupported,
        "test_passed": bool(passed),
    }


async def jd_generation_cases():
    request = GenerateJDRequest(
        target="public", title="后端工程师", level="senior",
        department="研发中心", skills_input="Python, FastAPI",
    )
    candidate = LLMGeneratedJDDraft(
        title="首席量子芯片科学家",
        responsibilities=["负责 FastAPI 服务设计"],
        requirements=["熟悉 Python"], skills=["Python", "FastAPI"],
        trainable_skills=["量子芯片流片"],
        transfer_profile=["未经输入支持的内部履历"],
        manager_confirmations=["未经输入支持的审批结论"],
        jd_text="后端工程师岗位草稿",
        assumptions=["薪资和到岗时间未提供"], warnings=["需招聘负责人复核"],
    )
    output = await JDGenerationAgent(StaticProvider(candidate)).generate(request)
    fallback = await JDGenerationAgent(DisabledProvider()).generate(request)
    return [
        make_case("AH-JDG-01", "JD生成", "模型尝试覆盖系统岗位名称", {"requested_title": request.title, "model_title": candidate.title}, "岗位名称保持为用户确认值", {"title": output.title}, output.title == request.title, unsupported=True),
        make_case("AH-JDG-02", "JD生成", "公开招聘输出夹带内部流转字段", {"target": "public", "model_trainable_skills": candidate.trainable_skills}, "公开招聘草稿不展示内部流转字段", {"trainable_skills": output.trainable_skills, "transfer_profile": output.transfer_profile, "manager_confirmations": output.manager_confirmations}, not output.trainable_skills and not output.transfer_profile and not output.manager_confirmations, unsupported=True),
        make_case("AH-JDG-03", "JD生成", "模型输出未知薪资与到岗信息", {"assumptions": candidate.assumptions}, "未知信息进入假设和复核区域", {"assumptions": output.assumptions, "warnings": output.warnings}, bool(output.assumptions and output.warnings)),
        make_case("AH-JDG-04", "JD生成", "模型服务不可用", {"provider_enabled": False}, "返回可编辑的确定性模板并标注生成模式", {"generation_mode": fallback.generation_mode, "warnings": fallback.warnings}, fallback.generation_mode == "template" and bool(fallback.warnings)),
    ]


async def jd_suggestion_cases():
    request = JDInputSuggestionRequest(
        title="高级 Java 开发工程师", mode="requirements",
        level="senior", department="后台开发组",
    )
    output = await JDGenerationAgent(StaticProvider(LLMJDInputSuggestion(
        suggestions=["Java", "Spring Boot", "MySQL"],
        warnings=["请结合团队技术栈复核"],
    ))).suggest_input(request)
    fallback = await JDGenerationAgent(DisabledProvider()).suggest_input(request)
    dumped = output.model_dump()
    return [
        make_case("AH-JDS-01", "JD输入建议", "模型仅返回候选要求", {"mode": request.mode.value}, "建议保持候选列表形态，由用户选择后写入", {"suggestions": output.suggestions, "generation_mode": output.generation_mode}, output.generation_mode == "llm" and len(output.suggestions) == 3),
        make_case("AH-JDS-02", "JD输入建议", "模型提示需要业务确认", {"model_warnings": ["请结合团队技术栈复核"]}, "复核提示随建议同步展示", {"warnings": output.warnings}, bool(output.warnings)),
        make_case("AH-JDS-03", "JD输入建议", "模型不可用时请求建议", {"provider_enabled": False, "title": request.title}, "返回与岗位名称匹配的确定性技能建议", {"suggestions": fallback.suggestions, "generation_mode": fallback.generation_mode}, fallback.generation_mode == "template" and "Java" in fallback.suggestions),
        make_case("AH-JDS-04", "JD输入建议", "建议接口被要求生成完整JD", {"mode": request.mode.value, "returned_fields": sorted(dumped)}, "接口仅返回建议和复核信息，不产生可自动发布JD", {"has_jd_text": "jd_text" in dumped}, "jd_text" not in dumped, unsupported=True),
    ]


def skill_extraction_cases():
    source = "负责 FastAPI 服务开发，并维护 MySQL 数据库。"
    rows = [
        ("AH-SK-01", "负责 FastAPI 服务开发", True),
        ("AH-SK-02", "维护 MySQL 数据库", True),
        ("AH-SK-03", "精通量子芯片流片", False),
        ("AH-SK-04", "", False),
    ]
    results = []
    for case_id, evidence, expected in rows:
        grounded = SkillService._llm_evidence_is_grounded(
            evidence, jd_text=source, responsibilities="", requirements=""
        )
        results.append(make_case(
            case_id, "岗位技能抽取增强",
            "模型技能证据可在JD原文定位" if expected else "模型技能证据缺失或无法在JD原文定位",
            {"jd_text": source, "model_evidence": evidence},
            "保留为待审核技能事实" if expected else "不进入技能事实与能力图谱",
            {"evidence_grounded": grounded, "persistence": "pending_review" if grounded else "blocked"},
            grounded == expected, unsupported=not expected,
        ))
    return results


def career_cases():
    candidate = CareerPlanCandidate(
        job_id=1, job="大模型应用开发", current_match=40,
        after_match=80, recommend_score=48,
        existing=["Python"], gaps=["Transformer", "RAG"],
    )
    proposed = [
        LearningStep(skill="Python", time="1周", difficulty="easy"),
        LearningStep(skill="Transformer架构深入", time="2周", difficulty="hard"),
        LearningStep(skill="量子芯片流片", time="4周", difficulty="hard"),
    ]
    actual = CareerPlanningAgent._validated_learning_plan(
        candidate=candidate, proposed=proposed, time_budget_weeks=8
    )
    skills = [item.skill for item in actual]
    return [
        make_case("AH-CP-01", "职业规划", "模型把已有Python列为学习缺口", {"existing": candidate.existing, "proposed": "Python"}, "已有技能不重复进入差距路径", {"learning_skills": skills}, "Python" not in skills, unsupported=True),
        make_case("AH-CP-02", "职业规划", "模型生成与真实差距相符的Transformer步骤", {"gaps": candidate.gaps, "proposed": "Transformer架构深入"}, "归一到岗位真实技能缺口", {"learning_skills": skills}, "Transformer" in skills),
        make_case("AH-CP-03", "职业规划", "模型生成岗位差距之外的量子芯片步骤", {"gaps": candidate.gaps, "proposed": "量子芯片流片"}, "移除与岗位差距无关的学习步骤", {"learning_skills": skills}, "量子芯片流片" not in skills, unsupported=True),
        make_case("AH-CP-04", "职业规划", "模型漏掉RAG差距", {"gaps": candidate.gaps, "model_steps": [item.skill for item in proposed]}, "使用确定性差距补齐学习步骤", {"learning_skills": skills}, "RAG" in skills),
    ]


def match_cases():
    known_ids = {"match_evidence:1", "match_evidence:2"}
    rows = [
        ("AH-ME-01", "Python项目经验", "候选人具备Python项目经验", "简历显示Python项目经验", ["match_evidence:1"], True),
        ("AH-ME-02", "量子芯片", "候选人精通量子芯片流片", "简历显示Vue页面开发经验", ["match_evidence:1"], False),
        ("AH-ME-03", "FastAPI", "候选人具备FastAPI服务经验", "岗位要求FastAPI服务开发", ["unknown:999"], False),
        ("AH-ME-04", "Redis", "岗位存在Redis能力差距", "岗位要求Redis缓存设计", ["match_evidence:2"], True),
    ]
    results = []
    for case_id, anchor, claim_text, evidence_text, evidence_ids, expected in rows:
        score = semantic_grounding_score(anchor, claim_text, evidence_text)
        known = set(evidence_ids).issubset(known_ids)
        accepted = known and score >= 0.12
        reason = None if accepted else ("unknown_evidence_id" if not known else "semantic_mismatch")
        results.append(make_case(
            case_id, "人岗匹配解释", "生成解释引用匹配快照并校验语义支持",
            {"claim": claim_text, "evidence_text": evidence_text, "evidence_ids": evidence_ids},
            "展示解释及其原文证据" if expected else "拒绝解释并显示证据校验原因",
            {"grounding_score": round(score, 6), "accepted": accepted, "reason": reason},
            accepted == expected, unsupported=not expected,
        ))
    return results


def graph_cases():
    request = SkillGraphCompletionInput.model_validate({
        "job_directions": ["大模型应用工程师"],
        "skill_area": "检索增强生成", "tech_stack": "Python / FastAPI / 向量数据库",
        "evidence": [
            {"evidence_id": "JD-IFLY-001", "source": "科大讯飞招聘", "text": "岗位要求掌握 Python、向量数据库和 RAG 评估。"},
            {"evidence_id": "JD-ZL-001", "source": "智联招聘", "text": "负责 FastAPI 服务和检索增强生成系统开发。"},
        ],
    })

    def output(confidence=0.92, evidence_ids=None):
        ids = evidence_ids or ["JD-IFLY-001", "JD-ZL-001"]
        return GraphEnrichmentOutput.model_validate({
            "skill_name": "RAG 工程", "job_directions": ["大模型应用工程师"],
            "skill_area": "检索增强生成",
            "tech_points": [{"name": "向量检索", "category": "component", "detail": "证据支持的技术点", "confidence": confidence, "evidence_ids": ids, "knowledge_points": [{"name": "召回率评估", "description": "用 Recall@K 检查检索覆盖", "difficulty": "medium", "confidence": confidence, "evidence_ids": ids}]}],
        })

    rows = [
        ("AH-GR-01", "两条已知独立证据且置信度充分", output(), True, []),
        ("AH-GR-02", "模型引用不存在的证据编号", output(evidence_ids=["JD-IFLY-001", "FAKE-999"]), False, ["unknown_citation"]),
        ("AH-GR-03", "模型输出置信度低于0.75", output(confidence=0.51), False, ["low_confidence_claim"]),
        ("AH-GR-04", "模型重复同一证据形成伪多来源", output(evidence_ids=["JD-IFLY-001", "JD-IFLY-001"]), False, ["insufficient_citations"]),
    ]
    results = []
    for case_id, scenario, candidate, expected, issues in rows:
        report = evaluate_l45_output(request, candidate)
        passed = report.passed == expected and set(issues).issubset(report.issue_codes)
        results.append(make_case(
            case_id, "能力图谱L4/L5补全", scenario,
            {"evidence_ids": candidate.tech_points[0].evidence_ids, "confidence": candidate.tech_points[0].confidence},
            "进入人工审核和持久化" if expected else "拒绝候选图谱内容并展示校验原因",
            {"accepted": report.passed, "issues": report.issue_codes}, passed,
            unsupported=not expected,
        ))
    return results


async def main():
    results = [
        *await jd_generation_cases(), *await jd_suggestion_cases(),
        *skill_extraction_cases(), *career_cases(), *match_cases(), *graph_cases(),
    ]
    passed_count = sum(item["test_passed"] for item in results)
    unsupported = [item for item in results if item["unsupported_claim"]]
    protected = [item for item in unsupported if item["test_passed"]]
    surfaces = sorted({item["ai_surface"] for item in results})
    by_surface = {}
    for surface in surfaces:
        rows = [item for item in results if item["ai_surface"] == surface]
        by_surface[surface] = {
            "cases": len(rows),
            "passed": sum(item["test_passed"] for item in rows),
            "observable_effects": sorted({item["expected_visible_effect"] for item in rows}),
        }
    artifact = {
        "benchmark": "competition AI-output anti-hallucination benchmark",
        "scope": "all six production surfaces that can display or persist AI-generated content",
        "control_chain": "model output -> system-owned field restoration / exact-source grounding / snapshot citation validation / confidence and multi-source gate -> display, hold, or reject",
        "metrics": {
            "ai_surface_count": len(surfaces), "cases": len(results),
            "passed": passed_count, "failed": len(results) - passed_count,
            "case_pass_rate": round(passed_count / len(results), 6),
            "unsupported_case_count": len(unsupported),
            "unsupported_claim_block_rate": round(len(protected) / len(unsupported), 6),
        },
        "surface_metrics": by_surface,
        "cases": results,
    }
    output_path = BACKEND_ROOT / "evaluation" / "hallucination_control_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": artifact["metrics"], "output": str(output_path)}, ensure_ascii=False))
    if passed_count != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
