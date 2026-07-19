"""
收藏相关 Schema —— 支持多类型收藏（岗位/学习资料/错题/AI知识点）。
"""
from pydantic import BaseModel, Field


class FavoriteCreate(BaseModel):
    """添加收藏请求"""
    item_type: str = Field(..., description="类型: position / learning_resource / quiz_error / knowledge_point")
    item_id: str = Field(..., description="资源ID")
    title: str = Field(..., max_length=200, description="标题")
    summary: str | None = Field(None, max_length=500, description="简要描述")
    metadata: dict | None = Field(None, description="完整数据快照")
    tags: list[str] | None = Field(None, description="用户自定义标签")


class FavoriteResponse(BaseModel):
    """收藏项响应"""
    id: int
    item_type: str
    item_id: str
    title: str
    summary: str | None = None
    metadata: dict | None = None
    tags: list[str] | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True
