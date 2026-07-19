"""
简历模型 —— 用户上传或手动创建的简历，包含教育/工作/项目经历。
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Resume(Base):
    """简历主表"""
    __tablename__ = "resume"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, comment="所属用户ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="简历别名，用户自定义")
    target_position: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="目标岗位方向")
    # 个人信息
    personal_name: Mapped[str] = mapped_column(String(50), default="", comment="姓名")
    personal_email: Mapped[str] = mapped_column(String(100), default="", comment="邮箱")
    personal_phone: Mapped[str] = mapped_column(String(20), default="", comment="手机号")
    personal_location: Mapped[str] = mapped_column(String(50), default="", comment="所在地")
    # 求职意向
    desired_position: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="期望职位")
    desired_city: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="期望城市")
    salary_expectation: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="期望薪资")
    work_mode: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="工作模式: fulltime/intern/remote")
    # 自我评价
    self_evaluation: Mapped[str] = mapped_column(Text, default="", comment="自我评价")
    # 来源文件
    source_file: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="上传的原始文件名")
    # 关联的列表数据
    education_list: Mapped[list] = mapped_column(JSON, default=list, comment="教育经历列表")
    work_experience_list: Mapped[list] = mapped_column(JSON, default=list, comment="工作经历列表")
    project_list: Mapped[list] = mapped_column(JSON, default=list, comment="项目经历列表")
    skill_list: Mapped[list] = mapped_column(JSON, default=list, comment="技能列表")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


# 以下三个类仅用于类型标注，实际数据以 JSON 形式存储在 Resume 表中
class Education:
    """教育经历（JSON 存储结构）"""
    school: str; degree: str; major: str; startDate: str; endDate: str


class WorkExperience:
    """工作经历（JSON 存储结构）"""
    company: str; position: str; startDate: str; endDate: str
    description: str; skills: list[str]


class Project:
    """项目经历（JSON 存储结构）"""
    name: str; role: str; description: str
    technologies: list[str]; highlights: list[str]
