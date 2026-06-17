"""认证接口"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == req.username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        return ApiResponse(code=40001, message="用户名或密码错误")
    token = create_access_token({"user_id": user.id, "username": user.username})
    return ApiResponse(
        data=TokenResponse(
            access_token=token, username=user.username
        ).model_dump()
    )


@router.post("/register", response_model=ApiResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        return ApiResponse(code=40002, message="用户名已存在")
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    await db.commit()
    return ApiResponse(message="注册成功")
