"""Neo4j 图谱同步 Celery 任务。"""

import asyncio

from app.core.celery_app import celery_app
from app.core.database import async_session, engine
from app.core.time import utc_now_naive
from app.domain.statuses import TaskStatus
from app.models import AsyncTask
from app.services.graph_service import GraphService


async def _process_graph_sync(
    task_id: str, mode: str, enrich_top_skills: bool, user_id: int | None
) -> dict:
    try:
        async with async_session() as db:
            task = await db.get(AsyncTask, task_id)
            if not task:
                raise RuntimeError(f"Task not found: {task_id}")
            task.status = TaskStatus.running.value
            task.progress = 1
            task.started_at = task.started_at or utc_now_naive()
            task.result = {
                "stage": "waiting",
                "detail": "正在等待其他图谱同步任务完成",
            }
            await db.commit()
        async with async_session() as db:
            task = await db.get(AsyncTask, task_id)
            if not task:
                raise RuntimeError(f"Task not found: {task_id}")
            try:
                result = await GraphService(db).sync(
                    mode=mode,
                    enrich_top_skills=enrich_top_skills,
                    user_id=user_id,
                    task_id=task_id,
                )
                task = await db.get(AsyncTask, task_id)
                task.status = TaskStatus.succeeded.value
                task.progress = 100
                task.result = result
                task.finished_at = utc_now_naive()
                await db.commit()
                return result
            except Exception:
                await db.rollback()
                raise
    except Exception as exc:
        async with async_session() as db:
            task = await db.get(AsyncTask, task_id)
            if task:
                task.status = TaskStatus.failed.value
                task.error_code = type(exc).__name__
                task.error_message = str(exc)[:2000]
                task.finished_at = utc_now_naive()
                await db.commit()
        raise


@celery_app.task(name="graph.process_sync")
def process_graph_sync(
    task_id: str, mode: str, enrich_top_skills: bool, user_id: int | None
) -> dict:
    async def run() -> dict:
        try:
            return await _process_graph_sync(task_id, mode, enrich_top_skills, user_id)
        finally:
            # Celery's Windows solo pool creates a fresh loop per asyncio.run().
            # Drop pooled async connections before that loop is closed.
            await engine.dispose()

    return asyncio.run(run())
