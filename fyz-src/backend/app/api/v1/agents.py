"""Agent 任务创建与运行审计 API。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.agent import (
    AgentRunResponse, AgentTaskResponse, GenerateJDRequest,
    JDGenerationTaskResponse, JDInputSuggestionRequest, MatchExplanationTaskRequest,
)
from app.schemas.auth import TokenPrincipal
from app.schemas.career import CareerAnalysisRequest
from app.schemas.common import ApiResponse
from app.services.jd_generation_service import JDGenerationService
from app.services.ai_agent_task_service import AIAgentTaskService

router = APIRouter(prefix="/agents", tags=["Agent"])


@router.post("/career-plannings", response_model=ApiResponse[AgentTaskResponse])
async def create_career_planning(
    payload: CareerAnalysisRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await AIAgentTaskService(db).create_career_task(
        payload, user_id=principal.user_id
    )
    return ApiResponse(message="转岗规划任务已创建", data=result)


@router.post("/match-explanations", response_model=ApiResponse[AgentTaskResponse])
async def create_match_explanation(
    payload: MatchExplanationTaskRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await AIAgentTaskService(db).create_match_task(
        payload.match_id, user_id=principal.user_id
    )
    return ApiResponse(message="匹配解释任务已创建", data=result)


@router.post("/jd-generations", response_model=ApiResponse[JDGenerationTaskResponse])
async def create_jd_generation(
    payload: GenerateJDRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[JDGenerationTaskResponse]:
    result = await JDGenerationService(db).create_task(payload, user_id=principal.user_id)
    return ApiResponse(message="JD 生成任务已创建", data=result)


@router.post(
    "/jd-input-suggestions",
    response_model=ApiResponse[JDGenerationTaskResponse],
)
async def create_jd_input_suggestion(
    payload: JDInputSuggestionRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[JDGenerationTaskResponse]:
    result = await JDGenerationService(db).create_suggestion_task(
        payload, user_id=principal.user_id
    )
    return ApiResponse(message="JD 输入建议任务已创建", data=result)


@router.get("/runs/{agent_run_id}", response_model=ApiResponse[AgentRunResponse])
async def get_agent_run(
    agent_run_id: str,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AgentRunResponse]:
    return ApiResponse(
        data=await JDGenerationService(db).get_run(
            agent_run_id, user_id=principal.user_id
        )
    )
