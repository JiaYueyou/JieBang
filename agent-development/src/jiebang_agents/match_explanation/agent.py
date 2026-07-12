from jiebang_agents.base import StructuredLLMProvider

from .prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from .schemas import ExplanationItem, LLMMatchExplanation, MatchExplanationOutput, MatchExplanationRequest


class MatchExplanationAgent:
    agent_type = "match_explanation"
    prompt_version = PROMPT_VERSION

    def __init__(self, llm: StructuredLLMProvider, *, timeout_seconds: int = 15) -> None:
        self.llm = llm
        self.timeout_seconds = timeout_seconds

    async def generate(self, request: MatchExplanationRequest) -> MatchExplanationOutput:
        if not bool(getattr(self.llm, "enabled", True)):
            return self.template_output(request)
        narrative = await self.llm.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(request),
            response_schema=LLMMatchExplanation,
            timeout_seconds=self.timeout_seconds,
            metadata={"agent_type": self.agent_type, "prompt_version": self.prompt_version},
        )
        allowed = {item.evidence_id for item in request.evidence}
        strengths = self._sanitize(narrative.strengths, allowed)
        gaps = self._sanitize(narrative.gaps, allowed)
        return MatchExplanationOutput(
            **request.model_dump(exclude={"evidence"}), summary=narrative.summary,
            strengths=strengths, gaps=gaps, risks=narrative.risks,
            interview_suggestions=narrative.interview_suggestions, generation_mode="llm",
            warnings=[] if strengths or gaps else ["模型未返回可验证的证据引用，请人工复核。"],
        )

    @classmethod
    def template_output(cls, request: MatchExplanationRequest) -> MatchExplanationOutput:
        by_skill: dict[str, list[int]] = {}
        for item in request.evidence:
            by_skill.setdefault(item.skill_name.casefold(), []).append(item.evidence_id)
        strengths = [ExplanationItem(title=s, explanation=f"简历证据与岗位技能 {s} 一致。", evidence_ids=by_skill.get(s.casefold(), [])) for s in request.matched_skills]
        gaps = [ExplanationItem(title=s, explanation=f"岗位要求包含 {s}，当前简历未发现对应证据。", evidence_ids=by_skill.get(s.casefold(), [])) for s in request.missing_skills]
        return MatchExplanationOutput(
            **request.model_dump(exclude={"evidence"}),
            summary=f"当前对 {request.job_title} 的技能覆盖匹配分为 {request.score} 分。",
            strengths=strengths, gaps=gaps,
            risks=["规则匹配仅反映技能覆盖，不代表最终录用结论。"],
            interview_suggestions=[f"围绕 {s} 准备可验证的项目案例。" for s in request.matched_skills[:3]],
            generation_mode="template", warnings=["模型不可用，当前为确定性模板解释。"],
        )

    @staticmethod
    def _sanitize(items: list[ExplanationItem], allowed: set[int]) -> list[ExplanationItem]:
        return [item.model_copy(update={"evidence_ids": [x for x in item.evidence_ids if x in allowed]}) for item in items]
