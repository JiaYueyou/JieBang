"""岗位管理 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.job import (
    JobCreate,
    JobStatus,
    JobStatusUpdate,
    JobSummary,
    JobUpdate,
    JobVersionResponse,
)
from app.schemas.skill import JobExtractionResult, SkillFactResponse
from app.services import JobService, SkillService

router = APIRouter(prefix="/jobs", tags=["岗位管理"])


def get_job_service(db: AsyncSession = Depends(get_db)) -> JobService:
    return JobService(db)


def get_skill_service(db: AsyncSession = Depends(get_db)) -> SkillService:
    return SkillService(db)


common_errors = {
    401: {"model": ApiResponse[None], "description": "认证失败"},
    404: {"model": ApiResponse[None], "description": "岗位不存在"},
    422: {"model": ApiResponse[None], "description": "参数校验失败"},
}


@router.get("", response_model=ApiResponse[list[JobSummary]], responses=common_errors)
@router.get(
    "/",
    response_model=ApiResponse[list[JobSummary]],
    responses=common_errors,
    include_in_schema=False,
)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: JobStatus | None = None,
    keyword: str | None = Query(default=None, max_length=120),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> ApiResponse[list[JobSummary]]:
    rows, meta = await service.list(
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
    )
    return ApiResponse(data=rows, meta=meta)


@router.post("", response_model=ApiResponse[JobSummary], responses=common_errors)
async def create_job(
    payload: JobCreate,
    principal: TokenPrincipal = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> ApiResponse[JobSummary]:
    return ApiResponse(
        message="岗位创建成功",
        data=await service.create(payload, user_id=principal.user_id),
    )


@router.get(
    "/{job_id}",
    response_model=ApiResponse[JobSummary],
    responses=common_errors,
)
async def get_job(
    job_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> ApiResponse[JobSummary]:
    return ApiResponse(data=await service.get(job_id))


@router.put(
    "/{job_id}",
    response_model=ApiResponse[JobSummary],
    responses=common_errors,
)
async def update_job(
    job_id: int,
    payload: JobUpdate,
    principal: TokenPrincipal = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> ApiResponse[JobSummary]:
    return ApiResponse(
        message="岗位更新成功",
        data=await service.update(job_id, payload, user_id=principal.user_id),
    )


@router.delete(
    "/{job_id}",
    response_model=ApiResponse[None],
    responses=common_errors,
)
async def delete_job(
    job_id: int,
    principal: TokenPrincipal = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> ApiResponse[None]:
    await service.delete(job_id, user_id=principal.user_id)
    return ApiResponse(message="岗位删除成功")


@router.put(
    "/{job_id}/status",
    response_model=ApiResponse[JobSummary],
    responses=common_errors,
)
async def update_job_status(
    job_id: int,
    payload: JobStatusUpdate,
    principal: TokenPrincipal = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> ApiResponse[JobSummary]:
    return ApiResponse(
        message="岗位状态更新成功",
        data=await service.update_status(
            job_id,
            payload.status,
            user_id=principal.user_id,
        ),
    )


@router.get(
    "/{job_id}/versions",
    response_model=ApiResponse[list[JobVersionResponse]],
    responses=common_errors,
)
async def list_job_versions(
    job_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> ApiResponse[list[JobVersionResponse]]:
    return ApiResponse(data=await service.list_versions(job_id))


@router.get(
    "/{job_id}/versions/{version_id}",
    response_model=ApiResponse[JobVersionResponse],
    responses=common_errors,
)
async def get_job_version(
    job_id: int,
    version_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
) -> ApiResponse[JobVersionResponse]:
    return ApiResponse(data=await service.get_version(job_id, version_id))


@router.post(
    "/{job_id}/extract-skills",
    response_model=ApiResponse[JobExtractionResult],
    responses=common_errors,
)
async def extract_job_skills(
    job_id: int,
    principal: TokenPrincipal = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
) -> ApiResponse[JobExtractionResult]:
    result = await service.extract_job(job_id, user_id=principal.user_id)
    return ApiResponse(message="技能抽取完成", data=result)


@router.get(
    "/{job_id}/skill-facts",
    response_model=ApiResponse[list[SkillFactResponse]],
    responses=common_errors,
)
async def get_job_skill_facts(
    job_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
) -> ApiResponse[list[SkillFactResponse]]:
    return ApiResponse(data=await service.list_job_facts(job_id))
