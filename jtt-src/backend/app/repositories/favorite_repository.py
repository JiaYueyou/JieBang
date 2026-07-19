"""
收藏仓库 —— 封装多类型收藏的存储和查询。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.favorite import Favorite


class FavoriteRepository:
    """收藏数据访问层（支持 position / learning_resource / quiz_error / knowledge_point）"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_user(self, user_id: int, item_type: str | None = None) -> list[Favorite]:
        """列出某用户的收藏，可按类型筛选"""
        stmt = select(Favorite).where(Favorite.user_id == user_id)
        if item_type:
            stmt = stmt.where(Favorite.item_type == item_type)
        stmt = stmt.order_by(Favorite.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_item(self, user_id: int, item_type: str, item_id: str) -> Favorite | None:
        """查找特定收藏项"""
        result = await self.db.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.item_type == item_type,
                Favorite.item_id == item_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, fav_id: int) -> Favorite | None:
        """按 ID 查找收藏"""
        result = await self.db.execute(
            select(Favorite).where(Favorite.id == fav_id)
        )
        return result.scalar_one_or_none()

    async def add(
        self, user_id: int, item_type: str, item_id: str,
        title: str, summary: str | None = None,
        item_data: dict | None = None, tags: list | None = None,
    ) -> Favorite:
        """添加收藏"""
        fav = Favorite(
            user_id=user_id, item_type=item_type, item_id=item_id,
            title=title, summary=summary,
            item_data=item_data or {}, tags=tags,
        )
        self.db.add(fav)
        await self.db.flush()
        return fav

    async def remove(self, favorite: Favorite):
        """取消收藏"""
        await self.db.delete(favorite)
        await self.db.flush()

    async def is_favorited(self, user_id: int, item_type: str, item_id: str) -> bool:
        """检查是否已收藏"""
        fav = await self.get_by_item(user_id, item_type, item_id)
        return fav is not None
