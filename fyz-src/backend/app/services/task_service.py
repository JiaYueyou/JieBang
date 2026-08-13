"""异步任务创建、分发与状态查询。"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.core.config import CELERY_TASK_ALWAYS_EAGER
from app.domain.statuses import TaskStatus
from app.models import AsyncTask
from app.repositories import TaskRepository
from app.schemas.skill import TaskStatusResponse
from app.services.task_status_cache import get_cached_task_status, publish_task_status


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tasks = TaskRepository(db)

    async def create_import(self, *, files: list[str], user_id: int) -> TaskStatusResponse:
        # Import lazily so Celery can discover app.tasks.skill_import without
        # task_service importing that same, partially initialized module.
        from app.tasks.skill_import import _process, process_job_files

        task = AsyncTask(
            id=str(uuid.uuid4()),
            task_type="job_data_import",
            status=TaskStatus.queued.value,
            progress=0,
            request_data={"files": files},
            created_by=user_id,
        )
        await self.tasks.create(task)
        await self.db.commit()
        if CELERY_TASK_ALWAYS_EAGER:
            await _process(task.id, files)
        else:
            process_job_files.delay(task.id, files)
        await self.db.refresh(task)
        await publish_task_status(task)
        return self.to_response(task)

    async def get(self, task_id: str, *, user_id: int | None = None) -> TaskStatusResponse:
        cached = await get_cached_task_status(task_id)
        if cached is not None:
            response, created_by = cached
            if user_id is not None and created_by != user_id:
                raise ResourceNotFoundError("任务不存在")
            return response
        task = await self.tasks.get(task_id)
        if not task or (user_id is not None and task.created_by != user_id):
            raise ResourceNotFoundError("任务不存在")
        await publish_task_status(task)
        return self.to_response(task)

    @staticmethod
    def to_response(task: AsyncTask) -> TaskStatusResponse:
        return TaskStatusResponse(
            task_id=task.id, task_type=task.task_type, status=task.status,
            progress=task.progress, result=task.result,
            error_code=task.error_code, error_message=task.error_message,
            created_at=task.created_at, started_at=task.started_at,
            finished_at=task.finished_at,
        )
