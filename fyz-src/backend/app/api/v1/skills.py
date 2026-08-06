"""标准技能库 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.skill import (
    SkillFactApproveAllRequest,
    SkillFactBatchReviewRequest,
    SkillFactBatchReviewResult,
    SkillFactReviewItem,
    SkillFactReviewList,
    SkillFactReviewRequest,
    SkillSummary,
    TaskStatusResponse,
    VerificationStatus,
)
from app.services import GraphTaskService, SkillService

router = APIRouter(prefix="/skills", tags=["标准技能"])


def get_skill_service(db: AsyncSession = Depends(get_db)) -> SkillService:
    return SkillService(db)


def get_graph_task_service(db: AsyncSession = Depends(get_db)) -> GraphTaskService:
    return GraphTaskService(db)


async def _auto_sync_graph_after_review(
    *,
    processed: int,
    decision: VerificationStatus,
    principal: TokenPrincipal,
    task_service: GraphTaskService,
) -> TaskStatusResponse | None:
    """事实审核确认后自动触发 L1~L3 图谱增量同步（进程内异步，不依赖 Celery）。

    同步会写入审核通过事实对应的 Job/SkillArea/TechStack 节点，
    实现"事实审核通过即入库可查询"。
    """
    if processed <= 0 or decision != VerificationStatus.verified:
        return None
    return await task_service.create_sync_in_background(
        mode="incremental", enrich_top_skills=False, user_id=principal.user_id,
    )


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
    task_service: GraphTaskService = Depends(get_graph_task_service),
) -> ApiResponse[SkillFactReviewItem]:
    row = await service.review_fact(
        fact_id,
        decision=payload.decision,
        note=payload.note,
        reviewer_id=principal.user_id,
    )
    action = "确认" if payload.decision == VerificationStatus.verified else "驳回"
    message = f"技能事实已{action}"
    task = await _auto_sync_graph_after_review(
        processed=1 if payload.decision == VerificationStatus.verified else 0,
        decision=payload.decision,
        principal=principal,
        task_service=task_service,
    )
    if task is not None:
        message += f"；已自动触发图谱增量同步（任务 {task.task_id[:8]}）"
    return ApiResponse(message=message, data=row)


@router.post(
    "/facts/reviews/batch",
    response_model=ApiResponse[SkillFactBatchReviewResult],
)
async def batch_review_facts(
    payload: SkillFactBatchReviewRequest,
    principal: TokenPrincipal = Depends(require_admin),
    service: SkillService = Depends(get_skill_service),
    task_service: GraphTaskService = Depends(get_graph_task_service),
) -> ApiResponse[SkillFactBatchReviewResult]:
    fact_ids, skipped = await service.review_facts(
        fact_ids=payload.fact_ids,
        keyword=None,
        decision=payload.decision,
        note=payload.note,
        reviewer_id=principal.user_id,
    )
    message = f"已批量处理 {len(fact_ids)} 条技能事实"
    task = await _auto_sync_graph_after_review(
        processed=len(fact_ids),
        decision=payload.decision,
        principal=principal,
        task_service=task_service,
    )
    if task is not None:
        message += f"；已自动触发图谱增量同步（任务 {task.task_id[:8]}）"
    return ApiResponse(
        message=message,
        data=SkillFactBatchReviewResult(
            processed_count=len(fact_ids), skipped_count=skipped, fact_ids=fact_ids
        ),
    )


@router.post(
    "/facts/reviews/approve-all",
    response_model=ApiResponse[SkillFactBatchReviewResult],
)
async def approve_all_fact_reviews(
    payload: SkillFactApproveAllRequest,
    principal: TokenPrincipal = Depends(require_admin),
    service: SkillService = Depends(get_skill_service),
    task_service: GraphTaskService = Depends(get_graph_task_service),
) -> ApiResponse[SkillFactBatchReviewResult]:
    fact_ids, _ = await service.review_facts(
        fact_ids=None,
        keyword=payload.keyword,
        decision=VerificationStatus.verified,
        note="管理员一键同意",
        reviewer_id=principal.user_id,
    )
    message = f"已同意 {len(fact_ids)} 条待审核技能事实"
    task = await _auto_sync_graph_after_review(
        processed=len(fact_ids),
        decision=VerificationStatus.verified,
        principal=principal,
        task_service=task_service,
    )
    if task is not None:
        message += f"；已自动触发图谱增量同步（任务 {task.task_id[:8]}）"
    return ApiResponse(
        message=message,
        data=SkillFactBatchReviewResult(
            processed_count=len(fact_ids), skipped_count=0, fact_ids=fact_ids
        ),
    )


@router.get("/{skill_id}", response_model=ApiResponse[SkillSummary])
async def get_skill(
    skill_id: int,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
) -> ApiResponse[SkillSummary]:
    return ApiResponse(data=await service.get_skill(skill_id))
