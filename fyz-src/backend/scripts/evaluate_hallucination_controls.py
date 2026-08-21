"""Create an observable, deterministic anti-hallucination benchmark artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AGENT_SRC = ROOT / "agent-development" / "src"
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_SRC))
sys.path.insert(0, str(BACKEND_ROOT))

from jiebang_agents.graph_enrichment.acceptance import evaluate_l45_output
from jiebang_agents.graph_enrichment.schemas import (
    GraphEnrichmentOutput,
    SkillGraphCompletionInput,
)
from app.services.agent_grounding_service import semantic_grounding_score


REQUEST = SkillGraphCompletionInput.model_validate(
    {
        "job_directions": ["大模型应用工程师"],
        "skill_area": "检索增强生成",
        "tech_stack": "Python / FastAPI / 向量数据库",
        "evidence": [
            {
                "evidence_id": "JD-IFLY-001",
                "source": "科大讯飞招聘",
                "text": "岗位要求掌握 Python、向量数据库和 RAG 评估。",
            },
            {
                "evidence_id": "JD-ZL-001",
                "source": "智联招聘",
                "text": "负责 FastAPI 服务和检索增强生成系统开发。",
            },
        ],
    }
)


def output(*, confidence: float = 0.92, evidence_ids: list[str] | None = None):
    ids = evidence_ids or ["JD-IFLY-001", "JD-ZL-001"]
    return GraphEnrichmentOutput.model_validate(
        {
            "skill_name": "RAG 工程",
            "job_directions": ["大模型应用工程师"],
            "skill_area": "检索增强生成",
            "tech_points": [
                {
                    "name": "向量检索",
                    "category": "component",
                    "detail": "根据两条招聘证据形成的技术点",
                    "confidence": confidence,
                    "evidence_ids": ids,
                    "knowledge_points": [
                        {
                            "name": "召回率评估",
                            "description": "用 Recall@K 检查检索覆盖",
                            "difficulty": "medium",
                            "confidence": confidence,
                            "evidence_ids": ids,
                        }
                    ],
                }
            ],
        }
    )


def main() -> None:
    structural_cases = [
        {
            "id": "AH-01",
            "scenario": "有两条已知独立证据且置信度充分",
            "expected_visible_effect": "内容通过，可进入人工审核/持久化阶段",
            "candidate": output(),
            "expected_pass": True,
            "expected_issues": [],
        },
        {
            "id": "AH-02",
            "scenario": "模型引用不存在的证据编号",
            "expected_visible_effect": "内容被拒绝，界面可显示 unknown_citation",
            "candidate": output(evidence_ids=["JD-IFLY-001", "FAKE-999"]),
            "expected_pass": False,
            "expected_issues": ["unknown_citation"],
        },
        {
            "id": "AH-03",
            "scenario": "模型输出置信度低于 0.75",
            "expected_visible_effect": "内容被拒绝，界面可显示 low_confidence_claim",
            "candidate": output(confidence=0.51),
            "expected_pass": False,
            "expected_issues": ["low_confidence_claim"],
        },
        {
            "id": "AH-04",
            "scenario": "模型重复同一证据，形式为两项但实际仅一条引用",
            "expected_visible_effect": "内容被拒绝，界面可显示 insufficient_citations",
            "candidate": output(evidence_ids=["JD-IFLY-001", "JD-IFLY-001"]),
            "expected_pass": False,
            "expected_issues": ["insufficient_citations"],
        },
    ]

    results: list[dict] = []
    for case in structural_cases:
        report = evaluate_l45_output(REQUEST, case.pop("candidate"))
        expected = set(case["expected_issues"])
        observed = set(report.issue_codes)
        passed = report.passed == case["expected_pass"] and expected <= observed
        results.append(
            {
                **case,
                "actual_pass": report.passed,
                "actual_issues": report.issue_codes,
                "test_passed": passed,
            }
        )

    semantic_cases = [
        {
            "id": "AH-05",
            "scenario": "生成内容与引用证据主题一致",
            "claim": "岗位需要使用 Python 构建 RAG 检索服务",
            "anchor": "Python",
            "evidence": "岗位要求掌握 Python、向量数据库和 RAG 评估。",
            "threshold": 0.12,
            "expected_accept": True,
            "expected_visible_effect": "语义证据闸门允许该主张",
        },
        {
            "id": "AH-06",
            "scenario": "生成内容声称量子芯片能力，但证据只讨论前端",
            "claim": "岗位必须精通量子芯片流片与低温测量",
            "anchor": "量子芯片",
            "evidence": "岗位负责 Vue 页面开发、交互设计和前端性能优化。",
            "threshold": 0.12,
            "expected_accept": False,
            "expected_visible_effect": "语义证据闸门拒绝该主张并标记 semantic_mismatch",
        },
    ]
    for case in semantic_cases:
        score = semantic_grounding_score(case["anchor"], case["claim"], case["evidence"])
        accepted = score >= case["threshold"]
        results.append(
            {
                **case,
                "grounding_score": round(score, 6),
                "actual_accept": accepted,
                "actual_issue": None if accepted else "semantic_mismatch",
                "test_passed": accepted == case["expected_accept"],
            }
        )

    passed_count = sum(item["test_passed"] for item in results)
    artifact = {
        "benchmark": "competition anti-hallucination observable cases",
        "policy": {
            "minimum_confidence": 0.75,
            "minimum_distinct_citations": 2,
            "semantic_threshold": 0.12,
            "persistence_rule": "only accepted claims may be persisted",
        },
        "metrics": {
            "cases": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
            "case_pass_rate": round(passed_count / len(results), 6),
            "unsupported_claim_block_rate": round(
                sum(
                    item["test_passed"]
                    for item in results
                    if item["id"] != "AH-01" and item["id"] != "AH-05"
                )
                / 4,
                6,
            ),
        },
        "cases": results,
        "limitations": [
            "该基准验证确定性证据闸门，不代表对任意自然语言事实进行开放域真伪判定。",
            "通过闸门的内容仍保留来源展示和人工审核入口。",
        ],
    }
    output_path = BACKEND_ROOT / "evaluation" / "hallucination_control_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"metrics": artifact["metrics"], "output": str(output_path)}, ensure_ascii=False))
    if passed_count != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
