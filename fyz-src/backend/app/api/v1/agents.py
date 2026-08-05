"""Agent 任务创建与运行审计 API。"""

from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin, require_recruiter
from app.domain.agent_status import AgentRunStatus
from app.schemas.agent import (
    AgentRunResponse, AgentTaskResponse, GenerateJDRequest,
    JDGenerationTaskResponse, JDInputSuggestionRequest, MatchExplanationTaskRequest,
)
from app.schemas.auth import TokenPrincipal
from app.schemas.career import CareerAnalysisRequest
from app.schemas.common import ApiResponse
from app.schemas.common import PageMeta
from app.services.agent_run_service import AgentRunService
from app.services.jd_generation_service import JDGenerationService
from app.services.ai_agent_task_service import AIAgentTaskService

router = APIRouter(prefix="/agents", tags=["Agent"])


@router.post("/career-plannings", response_model=ApiResponse[AgentTaskResponse])
async def create_career_planning(
    payload: CareerAnalysisRequest,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", max_length=64  # gitleaks:allow
    ),
    principal: TokenPrincipal = Depends(require_recruiter),
    db: AsyncSession = Depends(get_db),
):
    result = await AIAgentTaskService(db).create_career_task(
        payload, user_id=principal.user_id, idempotency_key=idempotency_key
    )
    return ApiResponse(message="转岗规划任务已创建", data=result)


@router.post("/match-explanations", response_model=ApiResponse[AgentTaskResponse])
async def create_match_explanation(
    payload: MatchExplanationTaskRequest,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", max_length=64  # gitleaks:allow
    ),
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await AIAgentTaskService(db).create_match_task(
        payload.match_id, user_id=principal.user_id, idempotency_key=idempotency_key
    )
    return ApiResponse(message="匹配解释任务已创建", data=result)


@router.post("/jd-generations", response_model=ApiResponse[JDGenerationTaskResponse])
async def create_jd_generation(
    payload: GenerateJDRequest,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", max_length=64  # gitleaks:allow
    ),
    principal: TokenPrincipal = Depends(require_recruiter),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[JDGenerationTaskResponse]:
    result = await JDGenerationService(db).create_task(
        payload, user_id=principal.user_id, idempotency_key=idempotency_key
    )
    return ApiResponse(message="JD 生成任务已创建", data=result)


@router.post(
    "/jd-input-suggestions",
    response_model=ApiResponse[JDGenerationTaskResponse],
)
async def create_jd_input_suggestion(
    payload: JDInputSuggestionRequest,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", max_length=64  # gitleaks:allow
    ),
    principal: TokenPrincipal = Depends(require_recruiter),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[JDGenerationTaskResponse]:
    result = await JDGenerationService(db).create_suggestion_task(
        payload, user_id=principal.user_id, idempotency_key=idempotency_key
    )
    return ApiResponse(message="JD 输入建议任务已创建", data=result)


@router.get("/runs/{agent_run_id}", response_model=ApiResponse[AgentRunResponse])
async def get_agent_run(
    agent_run_id: str,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[AgentRunResponse]:
    return ApiResponse(data=await AgentRunService(db).get(
        agent_run_id,
        user_id=principal.user_id,
        allow_all=principal.role == "admin",
    ))


@router.get("/runs", response_model=ApiResponse[list[AgentRunResponse]])
async def list_agent_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    agent_type: str | None = Query(default=None, max_length=50),
    status: AgentRunStatus | None = Query(default=None),
    created_by: int | None = Query(default=None, ge=1),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    _principal: TokenPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[AgentRunResponse]]:
    rows, total = await AgentRunService(db).list(
        page=page,
        page_size=page_size,
        agent_type=agent_type,
        status=status.value if status else None,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
    )
    return ApiResponse(
        data=rows,
        meta=PageMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total else 0,
        ),
    )
