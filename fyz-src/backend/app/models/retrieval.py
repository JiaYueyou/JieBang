"""Authoritative evidence and rebuildable retrieval index metadata."""

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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunk"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_skill_fact_id: Mapped[int] = mapped_column(
        ForeignKey("job_skill_fact.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_job_record_id: Mapped[int] = mapped_column(
        ForeignKey("raw_job_record.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    standard_job_id: Mapped[int] = mapped_column(
        ForeignKey("standard_job.id"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skill.id"),
        nullable=False,
        index=True,
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    source_platform: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    content_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    near_duplicate_group_id: Mapped[str | None] = mapped_column(
        String(40),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class RetrievalIndexVersion(Base):
    __tablename__ = "retrieval_index_version"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    backend: Mapped[str] = mapped_column(String(40), nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    chunking_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        index=True,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class RetrievalIndexEntry(Base):
    __tablename__ = "retrieval_index_entry"
    __table_args__ = (
        UniqueConstraint(
            "index_version_id",
            "evidence_id",
            name="uq_retrieval_index_entry_version_evidence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    index_version_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_index_version.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_chunk.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    embedding_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    lexical_text: Mapped[str] = mapped_column(Text, nullable=False)
    backend_document_id: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class RetrievalQueryLog(Base):
    __tablename__ = "retrieval_query_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    index_version_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_index_version.id"),
        nullable=False,
        index=True,
    )
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    query_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    filters_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    result_evidence_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AgentClaimCitation(Base):
    __tablename__ = "agent_claim_citation"
    __table_args__ = (
        UniqueConstraint(
            "agent_run_id",
            "claim_id",
            "evidence_id",
            name="uq_agent_claim_citation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_run.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_id: Mapped[str] = mapped_column(String(80), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_chunk.id"),
        nullable=False,
        index=True,
    )
    grounding_score: Mapped[float] = mapped_column(Float, nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
