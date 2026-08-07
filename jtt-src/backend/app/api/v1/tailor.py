"""
简历优化 API —— AI 优化建议、短语润色（Agent 1: 简历优化智能体）。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.tailor_service import TailorService
from app.schemas.tailor import (
    AcceptSuggestionRequest, ApplyAllRequest,
    OptimizePhraseRequest, OptimizePhraseResponse,
    SaveAsNewRequest, SaveAsNewResponse,
    SuggestionResponse,
)
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/tailor", tags=["简历优化"])


def get_tailor_service(db: AsyncSession = Depends(get_db)) -> TailorService:
    """依赖注入：创建简历优化服务实例"""
    return TailorService(db)


@router.get("/suggestions/{resume_id}/{position_id}", response_model=ApiResponse[list[SuggestionResponse]])
async def get_suggestions(
    resume_id: int,
    position_id: str,
    service: TailorService = Depends(get_tailor_service),
):
    """获取 AI 优化建议列表（含图谱回查防幻觉校验）"""
    suggestions = await service.get_suggestions(resume_id, position_id)
    return ApiResponse(data=suggestions)


@router.post("/accept", response_model=ApiResponse)
async def accept_suggestion(
    req: AcceptSuggestionRequest,
    service: TailorService = Depends(get_tailor_service),
):
    """接受单条优化建议"""
    await service.accept_suggestion(req.resume_id, req.suggestion_id)
    return ApiResponse(message="已接受")


@router.post("/apply-all", response_model=ApiResponse[SaveAsNewResponse])
async def apply_all(
    req: ApplyAllRequest,
    service: TailorService = Depends(get_tailor_service),
):
    """批量应用所有已接受的建议，生成新简历"""
    payload = [s.model_dump() for s in (req.suggestions or [])] or None
    new_id = await service.apply_all(req.resume_id, req.suggestion_ids, payload)
    return ApiResponse(data={"new_resume_id": new_id})


@router.post("/optimize-phrase", response_model=ApiResponse[OptimizePhraseResponse])
async def optimize_phrase(
    req: OptimizePhraseRequest,
    service: TailorService = Depends(get_tailor_service),
):
    """AI 短语润色 —— 将单段文本按指定风格改写"""
    suggestions = await service.optimize_phrase(req.text, req.style)
    return ApiResponse(data={"suggestions": suggestions})


@router.post("/save-as-new", response_model=ApiResponse[SaveAsNewResponse])
async def save_as_new(
    req: SaveAsNewRequest,
    service: TailorService = Depends(get_tailor_service),
):
    """保存优化后的简历为新版本"""
    payload = [s.model_dump() for s in (req.suggestions or [])] or None
    new_id = await service.save_as_new(req.resume_id, req.suggestion_ids, payload)
    return ApiResponse(data={"new_resume_id": new_id})
