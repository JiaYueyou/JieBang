"""
认证相关 API —— 登录、注册、个人信息、改密。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest, RegisterRequest, TokenResponse,
    UserProfileResponse, UpdateProfileRequest, ChangePasswordRequest,
)
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["认证"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """依赖注入：创建认证服务实例"""
    return AuthService(db)


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(req: LoginRequest, service: AuthService = Depends(get_auth_service)):
    """用户登录"""
    result = await service.login(req.username, req.password)
    return ApiResponse(data=result)


@router.post("/register", response_model=ApiResponse[TokenResponse])
async def register(req: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    """用户注册"""
    result = await service.register(req.username, req.email, req.password)
    return ApiResponse(data=result)


@router.post("/logout", response_model=ApiResponse)
async def logout():
    """用户登出（前端清除 token 即可）"""
    return ApiResponse(message="已登出")


@router.get("/profile", response_model=ApiResponse[UserProfileResponse])
async def get_profile(
    user: dict = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """获取当前用户个人信息"""
    profile = await service.get_profile(user["user_id"])
    return ApiResponse(data=profile)


@router.put("/profile", response_model=ApiResponse[UserProfileResponse])
async def update_profile(
    req: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """更新个人信息"""
    profile = await service.update_profile(user["user_id"], req.model_dump(exclude_none=True))
    return ApiResponse(data=profile)


@router.put("/password", response_model=ApiResponse)
async def change_password(
    req: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """修改密码"""
    await service.change_password(user["user_id"], req.old_password, req.new_password)
    return ApiResponse(message="密码修改成功")
