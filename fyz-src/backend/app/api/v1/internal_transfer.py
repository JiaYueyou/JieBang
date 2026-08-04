"""企业内部人才流动 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.internal_transfer import (
    EmployeeDirectoryCreate,
    EmployeeDirectorySummary,
    EnterpriseTalentCreate,
    EnterpriseTalentSummary,
    InternalMatchResult,
    InternalPositionCreate,
    InternalPositionStatus,
    InternalPositionStatusUpdate,
    InternalPositionSummary,
    MatchByPositionRequest,
    MatchByTalentRequest,
    SkillDemandSummary,
    TransferDecisionCreate,
    TransferDecisionSummary,
    TransferRuleSetCreate,
    TransferRuleSetSummary,
)
from app.services.internal_transfer_service import InternalTransferService

router = APIRouter(prefix="/internal-transfer", tags=["内部转岗"])


def service(db: AsyncSession = Depends(get_db)) -> InternalTransferService:
    return InternalTransferService(db)


@router.get("/employee-directory", response_model=ApiResponse[list[EmployeeDirectorySummary]])
async def search_employee_directory(
    keyword: str = Query(default="", max_length=50),
    limit: int = Query(default=10, ge=1, le=50),
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.search_employee_directory(keyword, limit=limit))


@router.post("/employee-directory", response_model=ApiResponse[EmployeeDirectorySummary])
async def sync_employee_directory(
    payload: EmployeeDirectoryCreate,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(
        message="企业员工主数据已同步",
        data=await svc.upsert_employee_directory(payload, user_id=principal.user_id),
    )


@router.get("/talents", response_model=ApiResponse[list[EnterpriseTalentSummary]])
async def list_talents(
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.list_talents())


@router.post("/talents", response_model=ApiResponse[EnterpriseTalentSummary])
async def create_talent(
    payload: EnterpriseTalentCreate,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(message="企业人才已添加", data=await svc.create_talent(payload, user_id=principal.user_id))


@router.post("/talents/from-directory/{employee_id}", response_model=ApiResponse[EnterpriseTalentSummary])
async def create_talent_from_directory(
    employee_id: int,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(
        message="员工已加入企业人才池",
        data=await svc.create_talent_from_directory(employee_id, user_id=principal.user_id),
    )


@router.get("/positions", response_model=ApiResponse[list[InternalPositionSummary]])
async def list_positions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: InternalPositionStatus | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=120),
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    rows, meta = await svc.list_positions(
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
    )
    return ApiResponse(data=rows, meta=meta)


@router.post("/positions", response_model=ApiResponse[InternalPositionSummary])
async def create_position(
    payload: InternalPositionCreate,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(message="内部岗位已创建", data=await svc.create_position(payload, user_id=principal.user_id))


@router.put("/positions/{position_id}/status", response_model=ApiResponse[InternalPositionSummary])
async def update_position_status(
    position_id: int,
    payload: InternalPositionStatusUpdate,
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(message="内部岗位状态已更新", data=await svc.update_position_status(position_id, payload.status))


@router.get("/skill-demands", response_model=ApiResponse[list[SkillDemandSummary]])
async def list_skill_demands(
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.list_skill_demands())


@router.get("/rule-sets", response_model=ApiResponse[list[TransferRuleSetSummary]])
async def list_rule_sets(
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.list_rule_sets())


@router.post("/rule-sets", response_model=ApiResponse[TransferRuleSetSummary])
async def create_rule_set(
    payload: TransferRuleSetCreate,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(message="转岗规则已保存", data=await svc.create_rule_set(payload, user_id=principal.user_id))


@router.post("/matches/by-talent", response_model=ApiResponse[list[InternalMatchResult]])
async def match_by_talent(
    payload: MatchByTalentRequest,
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.match_by_talent(
        payload.talent_id, position_ids=payload.position_ids, rule_set_id=payload.rule_set_id
    ))


@router.post("/matches/by-position", response_model=ApiResponse[list[InternalMatchResult]])
async def match_by_position(
    payload: MatchByPositionRequest,
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.match_by_position(
        payload.position_id, talent_ids=payload.talent_ids, rule_set_id=payload.rule_set_id
    ))


@router.get("/decisions", response_model=ApiResponse[list[TransferDecisionSummary]])
async def list_decisions(
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.list_decisions())


@router.post("/decisions", response_model=ApiResponse[TransferDecisionSummary])
async def create_decision(
    payload: TransferDecisionCreate,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(message="人岗决策已确认", data=await svc.create_decision(payload, user_id=principal.user_id))
