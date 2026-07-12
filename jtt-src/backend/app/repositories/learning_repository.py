"""
学习路径仓库 —— 封装学习路径 CRUD 操作。
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.learning import LearningPath


class LearningRepository:
    """学习路径数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_user(self, user_id: int) -> list[LearningPath]:
        """列出某用户的所有学习路径"""
        result = await self.db.execute(
            select(LearningPath)
            .where(LearningPath.user_id == user_id)
            .order_by(LearningPath.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, path_id: int) -> LearningPath | None:
        """根据 ID 获取学习路径"""
        result = await self.db.execute(select(LearningPath).where(LearningPath.id == path_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: int, data: dict) -> LearningPath:
        """创建学习路径"""
        path = LearningPath(user_id=user_id, **data)
        self.db.add(path)
        await self.db.flush()
        return path

    async def update(self, path: LearningPath, **kwargs):
        """更新学习路径"""
        for key, value in kwargs.items():
            if value is not None and hasattr(path, key):
                setattr(path, key, value)
        await self.db.flush()

    async def delete(self, path: LearningPath):
        """删除学习路径"""
        await self.db.delete(path)
        await self.db.flush()
