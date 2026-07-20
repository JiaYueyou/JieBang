from jiebang_agents.base import StructuredLLMProvider
from jiebang_agents.graph_enrichment.prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from jiebang_agents.graph_enrichment.schemas import (
    GraphEnrichmentOutput,
    KnowledgePointOutput,
    SkillGraphCompletionInput,
    TechPointOutput,
)


def _truncate(value: str | None, max_length: int) -> str:
    value = (value or "").strip()
    return value[:max_length] if value else ""


def _normalize_knowledge(item: KnowledgePointOutput) -> KnowledgePointOutput:
    return item.model_copy(
        update={
            "name": _truncate(item.name, 100),
            "description": _truncate(item.description, 500),
            "prerequisites": [_truncate(p, 100) for p in (item.prerequisites or []) if _truncate(p, 100)],
        }
    )


def _normalize_tech_point(point: TechPointOutput) -> TechPointOutput:
    return point.model_copy(
        update={
            "name": _truncate(point.name, 100),
            "detail": _truncate(point.detail, 500),
            "knowledge_points": [_normalize_knowledge(k) for k in (point.knowledge_points or [])],
        }
    )


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
        normalized = output.model_copy(
            update={
                "skill_name": request.tech_stack,
                "job_directions": request.job_directions,
                "skill_area": request.skill_area,
                "tech_points": [_normalize_tech_point(p) for p in (output.tech_points or [])],
            }
        )
        return normalized

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
