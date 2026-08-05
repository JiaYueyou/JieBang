from jiebang_agents.graph_enrichment import (
    GraphEnrichmentOutput,
    SkillGraphCompletionAgent,
    SkillGraphCompletionInput,
    TechPointOutput,
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
