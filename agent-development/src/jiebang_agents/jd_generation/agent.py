"""与 FastAPI、数据库和 Celery 无关的 JD Generation Agent。"""

from __future__ import annotations

from jiebang_agents.base import StructuredLLMProvider
from jiebang_agents.jd_generation.prompt import (
    INTERNAL_SUGGESTION_SYSTEM_PROMPT,
    INTERNAL_SYSTEM_PROMPT,
    PROMPT_VERSION,
    PUBLIC_SUGGESTION_SYSTEM_PROMPT,
    PUBLIC_SYSTEM_PROMPT,
    SUGGESTION_PROMPT_VERSION,
    build_suggestion_prompt,
    build_user_prompt,
)
from jiebang_agents.jd_generation.schemas import (
    GenerateJDRequest,
    GeneratedJDDraft,
    JDGenerationMode,
    JDGenerationTarget,
    JDInputSuggestion,
    JDInputSuggestionRequest,
    LLMGeneratedJDDraft,
    LLMJDInputSuggestion,
)


TITLE_SKILL_FALLBACKS: tuple[tuple[tuple[str, ...], list[str]], ...] = (
    (("java",), ["Java", "Spring Boot", "MySQL", "Redis", "微服务架构"]),
    (("python",), ["Python", "FastAPI", "MySQL", "Redis", "Linux"]),
    (("后端", "backend"), ["API 设计", "MySQL", "Redis", "Linux", "服务架构"]),
    (("前端", "frontend"), ["JavaScript", "TypeScript", "Vue", "HTML/CSS", "前端工程化"]),
    (("数据分析", "数据运营"), ["SQL", "Python", "数据清洗", "数据可视化", "统计分析"]),
    (("算法", "机器学习", "大模型"), ["Python", "机器学习", "深度学习", "模型评估", "数据处理"]),
)

DEFAULT_SKILL_SUGGESTIONS = ["岗位专业知识", "问题分析", "沟通协作", "项目交付", "持续学习"]
DEFAULT_PROFILE_SUGGESTIONS = [
    "具备与岗位相匹配的专业判断和实践能力",
    "能够独立分析问题并推动解决方案落地",
    "具备良好的跨团队沟通与协作能力",
    "能够持续学习并沉淀可复用经验",
]


