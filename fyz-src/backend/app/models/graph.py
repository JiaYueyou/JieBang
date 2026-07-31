"""标准岗位、图谱快照、同步批次与深层补全候选。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StandardJob(Base):
    __tablename__ = "standard_job"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(220), nullable=False, unique=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    stack: Mapped[str] = mapped_column(String(30), nullable=False, default="backend", index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="middle", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class StandardJobSource(Base):
    __tablename__ = "standard_job_source"
    __table_args__ = (UniqueConstraint("source_type", "source_id", name="uq_standard_job_source"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    standard_job_id: Mapped[int] = mapped_column(ForeignKey("standard_job.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    original_title: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class GraphSnapshot(Base):
    __tablename__ = "graph_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    snapshot_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class GraphSyncBatch(Base):
    __tablename__ = "graph_sync_batch"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    async_task_id: Mapped[str | None] = mapped_column(ForeignKey("async_task.id"), unique=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("graph_snapshot.id"), nullable=False, index=True)
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class GraphEnrichmentCandidate(Base):
    __tablename__ = "graph_enrichment_candidate"
    __table_args__ = (UniqueConstraint("snapshot_id", "skill_id", name="uq_graph_candidate_snapshot_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("graph_snapshot.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"), nullable=False, index=True)
    candidate_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Historical column name retained for compatibility; values are stable
    # Phase 2 EvidenceChunk IDs from Phase 3 onward.
    evidence_source_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unverified", index=True)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_run.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
