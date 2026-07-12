"""
JWT 认证 —— token 生成、解析、当前用户获取。
"""
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES

security_scheme = HTTPBearer()


def create_access_token(user_id: int, username: str) -> str:
    """生成 JWT token，包含用户 ID 和用户名，有过期时间"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解析 JWT token，返回 payload；无效或过期返回 None"""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    FastAPI 依赖：从请求头 Bearer Token 中提取当前登录用户信息。
    返回 {"user_id": int, "username": str}
    """
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return {
        "user_id": int(payload.get("sub")),
        "username": payload.get("username", ""),
    }
