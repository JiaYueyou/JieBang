"""
简历仓库 —— 封装简历 CRUD 操作。
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.resume import Resume


class ResumeRepository:
    """简历数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_user(self, user_id: int) -> list[Resume]:
        """列出某用户的所有简历"""
        result = await self.db.execute(
            select(Resume).where(Resume.user_id == user_id).order_by(Resume.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, resume_id: int) -> Resume | None:
        """根据 ID 获取简历"""
        result = await self.db.execute(select(Resume).where(Resume.id == resume_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: int, data: dict) -> Resume:
        """创建简历"""
        resume = Resume(user_id=user_id, **data)
        self.db.add(resume)
        await self.db.flush()
        return resume

    async def update(self, resume: Resume, **kwargs):
        """更新简历字段（JSON 字段需整体替换）"""
        for key, value in kwargs.items():
            if value is not None and hasattr(resume, key):
                setattr(resume, key, value)
        await self.db.flush()

    async def delete(self, resume: Resume):
        """删除简历"""
        await self.db.delete(resume)
        await self.db.flush()

    async def duplicate(self, resume: Resume) -> Resume:
        """复制简历（生成副本）"""
        # 将 SQLAlchemy 对象转为 dict，排除 id、外键和时间戳（user_id 由 create 单独传入）
        data = {c.name: getattr(resume, c.name) for c in resume.__table__.columns
                if c.name not in ("id", "user_id", "created_at", "updated_at")}
        data["name"] = f"{resume.name} (副本)"
        return await self.create(resume.user_id, data)
