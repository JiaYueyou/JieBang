"""标准技能、来源证据、抽取事实、Agent 与异步任务模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utc_now


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    graph_node_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class SourceDocument(Base):
    __tablename__ = "source_document"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255))
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    content_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class RawJobRecord(Base):
    __tablename__ = "raw_job_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_document.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    standardized_title: Mapped[str | None] = mapped_column(String(255), index=True)
    company: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    salary_text: Mapped[str | None] = mapped_column(String(100))
    experience_text: Mapped[str | None] = mapped_column(String(100))
    education_text: Mapped[str | None] = mapped_column(String(100))
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[str] = mapped_column(Text, nullable=False, default="")
    requirements: Mapped[str] = mapped_column(Text, nullable=False, default="")
    keywords: Mapped[str] = mapped_column(Text, nullable=False, default="")
    posted_at_text: Mapped[str | None] = mapped_column(String(100))
    crawled_at_text: Mapped[str | None] = mapped_column(String(100))
    dedup_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unique")
    normalized_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    source_document: Mapped[SourceDocument] = relationship(lazy="selectin")


class JobSkillFact(Base):
    __tablename__ = "job_skill_fact"
    __table_args__ = (
        UniqueConstraint("job_id", "skill_id", name="uq_job_skill_fact"),
        UniqueConstraint("raw_job_record_id", "skill_id", name="uq_raw_job_skill_fact"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("job_posting.id", ondelete="CASCADE"), index=True)
    raw_job_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_job_record.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    extraction_method: Mapped[str] = mapped_column(String(20), nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_run.id"))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    skill: Mapped[Skill] = relationship(lazy="selectin")


class AgentRun(Base):
    __tablename__ = "agent_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    structured_output: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AsyncTask(Base):
    __tablename__ = "async_task"
    __table_args__ = (
        UniqueConstraint(
            "created_by", "task_type", "idempotency_key",
            name="uq_async_task_idempotency",
        ),
    )
    __table_args__ = (
        UniqueConstraint(
            "created_by", "task_type", "idempotency_key",
            name="uq_async_task_idempotency",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[dict | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
