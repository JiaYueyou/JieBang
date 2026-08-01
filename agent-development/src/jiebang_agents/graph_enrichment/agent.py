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
            "core_stack": [_truncate(p, 100) for p in (item.core_stack or []) if _truncate(p, 100)][:8],
            "common_solutions": [
                solution.model_copy(update={
                    "name": _truncate(solution.name, 100),
                    "purpose": _truncate(solution.purpose, 300),
                })
                for solution in (item.common_solutions or [])
                if _truncate(solution.name, 100) and _truncate(solution.purpose, 300)
            ][:8],
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


_BROAD_TECH_POINT_TERMS = (
    "开发基础", "工程规范", "性能优化", "开发与应用", "框架与微服务",
    "后端 web 开发", "后端web开发", "算法与框架", "基础与应用",
)


def _is_concrete_tech_point(point: TechPointOutput, tech_stack: str) -> bool:
    """拒绝把能力主题或应用场景误写成 L4；L4 必须是具名工具实体。"""
    name = point.name.strip()
    lowered = name.casefold()
    if not name or lowered == tech_stack.strip().casefold():
        return False
    if any(term in lowered for term in _BROAD_TECH_POINT_TERMS):
        return False
    return len(name) <= 60


class SkillGraphCompletionAgent:
    agent_type = "skill_graph_completion"
    prompt_version = PROMPT_VERSION

    def __init__(
        self,
        llm: StructuredLLMProvider,
        *,
        timeout_seconds: int = 15,
        max_attempts: int = 2,
    ) -> None:
        self.llm = llm
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max(1, max_attempts)

    async def complete(self, request: SkillGraphCompletionInput) -> GraphEnrichmentOutput:
        output = await self.llm.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(request.model_dump(mode="json")),
            response_schema=GraphEnrichmentOutput,
            timeout_seconds=self.timeout_seconds,
            metadata={
                "agent_type": self.agent_type,
                "prompt_version": self.prompt_version,
                "max_attempts": self.max_attempts,
            },
        )
        normalized = output.model_copy(
            update={
                "skill_name": request.tech_stack,
                "job_directions": request.job_directions,
                "skill_area": request.skill_area,
                "tech_points": [
                    _normalize_tech_point(p)
                    for p in (output.tech_points or [])
                    if _is_concrete_tech_point(p, request.tech_stack)
                ],
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
