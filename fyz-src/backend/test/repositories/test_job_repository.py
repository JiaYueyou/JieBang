"""岗位 Repository 行为测试。"""

from app.core.database import async_session
from app.models import JobPosting
from app.repositories import JobRepository


async def test_repository_filters_soft_deleted_jobs():
    async with async_session() as db:
        repository = JobRepository(db)
        active = JobPosting(
            title="AI 工程师",
            level="senior",
            department="AI 研究院",
            created_by=1,
        )
        deleted = JobPosting(
            title="旧岗位",
            level="mid",
            department="历史部门",
            created_by=1,
        )
        await repository.add(active)
        await repository.add(deleted)
        from datetime import datetime

        deleted.deleted_at = datetime.utcnow()
        await db.commit()

        rows, total = await repository.list(page=1, page_size=20)
        assert total == 1
        assert [row.title for row in rows] == ["AI 工程师"]
