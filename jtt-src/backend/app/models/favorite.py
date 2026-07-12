"""
收藏模型 —— 用户收藏的岗位。
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Favorite(Base):
    """用户岗位收藏表"""
    __tablename__ = "favorite"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, comment="用户ID")
    position_id: Mapped[int] = mapped_column(ForeignKey("job_position.id"), nullable=False, comment="岗位ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="收藏时间")
