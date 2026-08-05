"""
人岗匹配 API —— 单人匹配、批量匹配、历史查询。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.match_service import MatchService
from app.schemas.match import (
    MatchRequest, BatchMatchRequest, MatchResultResponse,
)
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/match", tags=["匹配"])


def get_match_service(db: AsyncSession = Depends(get_db)) -> MatchService:
    """依赖注入：创建匹配服务实例"""
    return MatchService(db)


@router.post("", response_model=ApiResponse[MatchResultResponse])
async def do_match(
    req: MatchRequest,
    user: dict = Depends(get_current_user),
    service: MatchService = Depends(get_match_service),
):
    """执行单次人岗匹配"""
    result = await service.do_match(user["user_id"], req.resume_id, req.position_id)
    return ApiResponse(data=result)


@router.post("/batch", response_model=ApiResponse[list[MatchResultResponse]])
async def batch_match(
    req: BatchMatchRequest,
    user: dict = Depends(get_current_user),
    service: MatchService = Depends(get_match_service),
):
    """批量匹配（一份简历 vs 多个岗位）"""
    results = await service.batch_match(user["user_id"], req.resume_id, req.position_ids)
    return ApiResponse(data=results)


@router.post("/auto/{resume_id}", response_model=ApiResponse[list[MatchResultResponse]])
async def auto_match(
    resume_id: int,
    user: dict = Depends(get_current_user),
    service: MatchService = Depends(get_match_service),
):
    """[Agent 3 智能匹配] 自动将简历与系统中所有岗位逐一匹配，按综合分数降序返回诊断报告列表"""
    results = await service.auto_match(user["user_id"], resume_id)
    return ApiResponse(data=results)


@router.get("/result/{resume_id}/{position_id}", response_model=ApiResponse[MatchResultResponse])
async def get_match_result(
    resume_id: int,
    position_id: int,
    service: MatchService = Depends(get_match_service),
):
    """获取已有匹配结果"""
    result = await service.get_result(resume_id, position_id)
    return ApiResponse(data=result)


@router.get("/history", response_model=ApiResponse[list[MatchResultResponse]])
async def get_match_history(
    user: dict = Depends(get_current_user),
    service: MatchService = Depends(get_match_service),
):
    """获取用户的匹配历史"""
    results = await service.get_history(user["user_id"])
    return ApiResponse(data=results)
