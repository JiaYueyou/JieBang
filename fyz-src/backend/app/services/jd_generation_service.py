"""受约束、可审计的智能 JD 草稿生成服务。"""

from __future__ import annotations

import time
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import CELERY_TASK_ALWAYS_EAGER, DEEPSEEK_TIMEOUT_SECONDS
from app.core.exceptions import ResourceNotFoundError
from app.models import AgentRun, AsyncTask
from app.providers import DeepSeekProvider, LLMProvider
from app.repositories import SkillRepository, TaskRepository
from app.schemas.agent import (
    AgentRunResponse,
    GenerateJDRequest,
    GeneratedJDDraft,
    JDGenerationTaskResponse,
    LLMGeneratedJDDraft,
)
from app.schemas.skill import TaskStatusResponse
from app.services.task_service import TaskService


class JDGenerationService:
    agent_type = "jd_generation"
    prompt_version = "jd-generation-v2"

    def __init__(
        self,
        db: AsyncSession,
        *,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.db = db
        self.llm = llm_provider or DeepSeekProvider()
        self.agent_runs = SkillRepository(db)
        self.tasks = TaskRepository(db)

    async def create_task(
        self, request: GenerateJDRequest, *, user_id: int
    ) -> JDGenerationTaskResponse:
        run_id = str(uuid.uuid4())
        run = AgentRun(
            id=run_id,
            agent_type=self.agent_type,
            provider=self.llm.provider_name,
            model=self.llm.model_name,
            prompt_version=self.prompt_version,
            input_summary=self._input_summary(request),
            status="queued",
            retry_count=0,
            created_by=user_id,
        )
        task = AsyncTask(
            id=str(uuid.uuid4()),
            task_type=self.agent_type,
            status="queued",
            progress=0,
            request_data={
                "agent_run_id": run_id,
                "payload": request.model_dump(mode="json"),
            },
            created_by=user_id,
        )
        await self.agent_runs.add_agent_run(run)
        await self.tasks.create(task)
        await self.db.commit()

        from app.tasks.jd_generation import _process_jd_generation, process_jd_generation

        if CELERY_TASK_ALWAYS_EAGER:
            await _process_jd_generation(task.id)
        else:
            process_jd_generation.delay(task.id)
        await self.db.refresh(task)
        return JDGenerationTaskResponse(
            task=TaskService.to_response(task), agent_run_id=run_id
        )

    async def generate(
        self, request: GenerateJDRequest, *, agent_run_id: str
    ) -> GeneratedJDDraft:
        run = await self.get_run_model(agent_run_id)
        run.status = "running"
        started = time.perf_counter()
        try:
            if not bool(getattr(self.llm, "enabled", True)):
                draft = self._template_draft(request, "未配置 DeepSeek，已生成可编辑模板草稿。")
                run.status = "degraded"
            else:
                output = await self.llm.generate_structured(
                    system_prompt=(
                        "你是企业招聘 JD 起草助手。只根据用户明确提供的需求生成草稿；"
                        "不得编造薪资、福利、学历、工作年限或合规承诺。"
                        "岗位名称、职级、部门由系统控制，绝不能输出或覆盖它们。"
                        "只能返回一个 JSON 对象，禁止 Markdown、解释文字和额外字段。"
                    ),
                    user_prompt=self._prompt(request),
                    response_schema=LLMGeneratedJDDraft,
                    timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS,
                    metadata={"agent_run_id": agent_run_id},
                )
                draft = self._merge_llm_output(output, request)
                run.status = "succeeded"
            run.structured_output = draft.model_dump(mode="json")
            return draft
        except Exception as exc:
            draft = self._template_draft(request, "模型调用失败，已生成可编辑模板草稿。")
            run.status = "degraded"
            run.error_code = type(exc).__name__
            run.error_message = str(exc)[:2000]
            run.structured_output = draft.model_dump(mode="json")
            return draft
        finally:
            run.duration_ms = int((time.perf_counter() - started) * 1000)
            run.finished_at = datetime.utcnow()

    async def get_run(self, agent_run_id: str) -> AgentRunResponse:
        return self.to_response(await self.get_run_model(agent_run_id))

    async def get_run_model(self, agent_run_id: str) -> AgentRun:
        run = await self.db.get(AgentRun, agent_run_id)
        if not run:
            raise ResourceNotFoundError("Agent 运行记录不存在")
        return run

    @staticmethod
    def to_response(run: AgentRun) -> AgentRunResponse:
        return AgentRunResponse(
            id=run.id,
            agent_type=run.agent_type,
            provider=run.provider,
            model=run.model,
            prompt_version=run.prompt_version,
            input_summary=run.input_summary,
            structured_output=run.structured_output,
            status=run.status,
            duration_ms=run.duration_ms,
            retry_count=run.retry_count,
            error_code=run.error_code,
            error_message=run.error_message,
            created_at=run.created_at,
            finished_at=run.finished_at,
        )

    @staticmethod
    def _input_summary(request: GenerateJDRequest) -> str:
        return f"{request.mode.value}: {request.title}; {request.skills_input}"[:500]

    @staticmethod
    def _prompt(request: GenerateJDRequest) -> str:
        return (
            "请生成一份待人工审核的岗位 JD 草稿。\n"
            f"生成模式：{request.mode.value}\n"
            f"岗位名称：{request.title}\n"
            f"职级：{request.level or '未提供'}\n"
            f"部门：{request.department or '未提供'}\n"
            f"地点：{request.location or '未提供'}\n"
            f"公司：{request.company or '未提供'}\n"
            f"招聘人数：{request.headcount or '未提供'}\n"
            f"需求或人才画像：{request.skills_input or '未提供'}\n"
            "未知信息必须写入 assumptions 或 warnings，不能当作事实。\n"
            "严格返回如下 JSON 对象，字段名和类型必须一致：\n"
            "{\n"
            '  "standardized_title": "可选标准岗位名或 null",\n'
            '  "responsibilities": ["职责 1", "职责 2", "职责 3"],\n'
            '  "requirements": ["要求 1", "要求 2"],\n'
            '  "skills": ["核心技能"],\n'
            '  "bonus_skills": ["加分技能"],\n'
            '  "jd_text": "完整 JD 正文",\n'
            '  "assumptions": ["待确认事项"],\n'
            '  "warnings": ["风险或需人工复核事项"]\n'
            "}\n"
            "responsibilities、requirements、skills、bonus_skills、assumptions、warnings 必须是字符串数组，"
            "不能是对象、嵌套 JSON 或字符串。不要输出 position_name、title、level、department、generation_mode。"
        )

    @staticmethod
    def _merge_llm_output(
        output: LLMGeneratedJDDraft, request: GenerateJDRequest
    ) -> GeneratedJDDraft:
        template = JDGenerationService._template_draft(request, "")
        responsibilities = JDGenerationService._string_list(output.responsibilities) or template.responsibilities
        requirements = JDGenerationService._string_list(output.requirements) or template.requirements
        skills = JDGenerationService._string_list(output.skills) or template.skills
        bonus_skills = JDGenerationService._string_list(output.bonus_skills)
        assumptions = JDGenerationService._string_list(output.assumptions) or template.assumptions
        warnings = JDGenerationService._string_list(output.warnings)
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
            bonus_skills=bonus_skills[:12],
            jd_text=jd_text,
            assumptions=assumptions[:8],
            warnings=warnings[:8],
            generation_mode="llm",
        )

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(
            item.strip() for item in value if isinstance(item, str) and item.strip()
        ))

    @staticmethod
    def _template_draft(request: GenerateJDRequest, warning: str) -> GeneratedJDDraft:
        skills = [item.strip() for item in request.skills_input.replace("，", ",").split(",") if item.strip()]
        title = request.title
        level = request.level or "mid"
        department = request.department or "待确定部门"
        responsibilities = [
            f"负责{title}相关方案的设计、实施与持续优化。",
            "与产品、研发及相关业务团队协作，按计划交付工作成果。",
            "沉淀岗位相关文档、流程和可复用经验。",
        ]
        requirements = [
            f"具备与{title}相匹配的专业知识和实践能力。",
            "具备良好的沟通协作与问题分析能力。",
        ]
        if skills:
            requirements.insert(0, f"熟悉以下核心技能：{'、'.join(skills[:8])}。")
        jd_text = "\n".join([
            f"岗位名称：{title}",
            f"所属部门：{department}",
            "岗位职责：" + "；".join(responsibilities),
            "任职要求：" + "；".join(requirements),
        ])
        return GeneratedJDDraft(
            title=title,
            standardized_title=None,
            level=level,
            department=department,
            responsibilities=responsibilities,
            requirements=requirements,
            skills=skills[:20],
            bonus_skills=[],
            jd_text=jd_text,
            assumptions=["该草稿未包含薪资、福利、学历和工作年限，请由管理员补充。"],
            warnings=[warning],
            generation_mode="template",
        )
