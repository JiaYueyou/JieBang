"""
认证服务 —— 登录、注册、个人信息管理、密码修改。
"""
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_access_token
from app.core.exceptions import InvalidCredentialsError, DuplicateUsernameError
from app.repositories.user_repository import UserRepository


class AuthService:
    """用户认证与账户管理"""

    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)
        self.db = db

    async def login(self, username: str, password: str) -> dict:
        """用户登录，验证密码后返回 JWT token 和用户信息"""
        user = await self.repo.get_by_username(username)
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            raise InvalidCredentialsError("用户名或密码错误")

        token = create_access_token(user.id, user.username)
        return {"token": token, "user": self._user_to_dict(user)}

    async def register(self, username: str, email: str, password: str) -> dict:
        """注册新用户"""
        existing = await self.repo.get_by_username(username)
        if existing:
            raise DuplicateUsernameError("用户名已被注册")

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = await self.repo.create(username, email, password_hash)
        await self.db.commit()

        token = create_access_token(user.id, user.username)
        return {"token": token, "user": self._user_to_dict(user)}

    async def get_profile(self, user_id: int) -> dict:
        """获取用户个人信息"""
        user = await self.repo.get_by_id(user_id)
        return self._user_to_dict(user)

    async def update_profile(self, user_id: int, data: dict) -> dict:
        """更新用户个人信息"""
        user = await self.repo.get_by_id(user_id)
        user = await self.repo.update(user, **data)
        await self.db.commit()
        return self._user_to_dict(user)

    async def change_password(self, user_id: int, old_password: str, new_password: str):
        """修改密码"""
        user = await self.repo.get_by_id(user_id)
        if not bcrypt.checkpw(old_password.encode(), user.password_hash.encode()):
            raise InvalidCredentialsError("旧密码不正确")

        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        await self.repo.update(user, password_hash=new_hash)
        await self.db.commit()

    def _user_to_dict(self, user) -> dict:
        """将 User 模型转为字典供 API 返回"""
        return {
            "id": user.id, "username": user.username, "email": user.email,
            "nickname": user.nickname, "phone": user.phone,
            "city": user.city, "education": user.education,
            "avatar": user.avatar, "resume_count": user.resume_count,
            "match_history_count": user.match_history_count,
        }
