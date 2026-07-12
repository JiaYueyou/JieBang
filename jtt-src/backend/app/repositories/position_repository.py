"""
岗位仓库 —— 封装岗位、技能、技能变化的数据库操作。
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.position import JobPosition, Skill, SkillChange


class PositionRepository:
    """岗位数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_positions(
        self, category: str | None = None, keyword: str | None = None,
        tech_stack: str | None = None, page: int = 1, page_size: int = 20,
    ) -> tuple[list[JobPosition], int]:
        """分页查询岗位列表，支持分类、关键词、技术栈筛选"""
        query = select(JobPosition)

        if category:
            query = query.where(JobPosition.category == category)
        if keyword:
            # 关键词搜索岗位名称和概述
            query = query.where(
                (JobPosition.name.ilike(f"%{keyword}%")) |
                (JobPosition.summary.ilike(f"%{keyword}%"))
            )
        if tech_stack:
            # JSON 数组模糊匹配，查找包含指定技术栈的岗位
            query = query.where(JobPosition.tech_stack.contains([tech_stack]))

        # 计数查询
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(JobPosition.updated_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, position_id: int) -> JobPosition | None:
        """根据 ID 获取岗位详情，含关联技能和变化历史"""
        result = await self.db.execute(
            select(JobPosition)
            .where(JobPosition.id == position_id)
            .options(selectinload(JobPosition.required_skills))
            .options(selectinload(JobPosition.preferred_skills))
            .options(selectinload(JobPosition.skill_changes))
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> JobPosition:
        """创建新岗位"""
        position = JobPosition(**data)
        self.db.add(position)
        await self.db.flush()
        return position

    async def update_skills(self, position_id: int, skills: list[dict], kind: str):
        """替换岗位的某项技能列表（先删后加）"""
        # 删除旧的
        await self.db.execute(
            select(Skill).where(
                Skill.position_id == position_id,
                Skill.kind == kind,
            )
        )
        # 插入新的
        for sk in skills:
            s = Skill(position_id=position_id, kind=kind, **sk)
            self.db.add(s)

    async def add_skill_change(self, position_id: int, change: dict):
        """添加一条技能变化记录"""
        sc = SkillChange(position_id=position_id, **change)
        self.db.add(sc)
