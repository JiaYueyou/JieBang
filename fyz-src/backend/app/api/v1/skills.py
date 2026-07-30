"""标准技能库 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.skill import (
    SkillFactReviewItem,
    SkillFactReviewList,
    SkillFactReviewRequest,
    SkillSummary,
    VerificationStatus,
)
from app.services import SkillService

router = APIRouter(prefix="/skills", tags=["标准技能"])


def get_skill_service(db: AsyncSession = Depends(get_db)) -> SkillService:
    return SkillService(db)


@router.get("", response_model=ApiResponse[list[SkillSummary]])
async def list_skills(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=50),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
) -> ApiResponse[list[SkillSummary]]:
    rows, meta = await service.list_skills(
        page=page, page_size=page_size, keyword=keyword, category=category
    )
    return ApiResponse(data=rows, meta=meta)


@router.get(
    "/facts/reviews",
    response_model=ApiResponse[SkillFactReviewList],
)
async def list_fact_reviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: VerificationStatus | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=100),
    _principal: TokenPrincipal = Depends(require_admin),
    service: SkillService = Depends(get_skill_service),
) -> ApiResponse[SkillFactReviewList]:
    rows, meta = await service.list_fact_reviews(
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
    )
    return ApiResponse(data=rows, meta=meta)


@router.patch(
    "/facts/{fact_id}/review",
    response_model=ApiResponse[SkillFactReviewItem],
)
async def review_fact(
    fact_id: int,
    payload: SkillFactReviewRequest,
    principal: TokenPrincipal = Depends(require_admin),
    service: SkillService = Depends(get_skill_service),
) -> ApiResponse[SkillFactReviewItem]:
    row = await service.review_fact(
        fact_id,
        decision=payload.decision,
        note=payload.note,
        reviewer_id=principal.user_id,
    )
    action = "确认" if payload.decision == VerificationStatus.verified else "驳回"
    return ApiResponse(message=f"技能事实已{action}", data=row)


@router.get("/{skill_id}", response_model=ApiResponse[SkillSummary])
async def get_skill(
    skill_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
) -> ApiResponse[SkillSummary]:
    return ApiResponse(data=await service.get_skill(skill_id))
