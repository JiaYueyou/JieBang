"""岗位数据访问。"""

from __future__ import annotations

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.orm import selectinload

from app.models import JobPosting, JobPostingSkill, JobPostingVersion


class JobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[JobPosting], int]:
        filters = [JobPosting.deleted_at.is_(None)]
        if status:
            filters.append(JobPosting.status == status)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(
                or_(
                    JobPosting.title.like(pattern),
                    JobPosting.standardized_title.like(pattern),
                    JobPosting.department.like(pattern),
                )
            )
        total = await self.db.scalar(
            select(func.count(JobPosting.id)).where(*filters)
        )
        result = await self.db.execute(
            select(JobPosting)
            .options(selectinload(JobPosting.skills))
            .where(*filters)
            .order_by(JobPosting.created_at.desc(), JobPosting.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().unique()), int(total or 0)

    async def get(self, job_id: int, *, include_deleted: bool = False) -> JobPosting | None:
        query = (
            select(JobPosting)
            .options(
                selectinload(JobPosting.skills),
                selectinload(JobPosting.versions),
            )
            .where(JobPosting.id == job_id)
        )
        if not include_deleted:
            query = query.where(JobPosting.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def add(self, job: JobPosting) -> JobPosting:
        self.db.add(job)
        await self.db.flush()
        return job

    async def replace_skills(
        self,
        job: JobPosting,
        *,
        required: list[str],
        bonus: list[str],
    ) -> None:
        await self.db.execute(
            delete(JobPostingSkill).where(JobPostingSkill.job_id == job.id)
        )
        set_committed_value(job, "skills", [])
        for kind, names in (("required", required), ("bonus", bonus)):
            seen: set[str] = set()
            for index, raw_name in enumerate(names):
                name = raw_name.strip()
                key = name.casefold()
                if not name or key in seen:
                    continue
                seen.add(key)
                job.skills.append(
                    JobPostingSkill(name=name, kind=kind, sort_order=index)
                )
        await self.db.flush()

    async def next_version_no(self, job_id: int) -> int:
        current = await self.db.scalar(
            select(func.max(JobPostingVersion.version_no)).where(
                JobPostingVersion.job_id == job_id
            )
        )
        return int(current or 0) + 1

    async def add_version(
        self,
        *,
        job_id: int,
        version_no: int,
        snapshot: dict,
        change_reason: str,
        created_by: int,
    ) -> JobPostingVersion:
        version = JobPostingVersion(
            job_id=job_id,
            version_no=version_no,
            snapshot=snapshot,
            change_reason=change_reason,
            created_by=created_by,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def list_versions(self, job_id: int) -> list[JobPostingVersion]:
        result = await self.db.execute(
            select(JobPostingVersion)
            .where(JobPostingVersion.job_id == job_id)
            .order_by(JobPostingVersion.version_no.desc())
        )
        return list(result.scalars())

    async def get_version(
        self, job_id: int, version_id: int
    ) -> JobPostingVersion | None:
        result = await self.db.execute(
            select(JobPostingVersion).where(
                JobPostingVersion.job_id == job_id,
                JobPostingVersion.id == version_id,
            )
        )
        return result.scalar_one_or_none()
