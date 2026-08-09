"""岗位洞察人工决策审计模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
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


class AnalysisBaselineSnapshot(Base):
    """冻结的趋势分析历史基线。仅 active 版本可参与新兴技能判定。"""

    __tablename__ = "analysis_baseline_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    source_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    quality_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AnalysisBaselineSkill(Base):
    """某冻结基线中的技能覆盖和成熟度统计。"""

    __tablename__ = "analysis_baseline_skill"
    __table_args__ = (
        UniqueConstraint(
            "baseline_id", "skill_id", "segment_key",
            name="uq_analysis_baseline_skill_segment",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    baseline_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_baseline_snapshot.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"), nullable=False, index=True)
    segment_key: Mapped[str] = mapped_column(String(160), nullable=False, default="all")
    cluster_count: Mapped[int] = mapped_column(Integer, nullable=False)
    company_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    active_period_count: Mapped[int] = mapped_column(Integer, nullable=False)
    prevalence: Mapped[float] = mapped_column(Float, nullable=False)
    maturity_stage: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    evidence_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
