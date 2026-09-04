from jiebang_agents.graph_enrichment import (
    GraphEnrichmentOutput,
    KnowledgePointOutput,
    SkillGraphCompletionAgent,
    SkillGraphCompletionInput,
    TechPointOutput,
    evaluate_l45_output,
    nearest_rank_percentile,
)


class CapturingProvider:
    provider_name = "fake"
    model_name = "fake-structured"
    enabled = True

    def __init__(self):
        self.call = None

    async def generate_structured(self, **kwargs):
        self.call = kwargs
        return GraphEnrichmentOutput(
            skill_name="FastAPI",
            tech_points=[],
        )


async def test_completion_prompt_contains_l1_to_l3_context():
    provider = CapturingProvider()
    agent = SkillGraphCompletionAgent(provider)
    request = SkillGraphCompletionInput(
        job_directions=["Python 后端开发工程师"],
        skill_area="Framework",
        tech_stack="FastAPI",
        evidence=[
            {
                "evidence_id": "evidence-a",
                "source": "平台A",
                "text": "熟悉 FastAPI 路由与依赖注入",
            },
            {
                "evidence_id": "evidence-b",
                "source": "平台B",
                "text": "掌握 FastAPI 异步接口开发",
            },
        ],
    )

    await agent.complete(request)

    prompt = provider.call["user_prompt"]
    assert "Python 后端开发工程师" in prompt
    assert "Framework" in prompt
    assert "FastAPI" in prompt
    assert "evidence-a" in prompt
    assert "evidence-b" in prompt
    assert "core_stack" in prompt
    assert "common_solutions" in prompt
    assert "常用组件或方案" in provider.call["system_prompt"]
    assert provider.call["metadata"]["agent_type"] == "skill_graph_completion"


async def test_completion_filters_broad_l4_topics():
    provider = CapturingProvider()
    async def generate(**_kwargs):
        return _completed_output()
    provider.generate_structured = generate
    agent = SkillGraphCompletionAgent(provider)
    result = await agent.complete(SkillGraphCompletionInput(
        job_directions=["Python 后端工程师"],
        skill_area="Programming Language",
        tech_stack="Python",
        evidence=[
            {"evidence_id": "evidence-a", "source": "平台A", "text": "使用 Flask 开发接口"},
            {"evidence_id": "evidence-b", "source": "平台B", "text": "基于 Flask 构建 Web 服务"},
        ],
    ))

    assert [point.name for point in result.tech_points] == ["Flask"]


def _completed_output():
    common = dict(detail="证据说明", confidence=0.9, evidence_ids=["evidence-a", "evidence-b"])
    return GraphEnrichmentOutput(
        skill_name="Python",
        tech_points=[
            TechPointOutput(name="Python 开发基础与工程规范", **common),
            TechPointOutput(name="Flask", category="framework", **common),
        ],
    )


def test_acceptance_gate_rejects_unknown_or_weak_citations():
    request = SkillGraphCompletionInput(
        job_directions=["Python 后端工程师"],
        skill_area="Programming Language",
        tech_stack="Python",
        evidence=[
            {"evidence_id": "e1", "source": "A", "text": "使用 Flask 开发接口"},
            {"evidence_id": "e2", "source": "B", "text": "基于 Flask 构建服务"},
        ],
    )
    output = GraphEnrichmentOutput(
        skill_name="Python",
        tech_points=[TechPointOutput(
            name="Flask", category="framework", detail="Web 框架",
            confidence=.7, evidence_ids=["e1", "unknown"],
            knowledge_points=[KnowledgePointOutput(
                name="请求上下文", description="请求隔离", difficulty="medium",
                confidence=.9, evidence_ids=["e1", "e2"],
            )],
        )],
    )

    report = evaluate_l45_output(request, output)

    assert report.passed is False
    assert report.issue_codes == ["low_confidence_claim", "unknown_citation"]


def test_acceptance_gate_passes_grounded_l4_l5_output():
    request = SkillGraphCompletionInput(
        job_directions=["Python 后端工程师"],
        skill_area="Programming Language",
        tech_stack="Python",
        evidence=[
            {"evidence_id": "e1", "source": "A", "text": "使用 Flask 开发接口"},
            {"evidence_id": "e2", "source": "B", "text": "基于 Flask 构建服务"},
        ],
    )
    output = GraphEnrichmentOutput(
        skill_name="Python",
        tech_points=[TechPointOutput(
            name="Flask", category="framework", detail="Web 框架",
            confidence=.9, evidence_ids=["e1", "e2"],
            knowledge_points=[KnowledgePointOutput(
                name="请求上下文", description="请求隔离", difficulty="medium",
                confidence=.85, evidence_ids=["e1", "e2"],
            )],
        )],
    )

    assert evaluate_l45_output(request, output).passed is True


def test_nearest_rank_percentile_uses_ceiling_rank():
    assert nearest_rank_percentile([10, 20], .95) == 20
    assert nearest_rank_percentile(list(range(1, 21)), .95) == 19
    assert nearest_rank_percentile([30, 10, 20], .5) == 20
