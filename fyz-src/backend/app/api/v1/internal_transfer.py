"""企业内部人才流动 API。"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.internal_transfer import (
    EnterpriseDepartmentCreate,
    EnterpriseDepartmentSummary,
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
    TransferRuleSetUpdate,
    TransferRuleSetSummary,
    ResumeAdmissionRequest,
)
from app.services.internal_transfer_service import InternalTransferService

router = APIRouter(prefix="/internal-transfer", tags=["内部转岗"])


def service(db: AsyncSession = Depends(get_db)) -> InternalTransferService:
    return InternalTransferService(db)


@router.get("/departments", response_model=ApiResponse[list[EnterpriseDepartmentSummary]])
async def list_departments(
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.list_departments(user_id=principal.user_id))


@router.post("/departments", response_model=ApiResponse[EnterpriseDepartmentSummary])
async def create_department(
    payload: EnterpriseDepartmentCreate,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(message="企业部门已创建", data=await svc.create_department(payload, user_id=principal.user_id))


@router.put("/departments/{department_id}", response_model=ApiResponse[EnterpriseDepartmentSummary])
async def update_department(
    department_id: int,
    payload: EnterpriseDepartmentCreate,
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(message="企业部门已更新", data=await svc.update_department(department_id, payload))


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    await svc.delete_department(department_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/employee-directory", response_model=ApiResponse[list[EmployeeDirectorySummary]])
async def search_employee_directory(
    keyword: str = Query(default="", max_length=50),
    department: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.search_employee_directory(keyword, department=department, limit=limit))


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


@router.put("/employee-directory/{employee_id}", response_model=ApiResponse[EmployeeDirectorySummary])
async def update_employee_directory(
    employee_id: int,
    payload: EmployeeDirectoryCreate,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(
        message="员工目录已更新",
        data=await svc.update_employee_directory(employee_id, payload, user_id=principal.user_id),
    )


@router.delete("/employee-directory/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee_directory(
    employee_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    await svc.delete_employee_directory(employee_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.post("/talents/from-resume/{resume_id}", response_model=ApiResponse[EnterpriseTalentSummary])
async def admit_resume_to_talent_pool(
    resume_id: int,
    payload: ResumeAdmissionRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(
        message="候选人已录用并加入企业人才池",
        data=await svc.admit_resume(resume_id, payload, user_id=principal.user_id),
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


@router.get("/rule-sets/{rule_id}", response_model=ApiResponse[TransferRuleSetSummary])
async def get_rule_set(
    rule_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(data=await svc.get_rule_set(rule_id))


@router.post("/rule-sets", response_model=ApiResponse[TransferRuleSetSummary])
async def create_rule_set(
    payload: TransferRuleSetCreate,
    principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(message="转岗规则已保存", data=await svc.create_rule_set(payload, user_id=principal.user_id))


@router.put("/rule-sets/{rule_id}", response_model=ApiResponse[TransferRuleSetSummary])
async def update_rule_set(
    rule_id: int,
    payload: TransferRuleSetUpdate,
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    return ApiResponse(message="转岗规则已更新", data=await svc.update_rule_set(rule_id, payload))


@router.delete("/rule-sets/{rule_id}", response_model=ApiResponse[dict])
async def delete_rule_set(
    rule_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    svc: InternalTransferService = Depends(service),
):
    await svc.delete_rule_set(rule_id)
    return ApiResponse(message="转岗规则已删除", data={"id": rule_id})


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
