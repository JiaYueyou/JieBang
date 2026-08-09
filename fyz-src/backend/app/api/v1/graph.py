"""Neo4j 能力图谱同步、快照与查询 API。"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.graph import (
    GraphEnrichmentBatchRejectResponse,
    GraphEnrichmentCandidatePage,
    GraphEnrichmentCandidateResponse,
    GraphEnrichmentPublishRequest,
    GraphEnrichmentReviewRequest,
    GraphSnapshotResponse,
    GraphSubgraph,
    GraphSyncRequest,
)
from app.schemas.skill import TaskStatusResponse
from app.services import GraphService, GraphTaskService

router = APIRouter(prefix="/graph", tags=["技能图谱"])
logger = logging.getLogger(__name__)


def get_graph_service(db: AsyncSession = Depends(get_db)) -> GraphService:
    return GraphService(db)


def get_graph_task_service(db: AsyncSession = Depends(get_db)) -> GraphTaskService:
    return GraphTaskService(db)


@router.get("/", response_model=ApiResponse[dict])
async def graph_home(
    _principal: TokenPrincipal = Depends(get_current_user),
):
    return ApiResponse(data={"message": "技能图谱", "status": "ready"})


@router.post("/sync", response_model=ApiResponse[TaskStatusResponse])
async def sync_graph(
    payload: GraphSyncRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    service: GraphTaskService = Depends(get_graph_task_service),
):
    task = await service.create_sync(
        mode=payload.mode.value,
        enrich_top_skills=payload.enrich_top_skills,
        user_id=principal.user_id,
        run_eager_in_background=True,
    )
    logger.info(
        "graph_sync_created task_id=%s mode=%s enrich=%s user_id=%s",
        task.task_id, payload.mode.value, payload.enrich_top_skills, principal.user_id,
    )
    return ApiResponse(message="图谱同步任务已创建", data=task)


@router.get("/snapshots", response_model=ApiResponse[list[GraphSnapshotResponse]])
async def list_snapshots(
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.list_snapshots())


@router.get("/snapshots/{snapshot_id}", response_model=ApiResponse[GraphSnapshotResponse])
async def get_snapshot(
    snapshot_id: str,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.get_snapshot(snapshot_id))


@router.post("/enrichment/generate", response_model=ApiResponse[TaskStatusResponse])
async def generate_enrichment_candidates(
    principal: TokenPrincipal = Depends(require_admin),
    service: GraphTaskService = Depends(get_graph_task_service),
):
    task = await service.create_sync(
        mode="incremental", enrich_top_skills=True, user_id=principal.user_id,
        run_eager_in_background=True,
    )
    logger.info("graph_enrichment_created task_id=%s user_id=%s", task.task_id, principal.user_id)
    return ApiResponse(message="L4/L5 候选生成任务已创建", data=task)


@router.get(
    "/enrichment/candidates",
    response_model=ApiResponse[GraphEnrichmentCandidatePage],
)
async def list_enrichment_candidates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    review_status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    _principal: TokenPrincipal = Depends(require_admin),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.list_enrichment_candidates(
        page=page, page_size=page_size, review_status=review_status,
    ))


@router.patch(
    "/enrichment/candidates/{candidate_id}/review",
    response_model=ApiResponse[GraphEnrichmentCandidateResponse],
)
async def review_enrichment_candidate(
    candidate_id: int,
    payload: GraphEnrichmentReviewRequest,
    principal: TokenPrincipal = Depends(require_admin),
    service: GraphService = Depends(get_graph_service),
    task_service: GraphTaskService = Depends(get_graph_task_service),
):
    candidate = await service.review_enrichment_candidate(
        candidate_id, action=payload.action, note=payload.note,
        lock_version=payload.lock_version, user_id=principal.user_id,
    )
    message = "候选已批准" if payload.action == "approve" else "候选已驳回"
    if payload.action == "approve":
        # 批准后即发布：将候选置为可发布，并自动触发 L4/L5 增量写 Neo4j
        # （进程内异步，不依赖 Celery；_append_verified_deep_nodes 会读取
        #   publication_status=approved 的候选写入 TechPoint/KnowledgePoint）
        await service.prepare_enrichment_publication([candidate_id])
        task = await task_service.create_sync_in_background(
            mode="incremental", enrich_top_skills=False, user_id=principal.user_id,
        )
        message += f"；已自动触发 L4/L5 图谱发布（任务 {task.task_id[:8]}）"
    return ApiResponse(message=message, data=candidate)


@router.post(
    "/enrichment/candidates/reject-machine-failed",
    response_model=ApiResponse[GraphEnrichmentBatchRejectResponse],
)
async def reject_machine_failed_candidates(
    principal: TokenPrincipal = Depends(require_admin),
    service: GraphService = Depends(get_graph_service),
):
    candidate_ids = await service.reject_machine_failed_candidates(
        user_id=principal.user_id
    )
    return ApiResponse(
        message=f"已自动驳回 {len(candidate_ids)} 条机器未通过候选",
        data=GraphEnrichmentBatchRejectResponse(
            rejected_count=len(candidate_ids), candidate_ids=candidate_ids
        ),
    )


@router.post("/enrichment/publish", response_model=ApiResponse[TaskStatusResponse])
async def publish_enrichment_candidates(
    payload: GraphEnrichmentPublishRequest,
    principal: TokenPrincipal = Depends(require_admin),
    graph_service: GraphService = Depends(get_graph_service),
    task_service: GraphTaskService = Depends(get_graph_task_service),
):
    count = await graph_service.prepare_enrichment_publication(payload.candidate_ids)
    task = await task_service.create_sync(
        mode="incremental", enrich_top_skills=False, user_id=principal.user_id,
        run_eager_in_background=True,
    )
    logger.info(
        "graph_publication_created task_id=%s candidate_count=%d user_id=%s",
        task.task_id, count, principal.user_id,
    )
    return ApiResponse(message=f"{count} 条已批准候选进入图谱发布任务", data=task)


@router.get("/panorama", response_model=ApiResponse[GraphSubgraph])
async def panorama(
    stack: str | None = None,
    level: str | None = None,
    node_type: str | None = None,
    keyword: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=1000, ge=1, le=1000),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.panorama(
        stack=stack, level=level, node_type=node_type, keyword=keyword, limit=limit
    ))


@router.get("/overview", response_model=ApiResponse[GraphSubgraph])
async def graph_overview(
    cursor: str | None = Query(default=None, max_length=120),
    page_size: int = Query(default=24, ge=1, le=60),
    max_layer: int = Query(default=3, ge=1, le=3),
    stack: str | None = None,
    level: str | None = None,
    keyword: str | None = Query(default=None, max_length=120),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.overview(
        cursor=cursor, page_size=page_size, max_layer=max_layer,
        stack=stack, level=level, keyword=keyword,
    ))


@router.get("/nodes/{node_id}", response_model=ApiResponse[GraphSubgraph])
async def node_detail(
    node_id: str,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.node(node_id))


@router.get("/nodes/{node_id}/neighbors", response_model=ApiResponse[GraphSubgraph])
async def node_neighbors(
    node_id: str,
    cursor: str | None = Query(default=None, max_length=120),
    page_size: int = Query(default=40, ge=1, le=100),
    max_layer: int = Query(default=3, ge=1, le=5),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.neighbors(
        node_id, cursor=cursor, page_size=page_size, max_layer=max_layer,
    ))


@router.get("/expand", response_model=ApiResponse[GraphSubgraph])
async def expand(
    node_id: str,
    depth: int = Query(default=2, ge=1, le=5),
    limit: int = Query(default=300, ge=1, le=500),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.expand(node_id, depth, limit))


@router.get("/search", response_model=ApiResponse[GraphSubgraph])
async def search(
    q: str = Query(min_length=1, max_length=120),
    types: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.search(q, types, limit))


@router.get("/path", response_model=ApiResponse[GraphSubgraph])
async def path(
    from_id: str,
    to_id: str,
    max_depth: int = Query(default=6, ge=1, le=6),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.path(from_id, to_id, max_depth))


@router.get("/jobs/{job_id}/tree", response_model=ApiResponse[GraphSubgraph])
async def job_tree(
    job_id: int,
    depth: int = Query(default=5, ge=1, le=5),
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.job_tree(job_id, depth))
