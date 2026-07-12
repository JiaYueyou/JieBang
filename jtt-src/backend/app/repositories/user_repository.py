"""
用户仓库 —— 封装用户相关的数据库操作。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


class UserRepository:
    """用户数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_username(self, username: str) -> User | None:
        """通过用户名查找用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        """通过 ID 查找用户"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, username: str, email: str, password_hash: str) -> User:
        """创建新用户，返回用户对象"""
        user = User(username=username, email=email, password_hash=password_hash)
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(self, user: User, **kwargs) -> User:
        """更新用户字段"""
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        await self.db.flush()
        return user