class JDGenerationAgent:
    agent_type = "jd_generation"
    suggestion_task_type = "jd_input_suggestion"
    prompt_version = PROMPT_VERSION
    suggestion_prompt_version = SUGGESTION_PROMPT_VERSION

    def __init__(self, llm: StructuredLLMProvider, *, timeout_seconds: int = 15) -> None:
        self.llm = llm
        self.timeout_seconds = timeout_seconds

    async def generate(self, request: GenerateJDRequest) -> GeneratedJDDraft:
        if not bool(getattr(self.llm, "enabled", True)):
            return self.template_draft(request, "未配置 DeepSeek，已生成可编辑模板草稿。")
        output = await self.llm.generate_structured(
            system_prompt=(
                INTERNAL_SYSTEM_PROMPT
                if request.target == JDGenerationTarget.internal
                else PUBLIC_SYSTEM_PROMPT
            ),
            user_prompt=build_user_prompt(request),
            response_schema=LLMGeneratedJDDraft,
            timeout_seconds=self.timeout_seconds,
            metadata={
                "agent_type": self.agent_type,
                "prompt_version": self.prompt_version,
                "target": request.target.value,
            },
        )
        return self.merge_llm_output(output, request)

    async def suggest_input(self, request: JDInputSuggestionRequest) -> JDInputSuggestion:
        if not bool(getattr(self.llm, "enabled", True)):
            return self.template_suggestion(
                request,
                "未配置 DeepSeek，当前内容由岗位规则模板生成，请人工核对。",
            )
        output = await self.llm.generate_structured(
            system_prompt=(
                INTERNAL_SUGGESTION_SYSTEM_PROMPT
                if request.target == JDGenerationTarget.internal
                else PUBLIC_SUGGESTION_SYSTEM_PROMPT
            ),
            user_prompt=build_suggestion_prompt(request),
            response_schema=LLMJDInputSuggestion,
            timeout_seconds=self.timeout_seconds,
            metadata={
                "agent_type": self.suggestion_task_type,
                "prompt_version": self.suggestion_prompt_version,
                "target": request.target.value,
            },
        )
        suggestions = self.string_list(output.suggestions)
        if not suggestions:
            return self.template_suggestion(request, "AI 未返回有效建议，已使用岗位规则模板。")
        limit = 10 if request.mode == JDGenerationMode.requirements else 6
        return JDInputSuggestion(
            title=request.title,
            target=request.target,
            mode=request.mode,
            suggestions=suggestions[:limit],
            generation_mode="llm",
            warnings=self.string_list(output.warnings)[:8],
        )

    @classmethod
    def merge_llm_output(cls, output: LLMGeneratedJDDraft, request: GenerateJDRequest) -> GeneratedJDDraft:
        template = cls.template_draft(request, "")
        responsibilities = cls.string_list(output.responsibilities) or template.responsibilities
        requirements = cls.string_list(output.requirements) or template.requirements
        skills = cls.string_list(output.skills) or template.skills
        trainable_skills = (
            cls.string_list(output.trainable_skills) or template.trainable_skills
            if request.target == JDGenerationTarget.internal
            else []
        )
        trainable_keys = {item.casefold() for item in trainable_skills}
        if trainable_keys:
            skills = [item for item in skills if item.casefold() not in trainable_keys]
        assumptions = cls.string_list(output.assumptions) or template.assumptions
        jd_text = output.jd_text.strip() if isinstance(output.jd_text, str) else ""
        if not jd_text:
            jd_text = "\n".join([
                f"岗位名称：{request.title}",
                f"所属部门：{request.department or '待确定部门'}",
                "岗位职责：" + "；".join(responsibilities),
                "任职要求：" + "；".join(requirements),
            ])
        return GeneratedJDDraft(
            title=request.title,
            target=request.target,
            standardized_title=output.standardized_title,
            level=request.level or "mid",
            department=request.department or "待确定部门",
            responsibilities=responsibilities[:8],
            requirements=requirements[:8],
            skills=skills[:20],
            bonus_skills=cls.string_list(output.bonus_skills)[:12],
            trainable_skills=trainable_skills[:12],
            transfer_profile=(
                cls.string_list(output.transfer_profile)[:8]
                if request.target == JDGenerationTarget.internal
                else []
            ),
            manager_confirmations=(
                cls.string_list(output.manager_confirmations)[:8]
                if request.target == JDGenerationTarget.internal
                else []
            ),
            jd_text=jd_text,
            assumptions=assumptions[:8],
            warnings=cls.string_list(output.warnings)[:8],
            generation_mode="llm",
        )

    @staticmethod
    def string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(item.strip() for item in value if isinstance(item, str) and item.strip()))

    @staticmethod
    def template_draft(request: GenerateJDRequest, warning: str) -> GeneratedJDDraft:
        skills = [item.strip() for item in request.skills_input.replace("，", ",").split(",") if item.strip()]
        department = request.department or "待确定部门"
        internal = request.target == JDGenerationTarget.internal
        responsibilities = [
            f"承担{request.title}相关内部业务目标与交付责任。" if internal else f"负责{request.title}相关方案的设计、实施与持续优化。",
            "与接收部门及相关业务团队协作，完成内部岗位交接与目标落地。" if internal else "与产品、研发及相关业务团队协作，按计划交付工作成果。",
            "沉淀岗位相关文档、流程和可复用经验。",
        ]
        requirements = [
            f"具备转入{request.title}所需的专业基础和可迁移实践能力。" if internal else f"具备与{request.title}相匹配的专业知识和实践能力。",
            "具备良好的沟通协作与问题分析能力。",
        ]
        if skills:
            requirements.insert(0, f"熟悉以下核心技能：{'、'.join(skills[:8])}。")
        jd_text = "\n".join([
            "内部岗位需求说明" if internal else "公开招聘岗位 JD",
            f"岗位名称：{request.title}",
            f"{'接收部门' if internal else '所属部门'}：{department}",
            "岗位职责：" + "；".join(responsibilities),
            "任职要求：" + "；".join(requirements),
        ])
        return GeneratedJDDraft(
            title=request.title,
            target=request.target,
            standardized_title=None,
            level=request.level or "mid",
            department=department,
            responsibilities=responsibilities,
            requirements=requirements,
            skills=(skills[:4] if internal else skills[:20]),
            bonus_skills=[],
            trainable_skills=(skills[4:8] if internal else []),
            transfer_profile=(
                ["具备相近岗位或项目经验", "能够在培养期内完成关键技能补齐"]
                if internal else []
            ),
            manager_confirmations=(
                ["请确认内部开放范围、转岗资格和计划到岗时间"]
                if internal else []
            ),
            jd_text=jd_text,
            assumptions=[
                "该内部草稿未确认开放范围、审批条件和到岗时间，请由管理层补充。"
                if internal else
                "该草稿未包含薪资、福利、学历和工作年限，请由管理员补充。"
            ],
            warnings=[warning] if warning else [],
            generation_mode="template",
        )

    @staticmethod
    def template_suggestion(request: JDInputSuggestionRequest, warning: str) -> JDInputSuggestion:
        if request.mode == JDGenerationMode.profile:
            suggestions = DEFAULT_PROFILE_SUGGESTIONS
        else:
            normalized_title = request.title.casefold()
            suggestions = DEFAULT_SKILL_SUGGESTIONS
            for keywords, candidate_skills in TITLE_SKILL_FALLBACKS:
                if any(keyword.casefold() in normalized_title for keyword in keywords):
                    suggestions = candidate_skills
                    break
        return JDInputSuggestion(
            title=request.title,
            target=request.target,
            mode=request.mode,
            suggestions=suggestions,
            generation_mode="template",
            warnings=[warning] if warning else [],
        )
