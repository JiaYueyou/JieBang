"""数据导入与任务状态 API。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.skill import DataImportRequest, TaskStatusResponse
from app.services import ImportService, TaskService

router = APIRouter(tags=["数据导入"])


@router.post(
    "/data-imports/jobs",
    response_model=ApiResponse[TaskStatusResponse],
)
async def import_jobs(
    payload: DataImportRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TaskStatusResponse]:
    # 请求进入队列前先校验文件白名单与存在性。
    ImportService.resolve_files(payload.files)
    task = await TaskService(db).create_import(
        files=payload.files, user_id=principal.user_id
    )
    return ApiResponse(message="导入任务已创建", data=task)


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[TaskStatusResponse],
)
async def get_task(
    task_id: str,
    _principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TaskStatusResponse]:
    return ApiResponse(data=await TaskService(db).get(task_id))
