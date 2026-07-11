"""与 FastAPI、数据库和 Celery 无关的 JD Generation Agent。"""

from __future__ import annotations

from jiebang_agents.base import StructuredLLMProvider
from jiebang_agents.jd_generation.prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from jiebang_agents.jd_generation.schemas import GenerateJDRequest, GeneratedJDDraft, LLMGeneratedJDDraft


class JDGenerationAgent:
    agent_type = "jd_generation"
    prompt_version = PROMPT_VERSION

    def __init__(self, llm: StructuredLLMProvider, *, timeout_seconds: int = 15) -> None:
        self.llm = llm
        self.timeout_seconds = timeout_seconds

    async def generate(self, request: GenerateJDRequest) -> GeneratedJDDraft:
        if not bool(getattr(self.llm, "enabled", True)):
            return self.template_draft(request, "未配置 DeepSeek，已生成可编辑模板草稿。")
        output = await self.llm.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(request),
            response_schema=LLMGeneratedJDDraft,
            timeout_seconds=self.timeout_seconds,
            metadata={"agent_type": self.agent_type, "prompt_version": self.prompt_version},
        )
        return self.merge_llm_output(output, request)

    @classmethod
    def merge_llm_output(cls, output: LLMGeneratedJDDraft, request: GenerateJDRequest) -> GeneratedJDDraft:
        template = cls.template_draft(request, "")
        responsibilities = cls.string_list(output.responsibilities) or template.responsibilities
        requirements = cls.string_list(output.requirements) or template.requirements
        skills = cls.string_list(output.skills) or template.skills
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
            standardized_title=output.standardized_title,
            level=request.level or "mid",
            department=request.department or "待确定部门",
            responsibilities=responsibilities[:8],
            requirements=requirements[:8],
            skills=skills[:20],
            bonus_skills=cls.string_list(output.bonus_skills)[:12],
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
        responsibilities = [
            f"负责{request.title}相关方案的设计、实施与持续优化。",
            "与产品、研发及相关业务团队协作，按计划交付工作成果。",
            "沉淀岗位相关文档、流程和可复用经验。",
        ]
        requirements = [
            f"具备与{request.title}相匹配的专业知识和实践能力。",
            "具备良好的沟通协作与问题分析能力。",
        ]
        if skills:
            requirements.insert(0, f"熟悉以下核心技能：{'、'.join(skills[:8])}。")
        jd_text = "\n".join([
            f"岗位名称：{request.title}",
            f"所属部门：{department}",
            "岗位职责：" + "；".join(responsibilities),
            "任职要求：" + "；".join(requirements),
        ])
        return GeneratedJDDraft(
            title=request.title,
            standardized_title=None,
            level=request.level or "mid",
            department=department,
            responsibilities=responsibilities,
            requirements=requirements,
            skills=skills[:20],
            bonus_skills=[],
            jd_text=jd_text,
            assumptions=["该草稿未包含薪资、福利、学历和工作年限，请由管理员补充。"],
            warnings=[warning] if warning else [],
            generation_mode="template",
        )
