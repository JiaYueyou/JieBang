"""
用户模型 —— 系统用户表，存储登录凭证和个人信息。
"""
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="邮箱")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    # 个人信息字段
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="昵称")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="手机号")
    city: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="所在城市")
    education: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最高学历")
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="头像URL")
    # 统计字段
    resume_count: Mapped[int] = mapped_column(default=0, comment="简历数量")
    match_history_count: Mapped[int] = mapped_column(default=0, comment="匹配历史次数")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
