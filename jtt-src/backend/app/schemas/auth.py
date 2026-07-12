"""
认证相关 Schema —— 登录、注册、个人信息。
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=100, description="密码")


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., max_length=100, description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class TokenResponse(BaseModel):
    """登录/注册成功后返回的 token 信息"""
    token: str = Field(..., description="JWT token")
    user: "UserProfileResponse"


class UserProfileResponse(BaseModel):
    """用户个人信息"""
    id: int
    username: str
    email: str
    nickname: str | None = None
    phone: str | None = None
    city: str | None = None
    education: str | None = None
    avatar: str | None = None
    resume_count: int = 0
    match_history_count: int = 0


class UpdateProfileRequest(BaseModel):
    """更新个人信息请求（所有字段可选）"""
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    education: str | None = None


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
