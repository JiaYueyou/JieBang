"""智能 JD 草稿生成 Celery 任务。"""

import asyncio
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import async_session
from app.models import AgentRun, AsyncTask
from app.schemas.agent import GenerateJDRequest
from app.services.jd_generation_service import JDGenerationService


async def _process_jd_generation(task_id: str) -> dict:
    async with async_session() as db:
        task = await db.get(AsyncTask, task_id)
        if not task:
            raise RuntimeError(f"Task not found: {task_id}")
        task.status = "running"
        task.progress = 10
        task.started_at = datetime.utcnow()
        await db.commit()
        run_id = str(task.request_data["agent_run_id"])
        try:
            request = GenerateJDRequest.model_validate(task.request_data["payload"])
            draft = await JDGenerationService(db).generate(request, agent_run_id=run_id)
            task.status = "succeeded"
            task.progress = 100
            task.result = draft.model_dump(mode="json")
            task.finished_at = datetime.utcnow()
            await db.commit()
            return task.result
        except Exception as exc:
            await db.rollback()
            task = await db.get(AsyncTask, task_id)
            run = await db.get(AgentRun, run_id)
            task.status = "failed"
            task.error_code = type(exc).__name__
            task.error_message = str(exc)[:2000]
            task.finished_at = datetime.utcnow()
            if run:
                run.status = "failed"
                run.error_code = type(exc).__name__
                run.error_message = str(exc)[:2000]
                run.finished_at = datetime.utcnow()
            await db.commit()
            raise


@celery_app.task(name="agent.generate_jd")
def process_jd_generation(task_id: str) -> dict:
    return asyncio.run(_process_jd_generation(task_id))
