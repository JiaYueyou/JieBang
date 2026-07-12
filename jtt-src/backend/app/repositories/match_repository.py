"""
匹配仓库 —— 封装人岗匹配结果的存储和查询。
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.match import MatchResult


class MatchRepository:
    """匹配数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: dict) -> MatchResult:
        """保存匹配结果"""
        result = MatchResult(user_id=user_id, **data)
        self.db.add(result)
        await self.db.flush()
        return result

    async def get_by_ids(self, resume_id: int, position_id: int) -> MatchResult | None:
        """查找某简历对某岗位的最新匹配结果"""
        result = await self.db.execute(
            select(MatchResult)
            .where(MatchResult.resume_id == resume_id)
            .where(MatchResult.position_id == position_id)
            .order_by(MatchResult.match_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(self, user_id: int) -> list[MatchResult]:
        """获取用户的匹配历史"""
        result = await self.db.execute(
            select(MatchResult)
            .where(MatchResult.user_id == user_id)
            .order_by(MatchResult.match_date.desc())
            .limit(50)
        )
        return list(result.scalars().all())

    async def batch_create(self, user_id: int, results: list[dict]) -> list[MatchResult]:
        """批量保存匹配结果"""
        entities = []
        for data in results:
            entity = MatchResult(user_id=user_id, **data)
            self.db.add(entity)
            entities.append(entity)
        await self.db.flush()
        return entities
