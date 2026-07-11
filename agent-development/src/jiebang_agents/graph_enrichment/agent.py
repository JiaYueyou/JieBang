from jiebang_agents.base import StructuredLLMProvider
from jiebang_agents.graph_enrichment.prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from jiebang_agents.graph_enrichment.schemas import GraphEnrichmentOutput, SkillGraphCompletionInput


class SkillGraphCompletionAgent:
    agent_type = "skill_graph_completion"
    prompt_version = PROMPT_VERSION

    def __init__(self, llm: StructuredLLMProvider, *, timeout_seconds: int = 15) -> None:
        self.llm = llm
        self.timeout_seconds = timeout_seconds

    async def complete(self, request: SkillGraphCompletionInput) -> GraphEnrichmentOutput:
        output = await self.llm.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(request.model_dump(mode="json")),
            response_schema=GraphEnrichmentOutput,
            timeout_seconds=self.timeout_seconds,
            metadata={"agent_type": self.agent_type, "prompt_version": self.prompt_version},
        )
        return output.model_copy(
            update={
                "skill_name": request.tech_stack,
                "job_directions": request.job_directions,
                "skill_area": request.skill_area,
            }
        )

    async def enrich(
        self,
        *,
        skill_name: str,
        evidence: list[dict],
        skill_area: str = "未分类",
        job_directions: list[str] | None = None,
    ) -> GraphEnrichmentOutput:
        """兼容旧调用入口。"""

        return await self.complete(
            SkillGraphCompletionInput(
                job_directions=job_directions or [],
                skill_area=skill_area,
                tech_stack=skill_name,
                evidence=evidence,
            )
        )


GraphEnrichmentAgent = SkillGraphCompletionAgent
