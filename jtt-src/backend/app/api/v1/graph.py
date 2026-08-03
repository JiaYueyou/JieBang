"""Neo4j 能力图谱查询 API。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.graph import GraphSubgraph
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["技能图谱"])


def get_graph_service(db: AsyncSession = Depends(get_db)) -> GraphService:
    return GraphService(db)


@router.get("/panorama", response_model=ApiResponse[GraphSubgraph])
async def panorama(
    stack: str | None = None,
    level: str | None = None,
    node_type: str | None = None,
    keyword: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=1000, ge=1, le=1000),
    service: GraphService = Depends(get_graph_service),
):
    """全量图谱（支持按技术栈/级别/类型/关键词过滤）"""
    return ApiResponse(data=await service.panorama(
        stack=stack, level=level, node_type=node_type,
        keyword=keyword, limit=limit,
    ))


@router.get("/nodes/{node_id}", response_model=ApiResponse[GraphSubgraph])
async def node_detail(
    node_id: str,
    service: GraphService = Depends(get_graph_service),
):
    """节点详情 + 1-hop 邻居"""
    return ApiResponse(data=await service.get_node(node_id))


@router.get("/expand", response_model=ApiResponse[GraphSubgraph])
async def expand(
    node_id: str,
    depth: int = Query(default=2, ge=1, le=5),
    limit: int = Query(default=300, ge=1, le=500),
    service: GraphService = Depends(get_graph_service),
):
    """从指定节点 BFS 展开子图"""
    return ApiResponse(data=await service.expand(node_id, depth, limit))


@router.get("/search", response_model=ApiResponse[GraphSubgraph])
async def search(
    q: str = Query(min_length=1, max_length=120),
    types: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    service: GraphService = Depends(get_graph_service),
):
    """关键词搜索图谱节点"""
    return ApiResponse(data=await service.search(q, types, limit))


@router.get("/path", response_model=ApiResponse[GraphSubgraph])
async def path(
    from_id: str,
    to_id: str,
    max_depth: int = Query(default=6, ge=1, le=6),
    service: GraphService = Depends(get_graph_service),
):
    """两节点间最短路径"""
    return ApiResponse(data=await service.path(from_id, to_id, max_depth))


@router.get("/jobs/{job_id}/tree", response_model=ApiResponse[GraphSubgraph])
async def job_tree(
    job_id: int,
    depth: int = Query(default=5, ge=1, le=5),
    service: GraphService = Depends(get_graph_service),
):
    """岗位完整技能树"""
    return ApiResponse(data=await service.job_tree(job_id, depth))
