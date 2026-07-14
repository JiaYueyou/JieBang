"""Run Agent tasks inside the FastAPI process without Redis or Celery."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.core.database import async_session
from app.models import AsyncTask

logger = logging.getLogger(__name__)

AGENT_TASK_TYPES = {"jd_generation", "jd_input_suggestion", "career_planning", "match_explanation"}
_running_tasks: dict[str, asyncio.Task[dict]] = {}


def dispatch_agent_task(task_id: str, task_type: str) -> None:
    """Schedule one persisted task and keep a strong reference until it finishes."""
    current = _running_tasks.get(task_id)
    if current is not None and not current.done():
        return

    if task_type in {"jd_generation", "jd_input_suggestion"}:
        from app.tasks.jd_generation import _process_jd_generation

        coroutine = _process_jd_generation(task_id)
    elif task_type in {"career_planning", "match_explanation"}:
        from app.tasks.ai_agents import _process_ai_agent

        coroutine = _process_ai_agent(task_id)
    else:
        raise ValueError(f"Unsupported in-process Agent task type: {task_type}")

    task = asyncio.create_task(coroutine, name=f"agent:{task_type}:{task_id}")
    _running_tasks[task_id] = task
    task.add_done_callback(lambda completed: _task_finished(task_id, completed))


def _task_finished(task_id: str, task: asyncio.Task[dict]) -> None:
    _running_tasks.pop(task_id, None)
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        logger.error(
            "In-process Agent task %s failed: %s: %s",
            task_id,
            type(error).__name__,
            error,
        )


async def recover_pending_agent_tasks() -> int:
    """Resume queued/running Agent work after an API process restart."""
    async with async_session() as db:
        rows = list(
            (
                await db.execute(
                    select(AsyncTask.id, AsyncTask.task_type).where(
                        AsyncTask.task_type.in_(AGENT_TASK_TYPES),
                        AsyncTask.status.in_({"queued", "running"}),
                    )
                )
            ).all()
        )
    for task_id, task_type in rows:
        dispatch_agent_task(task_id, task_type)
    return len(rows)


async def shutdown_agent_tasks() -> None:
    """Cancel local work on shutdown; startup recovery will resume persisted tasks."""
    tasks = list(_running_tasks.values())
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    _running_tasks.clear()
