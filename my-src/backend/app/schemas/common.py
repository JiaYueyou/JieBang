"""统一响应 Schema"""

from typing import Any, Optional
from pydantic import BaseModel


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None
    meta: Optional[PageMeta] = None
