"""批量 JD 导入 Celery 任务。"""

import asyncio

from app.core.cache import close_cache
from app.core.celery_app import celery_app
from app.core.database import async_session, engine
from app.core.time import utc_now_naive
from app.domain.statuses import TaskStatus
from app.models import AsyncTask
from app.services.import_service import ImportService
from app.services.task_status_cache import bump_cache_generations, publish_task_status


async def _process(task_id: str, files: list[str]) -> dict:
    async with async_session() as db:
        task = await db.get(AsyncTask, task_id)
        if not task:
            raise RuntimeError(f"Task not found: {task_id}")
        task.status = TaskStatus.running.value
        task.started_at = utc_now_naive()
        await db.commit()
        await publish_task_status(task)

        async def progress(value: int) -> None:
            if value <= task.progress:
                return
            task.progress = value
            await db.commit()
            await publish_task_status(task)

        try:
            result = await ImportService(db).import_files(
                files, progress_callback=progress
            )
            task.status = TaskStatus.succeeded.value
            task.progress = 100
            task.result = result
            task.finished_at = utc_now_naive()
            await db.commit()
            await publish_task_status(task)
            await bump_cache_generations("analysis", "dashboard")
            return result
        except Exception as exc:
            await db.rollback()
            task = await db.get(AsyncTask, task_id)
            task.status = TaskStatus.failed.value
            task.error_code = type(exc).__name__
            task.error_message = str(exc)[:2000]
            task.finished_at = utc_now_naive()
            await db.commit()
            await publish_task_status(task)
            raise


@celery_app.task(name="skill_import.process_job_files")
def process_job_files(task_id: str, files: list[str]) -> dict:
    async def run() -> dict:
        try:
            return await _process(task_id, files)
        finally:
            # Avoid reusing aiomysql connections bound to a closed event loop
            # when the Windows solo worker executes the next task.
            await close_cache()
            await engine.dispose()

    return asyncio.run(run())
