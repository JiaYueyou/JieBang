"""
收藏模型 —— 用户收藏的岗位、学习资料、错题、AI知识点。
使用统一的 item_type + item_id + metadata 结构支持多种收藏类型。
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
class Favorite(Base):
    """用户收藏表（多态设计）"""
    __tablename__ = "favorite"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, comment="用户ID")
    item_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
        comment="收藏类型: position / learning_resource / quiz_error / knowledge_point"
    )
    item_id: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="对应类型的资源ID"
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="收藏项标题")
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="简要描述")
    item_data: Mapped[dict] = mapped_column("metadata", JSON, default=dict, comment="完整数据快照")
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="用户自定义标签")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="收藏时间")
