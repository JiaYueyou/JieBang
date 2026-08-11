"""智能 JD 草稿生成持久化任务。"""

from app.core.database import async_session
from app.core.time import utc_now
from app.domain.agent_status import AgentRunStatus, AsyncTaskStatus
from app.models import AgentRun, AsyncTask
from app.schemas.agent import GenerateJDRequest, JDInputSuggestionRequest
from app.services.jd_generation_service import JDGenerationService
from app.services.task_status_cache import publish_task_status


async def _process_jd_generation(task_id: str) -> dict:
    async with async_session() as db:
        task = await db.get(AsyncTask, task_id)
        if not task:
            raise RuntimeError(f"Task not found: {task_id}")
        started_at = utc_now()
        task.status = AsyncTaskStatus.running
        task.progress = 10
        task.started_at = started_at
        run_id = str(task.request_data["agent_run_id"])
        await db.commit()
        await publish_task_status(task)
        try:
            service = JDGenerationService(db)
            if task.task_type == service.agent.suggestion_task_type:
                request = JDInputSuggestionRequest.model_validate(task.request_data["payload"])
                result = await service.suggest_input(request, agent_run_id=run_id)
            else:
                request = GenerateJDRequest.model_validate(task.request_data["payload"])
                result = await service.generate(request, agent_run_id=run_id)
            task.status = AsyncTaskStatus.succeeded
            task.progress = 100
            task.result = result.model_dump(mode="json")
            task.finished_at = utc_now()
            await db.commit()
            await publish_task_status(task)
            return task.result
        except Exception as exc:
            await db.rollback()
            task = await db.get(AsyncTask, task_id)
            run = await db.get(AgentRun, run_id)
            task.status = AsyncTaskStatus.failed
            task.error_code = type(exc).__name__
            task.error_message = str(exc)[:2000]
            task.finished_at = utc_now()
            if run:
                run.status = AgentRunStatus.failed
                run.error_code = type(exc).__name__
                run.error_message = str(exc)[:2000]
                run.finished_at = utc_now()
            await db.commit()
            await publish_task_status(task)
            raise
