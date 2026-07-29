"""岗位洞察与趋势分析 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.analysis import (
    AnalysisOverview,
    InsightDecisionRequest,
    InsightDecisionResponse,
    JobInsightsResponse,
    TrendWindow,
)
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["趋势分析"])


def get_analysis_service(db: AsyncSession = Depends(get_db)) -> AnalysisService:
    return AnalysisService(db)


@router.get("/", response_model=ApiResponse[dict])
async def analysis_home(
    _principal: TokenPrincipal = Depends(get_current_user),
) -> ApiResponse[dict]:
    return ApiResponse(data={"message": "趋势分析", "status": "ready"})


@router.get("/overview", response_model=ApiResponse[AnalysisOverview])
async def overview(
    window: TrendWindow = Query(default=TrendWindow.months_3),
    keyword: str | None = Query(default=None, max_length=120),
    city: str | None = Query(default=None, max_length=100),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> ApiResponse[AnalysisOverview]:
    return ApiResponse(
        data=await service.overview(window=window, keyword=keyword, city=city)
    )


@router.get("/job-insights", response_model=ApiResponse[JobInsightsResponse])
async def job_insights(
    skill: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    principal: TokenPrincipal = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> ApiResponse[JobInsightsResponse]:
    return ApiResponse(
        data=await service.job_insights(
            skill=skill, limit=limit, user_id=principal.user_id
        )
    )


@router.put(
    "/emerging-jobs/{standard_job_id}/decision",
    response_model=ApiResponse[InsightDecisionResponse],
)
async def decide_emerging_job(
    standard_job_id: int,
    payload: InsightDecisionRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service),
) -> ApiResponse[InsightDecisionResponse]:
    return ApiResponse(
        message="洞察决策已保存",
        data=await service.decide_emerging_job(
            standard_job_id=standard_job_id,
            decision=payload.decision,
            note=payload.note,
            user_id=principal.user_id,
        ),
    )
