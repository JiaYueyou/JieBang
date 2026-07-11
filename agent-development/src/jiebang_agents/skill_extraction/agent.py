from jiebang_agents.base import StructuredLLMProvider
from jiebang_agents.skill_extraction.prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from jiebang_agents.skill_extraction.schemas import LLMDiscoveredSkills


class SkillExtractionAgent:
    agent_type = "skill_extraction"
    prompt_version = PROMPT_VERSION

    def __init__(self, llm: StructuredLLMProvider, *, timeout_seconds: int = 15) -> None:
        self.llm = llm
        self.timeout_seconds = timeout_seconds

    async def enrich(self, *, text: str, known_skills: list[str]) -> LLMDiscoveredSkills:
        return await self.llm.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(text=text, known_skills=known_skills),
            response_schema=LLMDiscoveredSkills,
            timeout_seconds=self.timeout_seconds,
            metadata={"agent_type": self.agent_type, "prompt_version": self.prompt_version},
        )
