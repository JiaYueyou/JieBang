"""Persisted resumes, deterministic match snapshots, and traceable evidence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Resume(Base):
    __tablename__ = "resume"
    __table_args__ = (UniqueConstraint("created_by", "content_hash", name="uq_resume_owner_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    current_position: Mapped[str | None] = mapped_column(String(120))
    experience: Mapped[str | None] = mapped_column(String(100))
    education: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100))
    company: Mapped[str | None] = mapped_column(String(150))
    location: Mapped[str | None] = mapped_column(String(100))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str | None] = mapped_column(String(120))
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    parse_result: Mapped["ResumeParseResult"] = relationship(back_populates="resume", cascade="all, delete-orphan", lazy="selectin")
    skills: Mapped[list["ResumeSkill"]] = relationship(back_populates="resume", cascade="all, delete-orphan", lazy="selectin")
    matches: Mapped[list["MatchRecord"]] = relationship(back_populates="resume", cascade="all, delete-orphan", lazy="selectin")


class ResumeParseResult(Base):
    __tablename__ = "resume_parse_result"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resume.id", ondelete="CASCADE"), nullable=False, unique=True)
    parsed_text: Mapped[str] = mapped_column(Text, nullable=False)
    profile: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    resume: Mapped[Resume] = relationship(back_populates="parse_result")


class ResumeSkill(Base):
    __tablename__ = "resume_skill"
    __table_args__ = (UniqueConstraint("resume_id", "canonical_key", name="uq_resume_skill_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resume.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    extraction_method: Mapped[str] = mapped_column(String(20), nullable=False, default="rule")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    resume: Mapped[Resume] = relationship(back_populates="skills")


class MatchRecord(Base):
    __tablename__ = "match_record"
    __table_args__ = (UniqueConstraint("resume_id", "job_id", "algorithm_version", name="uq_match_snapshot"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resume.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_posting.id", ondelete="CASCADE"), nullable=False, index=True)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    explanation_agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_run.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    resume: Mapped[Resume] = relationship(back_populates="matches")
    job: Mapped["JobPosting"] = relationship(lazy="selectin")
    evidence: Mapped[list["MatchEvidence"]] = relationship(back_populates="match", cascade="all, delete-orphan", lazy="selectin")


class MatchEvidence(Base):
    __tablename__ = "match_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match_record.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    match: Mapped[MatchRecord] = relationship(back_populates="evidence")


from app.models.job import JobPosting  # noqa: E402,F401
