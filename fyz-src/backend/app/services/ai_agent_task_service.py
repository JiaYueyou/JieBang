"""Async task orchestration for long-running Career and Match agents."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_runtime import CareerPlanningAgent, MatchExplanationAgent
from app.core.config import CELERY_TASK_ALWAYS_EAGER
from app.core.exceptions import InvalidParameterError, ResourceNotFoundError
from app.models import AgentRun, AsyncTask, MatchRecord, Resume
from app.providers import DeepSeekProvider
from app.schemas.agent import AgentTaskResponse
from app.schemas.career import CareerAnalysisRequest
from app.services.task_service import TaskService


class AIAgentTaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = DeepSeekProvider()

    async def create_career_task(
        self, request: CareerAnalysisRequest, *, user_id: int
    ) -> AgentTaskResponse:
        if not " ".join([request.skill_text, request.resume_text]).strip():
            raise InvalidParameterError("员工技能或简历文本至少填写一项")
        return await self._create(
            task_type=CareerPlanningAgent.agent_type,
            prompt_version=CareerPlanningAgent.prompt_version,
            payload=request.model_dump(mode="json"),
            input_summary="career analysis request",
            user_id=user_id,
        )

    async def create_match_task(
        self, match_id: int, *, user_id: int
    ) -> AgentTaskResponse:
        exists = await self.db.scalar(
            select(MatchRecord.id)
            .join(Resume)
            .where(
                MatchRecord.id == match_id,
                Resume.created_by == user_id,
                Resume.deleted_at.is_(None),
            )
        )
        if exists is None:
            raise ResourceNotFoundError("匹配记录不存在")
        return await self._create(
            task_type=MatchExplanationAgent.agent_type,
            prompt_version=MatchExplanationAgent.prompt_version,
            payload={"match_id": match_id},
            input_summary=f"match_id={match_id}",
            user_id=user_id,
        )

    async def _create(
        self,
        *,
        task_type: str,
        prompt_version: str,
        payload: dict,
        input_summary: str,
        user_id: int,
    ) -> AgentTaskResponse:
        run = AgentRun(
            id=str(uuid.uuid4()), agent_type=task_type,
            provider=self.llm.provider_name, model=self.llm.model_name,
            prompt_version=prompt_version, input_summary=input_summary,
            status="queued", retry_count=0, created_by=user_id,
        )
        task = AsyncTask(
            id=str(uuid.uuid4()), task_type=task_type, status="queued", progress=0,
            request_data={"agent_run_id": run.id, "payload": payload},
            created_by=user_id,
        )
        self.db.add_all([run, task])
        await self.db.commit()

        from app.tasks.ai_agents import _process_ai_agent, process_ai_agent

        if CELERY_TASK_ALWAYS_EAGER:
            await _process_ai_agent(task.id)
        else:
            process_ai_agent.delay(task.id)
        await self.db.refresh(task)
        return AgentTaskResponse(task=TaskService.to_response(task), agent_run_id=run.id)
