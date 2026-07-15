"""企业内部人才流动领域模型，与公开招聘数据严格隔离。"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EnterpriseTalent(Base):
    __tablename__ = "enterprise_talent"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    current_position: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[str] = mapped_column(String(30), nullable=False, default="mid")
    location: Mapped[str | None] = mapped_column(String(100))
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position_tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    project_highlights: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class EnterpriseEmployeeDirectory(Base):
    """企业员工主数据目录，作为人才池录入的数据源。"""

    __tablename__ = "enterprise_employee_directory"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    current_position: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[str] = mapped_column(String(30), nullable=False, default="mid")
    location: Mapped[str | None] = mapped_column(String(100))
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position_tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    project_highlights: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="hr_sync")
    synced_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class InternalPosition(Base):
    __tablename__ = "internal_position"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    standardized_title: Mapped[str | None] = mapped_column(String(120), index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    receiving_manager: Mapped[str | None] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(30), nullable=False, default="mid")
    headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    open_reason: Mapped[str] = mapped_column(String(300), nullable=False, default="组织人才配置")
    responsibilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    requirements: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    trainable_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    transfer_profile: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    manager_confirmations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    min_tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_position_tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    allowed_departments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    restrictions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    target_start_date: Mapped[date | None] = mapped_column(Date)
    open_from: Mapped[date | None] = mapped_column(Date)
    open_until: Mapped[date | None] = mapped_column(Date)
    internal_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class TransferRuleSet(Base):
    __tablename__ = "transfer_rule_set"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    min_tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_position_tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_match_score: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    skill_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=85)
    tenure_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class TransferDecision(Base):
    __tablename__ = "transfer_decision"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    talent_id: Mapped[int] = mapped_column(ForeignKey("enterprise_talent.id"), nullable=False, index=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("internal_position.id"), nullable=False, index=True)
    match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rule_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="confirmed", index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
