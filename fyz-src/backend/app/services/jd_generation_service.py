"""JD Generation 的任务编排、审计持久化和查询服务。"""

from __future__ import annotations

import time
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_runtime import JDGenerationAgent
from app.core.config import CELERY_TASK_ALWAYS_EAGER, DEEPSEEK_TIMEOUT_SECONDS
from app.core.exceptions import ResourceNotFoundError
from app.models import AgentRun, AsyncTask
from app.providers import DeepSeekProvider, LLMProvider
from app.repositories import SkillRepository, TaskRepository
from app.schemas.agent import AgentRunResponse, GenerateJDRequest, GeneratedJDDraft, JDGenerationTaskResponse
from app.services.task_service import TaskService


class JDGenerationService:
    """保留既有 Service 入口，兼容现有 API 与 Celery 任务。"""

    agent_type = JDGenerationAgent.agent_type
    prompt_version = JDGenerationAgent.prompt_version

    def __init__(self, db: AsyncSession, *, llm_provider: LLMProvider | None = None) -> None:
        self.db = db
        self.llm = llm_provider or DeepSeekProvider()
        self.agent = JDGenerationAgent(self.llm, timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS)
        self.agent_runs = SkillRepository(db)
        self.tasks = TaskRepository(db)

    async def create_task(self, request: GenerateJDRequest, *, user_id: int) -> JDGenerationTaskResponse:
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
            request_data={"agent_run_id": run_id, "payload": request.model_dump(mode="json")},
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
        return JDGenerationTaskResponse(task=TaskService.to_response(task), agent_run_id=run_id)

    async def generate(self, request: GenerateJDRequest, *, agent_run_id: str) -> GeneratedJDDraft:
        run = await self.get_run_model(agent_run_id)
        run.status = "running"
        started = time.perf_counter()
        try:
            draft = await self.agent.generate(request)
            run.status = "degraded" if draft.generation_mode == "template" else "succeeded"
            run.structured_output = draft.model_dump(mode="json")
            return draft
        except Exception as exc:
            draft = JDGenerationAgent.template_draft(request, "模型调用失败，已生成可编辑模板草稿。")
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
