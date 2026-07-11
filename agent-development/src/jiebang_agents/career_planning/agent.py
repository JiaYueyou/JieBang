from jiebang_agents.base import StructuredLLMProvider
from jiebang_agents.career_planning.prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from jiebang_agents.career_planning.schemas import (
    CareerAnalysisOutput,
    CareerPlanCandidate,
    CareerRecommendation,
    LLMCareerAnalysis,
    LearningStep,
    ResumeProfile,
)


class CareerPlanningAgent:
    agent_type = "career_planning"
    prompt_version = PROMPT_VERSION

    def __init__(self, llm: StructuredLLMProvider, *, timeout_seconds: int = 15) -> None:
        self.llm = llm
        self.timeout_seconds = timeout_seconds

    async def generate(
        self,
        *,
        resume_text: str,
        skills: list[str],
        enterprise_tech: str,
        candidates: list[CareerPlanCandidate],
        time_budget_weeks: int,
    ) -> CareerAnalysisOutput:
        if not bool(getattr(self.llm, "enabled", True)):
            return self.template_output(skills, candidates, time_budget_weeks)
        output = await self.llm.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(
                resume_text=resume_text,
                skills=skills,
                enterprise_tech=enterprise_tech,
                candidates=candidates,
                time_budget_weeks=time_budget_weeks,
            ),
            response_schema=LLMCareerAnalysis,
            timeout_seconds=self.timeout_seconds,
            metadata={"agent_type": self.agent_type, "prompt_version": self.prompt_version},
        )
        narratives = {item.job_id: item for item in output.recommendations}
        recommendations = []
        for rank, candidate in enumerate(candidates, 1):
            narrative = narratives.get(candidate.job_id)
            fallback = self._fallback_steps(candidate.gaps, time_budget_weeks)
            recommendations.append(CareerRecommendation(
                rank=rank,
                **candidate.model_dump(),
                learning_plan=narrative.learning_plan if narrative and narrative.learning_plan else fallback,
                suggested_project=narrative.suggested_project if narrative else f"完成一个面向{candidate.job}的内部实践项目",
                total_time=narrative.total_time if narrative else self._total_time(candidate.gaps, time_budget_weeks),
                explanation=narrative.explanation if narrative else "根据已具备技能与目标岗位差距生成。",
            ))
        profile = output.resume_profile.model_copy(update={"skills": skills})
        return CareerAnalysisOutput(resume_profile=profile, recommendations=recommendations, warnings=output.warnings)

    @classmethod
    def template_output(cls, skills, candidates, time_budget_weeks) -> CareerAnalysisOutput:
        rows = [CareerRecommendation(
            rank=rank,
            **candidate.model_dump(),
            learning_plan=cls._fallback_steps(candidate.gaps, time_budget_weeks),
            suggested_project=f"完成一个面向{candidate.job}的内部实践项目",
            total_time=cls._total_time(candidate.gaps, time_budget_weeks),
            explanation="模型不可用，已按确定性技能差距生成模板计划。",
        ) for rank, candidate in enumerate(candidates, 1)]
        return CareerAnalysisOutput(
            resume_profile=ResumeProfile(skills=skills, assumptions=["当前岗位、年限和教育信息需人工确认。"]),
            recommendations=rows,
            warnings=["模型不可用，当前为模板学习路径。"],
        )

    @staticmethod
    def _fallback_steps(gaps: list[str], time_budget_weeks: int) -> list[LearningStep]:
        if not gaps:
            return []
        weeks = max(1, min(4, time_budget_weeks // max(1, len(gaps))))
        return [LearningStep(skill=skill, time=f"{weeks} 周", difficulty="medium", resources=["官方文档", "内部实践任务"]) for skill in gaps[:12]]

    @staticmethod
    def _total_time(gaps: list[str], time_budget_weeks: int) -> str:
        return f"{min(time_budget_weeks, max(1, len(gaps) * 2))} 周"
