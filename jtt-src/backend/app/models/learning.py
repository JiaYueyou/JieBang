"""
学习路径模型 —— 用户的学习计划，包含步骤和资源推荐。
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LearningPath(Base):
    """学习路径主表"""
    __tablename__ = "learning_path"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, comment="用户ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="路径名称")
    position_id: Mapped[int] = mapped_column(ForeignKey("job_position.id"), nullable=False, comment="目标岗位ID")
    position_name: Mapped[str] = mapped_column(String(100), default="", comment="目标岗位名称")
    # 步骤和资源以 JSON 存储
    steps: Mapped[list] = mapped_column(JSON, default=list, comment="学习步骤列表")
    total_duration: Mapped[str] = mapped_column(String(50), default="", comment="总学习时长，如 12周")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class LearningStep:
    """学习步骤（JSON 存储结构）"""
    id: str; order: int
    title: str; description: str; duration: str
    resources: list  # LearningResource[]
    completed: bool


class LearningResource:
    """学习资源（JSON 存储结构）"""
    id: str; title: str
    type: str  # course/book/article/project/video
    url: str; platform: str
