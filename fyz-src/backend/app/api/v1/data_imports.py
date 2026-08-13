"""数据导入与任务状态 API。"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.skill import DataImportRequest, TaskStatusResponse
from app.services import ImportService, TaskService

router = APIRouter(tags=["数据导入"])
logger = logging.getLogger(__name__)


@router.post(
    "/data-imports/jobs",
    response_model=ApiResponse[TaskStatusResponse],
)
async def import_jobs(
    payload: DataImportRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TaskStatusResponse]:
    # 请求进入队列前确认文件位于本地数据目录且为 JSON。
    ImportService.resolve_files(payload.files)
    task = await TaskService(db).create_import(
        files=payload.files, user_id=principal.user_id
    )
    logger.info(
        "job_import_created task_id=%s file_count=%d files=%s user_id=%s",
        task.task_id, len(payload.files), ",".join(payload.files), principal.user_id,
    )
    return ApiResponse(message="导入任务已创建", data=task)


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[TaskStatusResponse],
)
async def get_task(
    task_id: str,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TaskStatusResponse]:
    return ApiResponse(data=await TaskService(db).get(task_id, user_id=principal.user_id))
