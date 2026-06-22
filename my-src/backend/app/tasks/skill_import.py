"""批量 JD 导入 Celery 任务。"""

import asyncio
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import async_session
from app.models import AsyncTask
from app.services.import_service import ImportService


async def _process(task_id: str, files: list[str]) -> dict:
    async with async_session() as db:
        task = await db.get(AsyncTask, task_id)
        if not task:
            raise RuntimeError(f"Task not found: {task_id}")
        task.status = "running"
        task.started_at = datetime.utcnow()
        await db.commit()

        async def progress(value: int) -> None:
            task.progress = value
            await db.commit()

        try:
            result = await ImportService(db).import_files(
                files, progress_callback=progress
            )
            task.status = "succeeded"
            task.progress = 100
            task.result = result
            task.finished_at = datetime.utcnow()
            await db.commit()
            return result
        except Exception as exc:
            await db.rollback()
            task = await db.get(AsyncTask, task_id)
            task.status = "failed"
            task.error_code = type(exc).__name__
            task.error_message = str(exc)[:2000]
            task.finished_at = datetime.utcnow()
            await db.commit()
            raise


@celery_app.task(name="skill_import.process_job_files")
def process_job_files(task_id: str, files: list[str]) -> dict:
    return asyncio.run(_process(task_id, files))
