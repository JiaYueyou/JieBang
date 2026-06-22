"""岗位发布、技能与版本模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
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


class JobPosting(Base):
    __tablename__ = "job_posting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    standardized_title: Mapped[str | None] = mapped_column(String(120), index=True)
    level: Mapped[str] = mapped_column(String(30), nullable=False, default="mid")
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    company: Mapped[str | None] = mapped_column(String(150))
    location: Mapped[str | None] = mapped_column(String(100), index=True)
    experience: Mapped[str | None] = mapped_column(String(50))
    education: Mapped[str | None] = mapped_column(String(50))
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_months: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    responsibilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    requirements: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    skills: Mapped[list["JobPostingSkill"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="JobPostingSkill.sort_order",
    )
    versions: Mapped[list["JobPostingVersion"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="JobPostingVersion.version_no",
    )


class JobPostingSkill(Base):
    __tablename__ = "job_posting_skill"
    __table_args__ = (
        UniqueConstraint("job_id", "name", "kind", name="uq_job_skill_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_posting.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    job: Mapped[JobPosting] = relationship(back_populates="skills")


class JobPostingVersion(Base):
    __tablename__ = "job_posting_version"
    __table_args__ = (
        UniqueConstraint("job_id", "version_no", name="uq_job_version_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_posting.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    change_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    job: Mapped[JobPosting] = relationship(back_populates="versions")
