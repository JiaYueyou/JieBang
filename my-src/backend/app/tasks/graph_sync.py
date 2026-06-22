"""Neo4j 图谱同步 Celery 任务。"""

import asyncio
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import async_session
from app.models import AsyncTask
from app.services.graph_service import GraphService


async def _process_graph_sync(
    task_id: str, mode: str, enrich_top_skills: bool, user_id: int | None
) -> dict:
    async with async_session() as db:
        task = await db.get(AsyncTask, task_id)
        if not task:
            raise RuntimeError(f"Task not found: {task_id}")
        task.status = "running"
        task.progress = 5
        task.started_at = datetime.utcnow()
        await db.commit()
        try:
            result = await GraphService(db).sync(
                mode=mode,
                enrich_top_skills=enrich_top_skills,
                user_id=user_id,
                task_id=task_id,
            )
            task = await db.get(AsyncTask, task_id)
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


@celery_app.task(name="graph.process_sync")
def process_graph_sync(
    task_id: str, mode: str, enrich_top_skills: bool, user_id: int | None
) -> dict:
    return asyncio.run(_process_graph_sync(task_id, mode, enrich_top_skills, user_id))
