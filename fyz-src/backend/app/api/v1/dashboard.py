from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["工作台"])


@router.get("/overview", response_model=ApiResponse[dict])
async def dashboard_overview(
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await DashboardService(db).overview(user_id=principal.user_id)
    )
