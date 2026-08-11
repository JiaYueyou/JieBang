from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.services.dashboard_service import DashboardService
from app.services.query_cache import (
    DASHBOARD_CACHE_NAMESPACE,
    DASHBOARD_OVERVIEW_TTL_SECONDS,
    cached_dict_query,
)

router = APIRouter(prefix="/dashboard", tags=["工作台"])


@router.get("/overview", response_model=ApiResponse[dict])
async def dashboard_overview(
    hot_jobs_page: int = Query(default=1, ge=1),
    hot_jobs_page_size: int = Query(default=10, ge=1, le=50),
    emerging_page: int = Query(default=1, ge=1),
    emerging_page_size: int = Query(default=10, ge=1, le=50),
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    service = DashboardService(db)
    return ApiResponse(
        data=await cached_dict_query(
            generation_namespace=DASHBOARD_CACHE_NAMESPACE,
            operation="overview",
            params={
                "user_id": principal.user_id,
                "hot_jobs_page": hot_jobs_page,
                "hot_jobs_page_size": hot_jobs_page_size,
                "emerging_page": emerging_page,
                "emerging_page_size": emerging_page_size,
            },
            ttl_seconds=DASHBOARD_OVERVIEW_TTL_SECONDS,
            loader=lambda: service.overview(
                user_id=principal.user_id,
                hot_jobs_page=hot_jobs_page,
                hot_jobs_page_size=hot_jobs_page_size,
                emerging_page=emerging_page,
                emerging_page_size=emerging_page_size,
            ),
        )
    )
