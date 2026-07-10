"""岗位洞察人工决策审计模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisInsightDecision(Base):
    __tablename__ = "analysis_insight_decision"
    __table_args__ = (
        UniqueConstraint(
            "insight_type", "target_id", "created_by", name="uq_analysis_decision_user_target"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    insight_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
