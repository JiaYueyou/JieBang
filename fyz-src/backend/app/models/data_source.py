"""数据源配置模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    Boolean,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataSource(Base):
    """数据源配置表"""

    __tablename__ = "data_source"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="数据源名称")
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="类型：zhaopin / iflytek / other")
    entry_url: Mapped[str | None] = mapped_column(String(500), comment="入口地址")
    description: Mapped[str | None] = mapped_column(String(500), comment="描述")

    # 调度
    schedule_expression: Mapped[str | None] = mapped_column(String(100), comment="cron 表达式")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 抓取配置（JSON，存储爬虫配置参数）
    crawl_config: Mapped[dict | None] = mapped_column(JSON, comment="抓取配置 JSON")

    # 运行状态
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, comment="最后运行时间")
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime, index=True, comment="最后成功时间"
    )
    last_error: Mapped[str | None] = mapped_column(Text, comment="最近失败摘要")
    freshness_slo_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2880, comment="数据新鲜度 SLO（分钟）"
    )
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, comment="下次运行时间")
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="连续失败次数")

    # 记录
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<DataSource id={self.id} name={self.name!r} type={self.source_type}>"


class PipelineRun(Base):
    """Persistent audit record for one end-to-end data refresh.

    The scheduler and the manual API both write this table.  A unique
    idempotency key makes periodic execution safe when more than one API
    worker is running.
    """

    __tablename__ = "pipeline_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    trigger: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(40), nullable=False, default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requested_sources: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    stage_results: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    quality_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[int | None] = mapped_column(Integer, index=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
