"""标准技能库 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.skill import SkillSummary
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


@router.get("/{skill_id}", response_model=ApiResponse[SkillSummary])
async def get_skill(
    skill_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
) -> ApiResponse[SkillSummary]:
    return ApiResponse(data=await service.get_skill(skill_id))
