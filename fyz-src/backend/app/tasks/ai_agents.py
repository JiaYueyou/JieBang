"""Celery execution for Career Planning and Match Explanation."""

import asyncio
from datetime import datetime

from app.core.agent_runtime import CareerPlanningAgent, MatchExplanationAgent
from app.core.celery_app import celery_app
from app.core.database import async_session
from app.models import AgentRun, AsyncTask
from app.schemas.career import CareerAnalysisRequest
from app.services.career_service import CareerService
from app.services.matching_service import MatchingService


async def _process_ai_agent(task_id: str) -> dict:
    async with async_session() as db:
        task = await db.get(AsyncTask, task_id)
        if task is None:
            raise RuntimeError(f"Task not found: {task_id}")
        task.status, task.progress, task.started_at = "running", 10, datetime.utcnow()
        run_id = str(task.request_data["agent_run_id"])
        await db.commit()
        try:
            if task.task_type == CareerPlanningAgent.agent_type:
                request = CareerAnalysisRequest.model_validate(task.request_data["payload"])
                result = await CareerService(db).analyze(
                    request, user_id=task.created_by, agent_run_id=run_id
                )
            elif task.task_type == MatchExplanationAgent.agent_type:
                match_id = int(task.request_data["payload"]["match_id"])
                result = await MatchingService(db).explain(
                    match_id, task.created_by, agent_run_id=run_id
                )
            else:
                raise RuntimeError(f"Unsupported AI task type: {task.task_type}")
            task.status, task.progress = "succeeded", 100
            task.result = result.model_dump(mode="json")
            task.finished_at = datetime.utcnow()
            await db.commit()
            return task.result
        except Exception as exc:
            await db.rollback()
            task = await db.get(AsyncTask, task_id)
            run = await db.get(AgentRun, run_id)
            task.status = "failed"
            task.error_code, task.error_message = type(exc).__name__, str(exc)[:2000]
            task.finished_at = datetime.utcnow()
            if run:
                run.status = "failed"
                run.error_code, run.error_message = type(exc).__name__, str(exc)[:2000]
                run.finished_at = datetime.utcnow()
            await db.commit()
            raise


@celery_app.task(name="agent.process_ai")
def process_ai_agent(task_id: str) -> dict:
    return asyncio.run(_process_ai_agent(task_id))
