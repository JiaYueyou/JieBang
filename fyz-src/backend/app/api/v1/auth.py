"""认证接口"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.common import ApiResponse
from app.services import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


error_responses = {
    401: {"model": ApiResponse[None], "description": "认证失败"},
    409: {"model": ApiResponse[None], "description": "资源冲突"},
    422: {"model": ApiResponse[None], "description": "参数校验失败"},
}


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    responses={401: error_responses[401], 422: error_responses[422]},
)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[TokenResponse]:
    token = await service.login(request)
    return ApiResponse(data=token)


@router.post(
    "/register",
    response_model=ApiResponse[None],
    responses={409: error_responses[409], 422: error_responses[422]},
)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[None]:
    await service.register(request)
    return ApiResponse(message="注册成功")
