"""Agent 任务创建与运行审计 API。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.agent import AgentRunResponse, GenerateJDRequest, JDGenerationTaskResponse
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.services.jd_generation_service import JDGenerationService

router = APIRouter(prefix="/agents", tags=["Agent"])


@router.post("/jd-generations", response_model=ApiResponse[JDGenerationTaskResponse])
async def create_jd_generation(
    payload: GenerateJDRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[JDGenerationTaskResponse]:
    result = await JDGenerationService(db).create_task(payload, user_id=principal.user_id)
    return ApiResponse(message="JD 生成任务已创建", data=result)


@router.get("/runs/{agent_run_id}", response_model=ApiResponse[AgentRunResponse])
async def get_agent_run(
    agent_run_id: str,
    _principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AgentRunResponse]:
    return ApiResponse(data=await JDGenerationService(db).get_run(agent_run_id))
