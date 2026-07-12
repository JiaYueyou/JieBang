"""
岗位模型 —— 新岗位和既有岗位，包含技能要求、技能变化历史。
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Float, Text, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class JobPosition(Base):
    """岗位表 —— 新岗位和既有岗位统一存储"""
    __tablename__ = "job_position"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="岗位名称")
    category: Mapped[str] = mapped_column(String(20), nullable=False, comment="岗位类型: new=新岗位, existing=既有岗位")
    aliases: Mapped[list] = mapped_column(JSON, default=list, comment="岗位别名列表")
    summary: Mapped[str] = mapped_column(Text, nullable=False, comment="岗位概述")
    responsibilities: Mapped[list] = mapped_column(JSON, default=list, comment="核心职责列表")
    industry_scenarios: Mapped[list] = mapped_column(JSON, default=list, comment="典型行业应用场景")
    tech_stack: Mapped[list] = mapped_column(JSON, default=list, comment="技术栈列表")
    career_level: Mapped[str] = mapped_column(String(20), default="mid", comment="职业级别: junior/mid/senior")
    salary_range: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="薪资范围，如 15K-30K")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联的技能和变化历史
    required_skills: Mapped[list["Skill"]] = relationship(
        "Skill", back_populates="position", cascade="all, delete-orphan",
        primaryjoin="and_(JobPosition.id==Skill.position_id, Skill.kind=='required')",
        viewonly=True,
    )
    preferred_skills: Mapped[list["Skill"]] = relationship(
        "Skill", back_populates="position", cascade="all, delete-orphan",
        primaryjoin="and_(JobPosition.id==Skill.position_id, Skill.kind=='preferred')",
        viewonly=True,
    )
    skill_changes: Mapped[list["SkillChange"]] = relationship(
        "SkillChange", back_populates="position", cascade="all, delete-orphan",
    )


class Skill(Base):
    """技能表 —— 岗位要求的必备/加分技能"""
    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("job_position.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="技能名称")
    level: Mapped[str] = mapped_column(String(20), default="required", comment="重要性: required/preferred/advanced")
    kind: Mapped[str] = mapped_column(String(20), default="required", comment="类型: required=必备, preferred=加分")
    category: Mapped[str] = mapped_column(String(50), default="", comment="技术栈分类，如后端/前端/AI")

    position: Mapped["JobPosition"] = relationship("JobPosition", back_populates="required_skills")


class SkillChange(Base):
    """技能变化历史 —— 既有岗位的能力项变化记录"""
    __tablename__ = "skill_change"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("job_position.id"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="变化的技能名")
    change_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="变化类型: added/removed/modified")
    description: Mapped[str] = mapped_column(Text, default="", comment="变化说明")
    source: Mapped[str] = mapped_column(String(200), default="", comment="数据来源")
    change_date: Mapped[str] = mapped_column(String(20), default="", comment="变化日期，如 2026-06")

    position: Mapped["JobPosition"] = relationship("JobPosition", back_populates="skill_changes")
