"""
简历相关 API —— 简历 CRUD、上传解析。
"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.resume_service import ResumeService
from app.schemas.resume import (
    ResumeCreate, ResumeUpdate, ResumeResponse, ResumeUploadResponse,
)
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/resume", tags=["简历"])


def get_resume_service(db: AsyncSession = Depends(get_db)) -> ResumeService:
    """依赖注入：创建简历服务实例"""
    return ResumeService(db)


@router.post("/upload", response_model=ApiResponse[ResumeUploadResponse])
async def upload_resume(
    file: UploadFile = File(..., description="简历文件（PDF/Word）"),
    user: dict = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
):
    """上传并解析简历文件，提取结构化信息"""
    content = await file.read()
    result = await service.parse_upload(user["user_id"], content, file.filename or "简历")
    return ApiResponse(data=result)


@router.get("/resumes", response_model=ApiResponse[list[ResumeResponse]])
async def list_resumes(
    user: dict = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
):
    """获取当前用户的所有简历"""
    resumes = await service.list_resumes(user["user_id"])
    return ApiResponse(data=resumes)


@router.get("/{resume_id}", response_model=ApiResponse[ResumeResponse])
async def get_resume(
    resume_id: int,
    service: ResumeService = Depends(get_resume_service),
):
    """获取简历详情"""
    detail = await service.get_detail(resume_id)
    return ApiResponse(data=detail)


@router.post("", response_model=ApiResponse[ResumeResponse])
async def create_resume(
    req: ResumeCreate,
    user: dict = Depends(get_current_user),
    service: ResumeService = Depends(get_resume_service),
):
    """手动创建空简历"""
    resume = await service.create(user["user_id"], req.model_dump())
    return ApiResponse(data=resume)


@router.put("/{resume_id}", response_model=ApiResponse[ResumeResponse])
async def update_resume(
    resume_id: int,
    req: ResumeUpdate,
    service: ResumeService = Depends(get_resume_service),
):
    """更新简历内容"""
    resume = await service.update(resume_id, req.model_dump(exclude_none=True))
    return ApiResponse(data=resume)


@router.delete("/{resume_id}", response_model=ApiResponse)
async def delete_resume(
    resume_id: int,
    service: ResumeService = Depends(get_resume_service),
):
    """删除简历"""
    await service.delete(resume_id)
    return ApiResponse(message="简历已删除")


@router.post("/{resume_id}/duplicate", response_model=ApiResponse[ResumeResponse])
async def duplicate_resume(
    resume_id: int,
    service: ResumeService = Depends(get_resume_service),
):
    """复制简历，生成副本"""
    new_resume = await service.duplicate(resume_id)
    return ApiResponse(data=new_resume)
