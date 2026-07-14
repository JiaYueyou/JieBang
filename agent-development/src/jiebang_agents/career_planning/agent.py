import re
from difflib import SequenceMatcher

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
        used_projects: set[str] = set()
        for rank, candidate in enumerate(candidates, 1):
            narrative = narratives.get(candidate.job_id)
            learning_plan = self._validated_learning_plan(
                candidate=candidate,
                proposed=narrative.learning_plan if narrative else [],
                time_budget_weeks=time_budget_weeks,
            )
            project = narrative.suggested_project.strip() if narrative else ""
            project_key = self._normalize_skill(project)
            if not project or project_key in used_projects:
                project = self._fallback_project(candidate)
                project_key = self._normalize_skill(project)
            used_projects.add(project_key)
            recommendations.append(CareerRecommendation(
                rank=rank,
                **candidate.model_dump(),
                learning_plan=learning_plan,
                suggested_project=project,
                total_time=(
                    narrative.total_time
                    if narrative and narrative.total_time and len(learning_plan) == len(narrative.learning_plan)
                    else self._total_time([step.skill for step in learning_plan], time_budget_weeks)
                ),
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
            suggested_project=cls._fallback_project(candidate),
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

    @classmethod
    def _validated_learning_plan(
        cls,
        *,
        candidate: CareerPlanCandidate,
        proposed: list[LearningStep],
        time_budget_weeks: int,
    ) -> list[LearningStep]:
        """只接受能映射到该岗位真实技能缺口的模型步骤。"""
        valid_gaps = [
            gap for gap in candidate.gaps
            if not any(cls._skills_match(gap, existing) for existing in candidate.existing)
        ]
        selected: list[LearningStep] = []
        used_gaps: set[str] = set()
        for step in proposed:
            matched = next((
                gap for gap in valid_gaps
                if gap not in used_gaps and cls._skills_match(step.skill, gap)
            ), None)
            if matched is None:
                continue
            used_gaps.add(matched)
            selected.append(step.model_copy(update={"skill": matched}))
        remaining = [gap for gap in valid_gaps if gap not in used_gaps]
        selected.extend(cls._fallback_steps(remaining, time_budget_weeks))
        return selected[:12]

    @classmethod
    def _skills_match(cls, left: str, right: str) -> bool:
        left_key, right_key = cls._normalize_skill(left), cls._normalize_skill(right)
        if not left_key or not right_key:
            return False
        if left_key == right_key:
            return True
        if min(len(left_key), len(right_key)) >= 3 and (
            left_key in right_key or right_key in left_key
        ):
            shorter = min((left_key, right_key), key=len)
            if shorter not in {"大模型"}:
                return True
        if min(len(left_key), len(right_key)) >= 4 and SequenceMatcher(
            None, left_key, right_key
        ).ratio() >= 0.66:
            return True
        return len(cls._technical_topics(left_key) & cls._technical_topics(right_key)) >= 2

    @staticmethod
    def _technical_topics(value: str) -> set[str]:
        topics = (
            "分布式", "训练", "部署", "微调", "向量数据库", "数据分析",
            "自然语言处理", "计算机视觉", "claudecode", "transformer", "rag",
        )
        return {topic for topic in topics if topic in value}

    @staticmethod
    def _normalize_skill(value: str) -> str:
        normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.casefold())
        aliases = {"nlp": "自然语言处理", "cv": "计算机视觉", "llm": "大模型"}
        normalized = aliases.get(normalized, normalized)
        for marker in (
            "有", "熟悉", "掌握", "了解", "具备", "使用经验", "相关经验", "经验",
            "基础", "高级应用", "深入", "实践", "等", "或", "与", "和", "架构",
        ):
            normalized = normalized.replace(marker, "")
        return normalized

    @staticmethod
    def _fallback_project(candidate: CareerPlanCandidate) -> str:
        focus = "、".join(candidate.gaps[:3]) or "岗位核心职责"
        return f"完成一个面向{candidate.job}、覆盖{focus}的可验收实战项目"

    @staticmethod
    def _total_time(gaps: list[str], time_budget_weeks: int) -> str:
        return f"{min(time_budget_weeks, max(1, len(gaps) * 2))} 周"
