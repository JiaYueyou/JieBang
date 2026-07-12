"""
收藏仓库 —— 封装用户岗位收藏的存储和查询。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.favorite import Favorite


class FavoriteRepository:
    """收藏数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_user(self, user_id: int) -> list[Favorite]:
        """列出某用户的所有收藏"""
        result = await self.db.execute(
            select(Favorite).where(Favorite.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get(self, user_id: int, position_id: int) -> Favorite | None:
        """查找特定收藏记录"""
        result = await self.db.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.position_id == position_id,
            )
        )
        return result.scalar_one_or_none()

    async def add(self, user_id: int, position_id: int) -> Favorite:
        """添加收藏"""
        fav = Favorite(user_id=user_id, position_id=position_id)
        self.db.add(fav)
        await self.db.flush()
        return fav

    async def remove(self, favorite: Favorite):
        """取消收藏"""
        await self.db.delete(favorite)
        await self.db.flush()

    async def is_favorited(self, user_id: int, position_id: int) -> bool:
        """检查是否已收藏"""
        fav = await self.get(user_id, position_id)
        return fav is not None
