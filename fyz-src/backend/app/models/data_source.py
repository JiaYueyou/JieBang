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
