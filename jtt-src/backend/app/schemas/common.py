"""
通用响应 Schema —— 统一的 API 响应格式和分页结构。
"""
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应包装"""
    code: int = 200
    message: str = "success"
    data: T | None = None


class PaginatedData(BaseModel, Generic[T]):
    """分页数据"""
    items: list[T] = Field(default_factory=list, alias="list")
    total: int = 0
    page: int = 1
    page_size: int = 20

    model_config = {"populate_by_name": True}
