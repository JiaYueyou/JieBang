"""JWT 认证工具"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.schemas.auth import TokenPrincipal

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPrincipal:
    if not credentials:
        raise AuthenticationError("未提供认证信息")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise AuthenticationError()

    user_id = payload.get("user_id")
    username = payload.get("username")
    role = payload.get("role", "user")
    if not isinstance(user_id, int) or not isinstance(username, str):
        raise AuthenticationError()
    if role not in {"user", "recruiter", "admin"}:
        raise AuthenticationError()
    return TokenPrincipal(user_id=user_id, username=username, role=role)


async def require_recruiter(
    principal: TokenPrincipal = Depends(get_current_user),
) -> TokenPrincipal:
    if principal.role not in {"recruiter", "admin"}:
        raise AuthorizationError("该 Agent 能力仅限招聘负责人或管理员")
    return principal


async def require_admin(
    principal: TokenPrincipal = Depends(get_current_user),
) -> TokenPrincipal:
    if principal.role != "admin":
        raise AuthorizationError("该操作仅限管理员")
    return principal
