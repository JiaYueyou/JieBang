from jiebang_agents.graph_enrichment import (
    GraphEnrichmentOutput,
    SkillGraphCompletionAgent,
    SkillGraphCompletionInput,
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
            {"source_id": 1, "source": "平台A", "text": "熟悉 FastAPI 路由与依赖注入"},
            {"source_id": 2, "source": "平台B", "text": "掌握 FastAPI 异步接口开发"},
        ],
    )

    await agent.complete(request)

    prompt = provider.call["user_prompt"]
    assert "Python 后端开发工程师" in prompt
    assert "Framework" in prompt
    assert "FastAPI" in prompt
    assert provider.call["metadata"]["agent_type"] == "skill_graph_completion"
