"""
岗位相关 API —— 岗位列表、详情、知识图谱数据。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.position_service import PositionService
from app.schemas.position import (
    JobPositionResponse, GraphResponse,
)
from app.schemas.common import ApiResponse, PaginatedData

router = APIRouter(prefix="/positions", tags=["岗位"])


def get_position_service(db: AsyncSession = Depends(get_db)) -> PositionService:
    """依赖注入：创建岗位服务实例"""
    return PositionService(db)


@router.get("", response_model=ApiResponse[PaginatedData[JobPositionResponse]])
async def list_positions(
    category: str | None = Query(None, description="岗位类型: new / existing"),
    keyword: str | None = Query(None, description="搜索关键词"),
    tech_stack: str | None = Query(None, description="技术栈筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: PositionService = Depends(get_position_service),
):
    """分页查询岗位列表，支持分类、关键词、技术栈筛选"""
    result = await service.list_positions({
        "category": category, "keyword": keyword,
        "tech_stack": tech_stack, "page": page, "page_size": page_size,
    })
    return ApiResponse(data=result)


@router.get("/graph", response_model=ApiResponse[GraphResponse])
async def get_knowledge_graph(
    root_tech: str | None = Query(None, description="根技术筛选，如 Java"),
    service: PositionService = Depends(get_position_service),
):
    """获取知识图谱数据（五级节点 + 边）"""
    data = await service.get_graph_data(root_tech)
    return ApiResponse(data=data)


@router.get("/{position_id}", response_model=ApiResponse[JobPositionResponse])
async def get_position_detail(
    position_id: int,
    service: PositionService = Depends(get_position_service),
):
    """获取岗位详情，含技能要求和变化历史"""
    detail = await service.get_detail(position_id)
    return ApiResponse(data=detail)
