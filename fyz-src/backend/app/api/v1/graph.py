"""Neo4j 能力图谱同步、快照与查询 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.graph import GraphSnapshotResponse, GraphSubgraph, GraphSyncRequest
from app.schemas.skill import TaskStatusResponse
from app.services import GraphService, GraphTaskService

router = APIRouter(prefix="/graph", tags=["技能图谱"])


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


@router.get("/nodes/{node_id}", response_model=ApiResponse[GraphSubgraph])
async def node_detail(
    node_id: str,
    _principal: TokenPrincipal = Depends(get_current_user),
    service: GraphService = Depends(get_graph_service),
):
    return ApiResponse(data=await service.node(node_id))


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
