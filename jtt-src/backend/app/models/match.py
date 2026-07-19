"""
匹配模型 —— 人岗匹配结果，包含各维度评分、差距分析、优化建议。
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Float, Text, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class MatchResult(Base):
    """匹配结果主表"""
    __tablename__ = "match_result"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, comment="用户ID")
    resume_id: Mapped[int] = mapped_column(ForeignKey("resume.id"), nullable=False, comment="简历ID")
    position_id: Mapped[int] = mapped_column(ForeignKey("job_position.id"), nullable=False, comment="岗位ID")
    position_name: Mapped[str] = mapped_column(String(100), default="", comment="岗位名称（冗余，方便查询）")
    resume_name: Mapped[str] = mapped_column(String(100), default="", comment="简历名称（冗余）")
    total_score: Mapped[int] = mapped_column(Integer, default=0, comment="综合匹配分数 0-100")
    # 各维度评分和差距分析以 JSON 存储
    dimensions: Mapped[list] = mapped_column(JSON, default=list, comment="各维度评分列表")
    gap_analysis: Mapped[dict] = mapped_column(JSON, default=dict, comment="差距分析结果")
    suggestions: Mapped[list] = mapped_column(JSON, default=list, comment="优化建议列表")
    match_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="匹配时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# 以下为 JSON 存储结构的类型说明，不映射数据库表
class MatchDimension:
    """匹配维度（JSON 存储）"""
    name: str        # 维度名称: 技能匹配/经验匹配/学历匹配/综合素质
    score: int       # 0-100 分
    weight: float    # 权重
    details: str     # 详细说明


class GapAnalysis:
    """差距分析（JSON 存储）"""
    missingSkills: list  # 完全缺失的技能
    weakSkills: list     # 薄弱技能
    matchSkills: list    # 已匹配技能


class ImprovementSuggestion:
    """优化建议（JSON 存储）"""
    id: str              # 建议ID
    section: str         # 简历模块: skills/workExperience/education/selfEvaluation
    field: str           # 具体字段
    original: str        # 原文
    suggested: str       # 建议修改为
    reason: str          # 修改理由
    changeType: str      # small=小改, large=大改
    accepted: bool       # 用户是否接受
    verified: bool       # 是否通过图谱校验防幻觉
    warning: str | None  # 校验警告信息
