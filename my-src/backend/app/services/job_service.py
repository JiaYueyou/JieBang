"""岗位管理领域服务。"""

from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidParameterError, ResourceNotFoundError
from app.models import JobPosting
from app.repositories import JobRepository
from app.schemas.common import PageMeta
from app.schemas.job import (
    JobCreate,
    JobStatus,
    JobSummary,
    JobUpdate,
    JobVersionResponse,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobService:
    def __init__(
        self,
        db: AsyncSession,
        repository: JobRepository | None = None,
    ) -> None:
        self.db = db
        self.jobs = repository or JobRepository(db)

    @staticmethod
    def _salary_range(job: JobPosting) -> str:
        if job.salary_min is None or job.salary_max is None:
            return ""
        minimum = f"{job.salary_min / 1000:g}K"
        maximum = f"{job.salary_max / 1000:g}K"
        suffix = f" · {job.salary_months}薪" if job.salary_months else ""
        return f"{minimum}-{maximum}{suffix}"

    @classmethod
    def to_summary(cls, job: JobPosting) -> JobSummary:
        required = [skill.name for skill in job.skills if skill.kind == "required"]
        bonus = [skill.name for skill in job.skills if skill.kind == "bonus"]
        return JobSummary(
            id=job.id,
            title=job.title,
            standardized_title=job.standardized_title,
            level=job.level,
            department=job.department,
            company=job.company,
            location=job.location,
            experience=job.experience,
            education=job.education,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_months=job.salary_months,
            salary_range=cls._salary_range(job),
            headcount=job.headcount,
            responsibilities=job.responsibilities or [],
            requirements=job.requirements or [],
            skills=required,
            bonus_skills=bonus,
            jd_text=job.jd_text,
            status=JobStatus(job.status),
            urgent=job.urgent,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    @classmethod
    def _snapshot(cls, job: JobPosting) -> dict:
        return cls.to_summary(job).model_dump(mode="json")

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        status: JobStatus | None,
        keyword: str | None,
    ) -> tuple[list[JobSummary], PageMeta]:
        rows, total = await self.jobs.list(
            page=page,
            page_size=page_size,
            status=status.value if status else None,
            keyword=keyword,
        )
        return [self.to_summary(row) for row in rows], PageMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total else 0,
        )

    async def get(self, job_id: int) -> JobSummary:
        job = await self._get_or_raise(job_id)
        return self.to_summary(job)

    async def create(self, payload: JobCreate, *, user_id: int) -> JobSummary:
        values = payload.model_dump(exclude={"skills", "bonus_skills", "salary_range"})
        values["status"] = payload.status.value
        if payload.status == JobStatus.open:
            values["published_at"] = _utc_now()
        job = JobPosting(**values, created_by=user_id, skills=[])
        try:
            await self.jobs.add(job)
            await self.jobs.replace_skills(
                job,
                required=payload.skills,
                bonus=payload.bonus_skills,
            )
            # MySQL 服务端生成时间字段后需在异步上下文中显式刷新，
            # 避免构建首个版本快照时触发 MissingGreenlet 懒加载。
            await self.db.refresh(job, attribute_names=["created_at", "updated_at"])
            await self.jobs.add_version(
                job_id=job.id,
                version_no=1,
                snapshot=self._snapshot(job),
                change_reason="创建岗位",
                created_by=user_id,
            )
            await self.db.commit()
            return self.to_summary(job)
        except Exception:
            await self.db.rollback()
            raise

    async def update(
        self,
        job_id: int,
        payload: JobUpdate,
        *,
        user_id: int,
    ) -> JobSummary:
        job = await self._get_or_raise(job_id)
        values = payload.model_dump(
            exclude_unset=True,
            exclude={"skills", "bonus_skills", "salary_range"},
        )
        status = values.get("status")
        if isinstance(status, JobStatus):
            values["status"] = status.value
        salary_min = values.get("salary_min", job.salary_min)
        salary_max = values.get("salary_max", job.salary_max)
        if (
            salary_min is not None
            and salary_max is not None
            and salary_min > salary_max
        ):
            raise InvalidParameterError("最低薪资不能高于最高薪资")
        for field, value in values.items():
            setattr(job, field, value)
        job.updated_at = _utc_now()
        if payload.status == JobStatus.open and job.published_at is None:
            job.published_at = _utc_now()
        required = (
            payload.skills
            if payload.skills is not None
            else [skill.name for skill in job.skills if skill.kind == "required"]
        )
        bonus = (
            payload.bonus_skills
            if payload.bonus_skills is not None
            else [skill.name for skill in job.skills if skill.kind == "bonus"]
        )
        try:
            if payload.skills is not None or payload.bonus_skills is not None:
                await self.jobs.replace_skills(job, required=required, bonus=bonus)
            await self.db.flush()
            version_no = await self.jobs.next_version_no(job.id)
            await self.jobs.add_version(
                job_id=job.id,
                version_no=version_no,
                snapshot=self._snapshot(job),
                change_reason="更新岗位",
                created_by=user_id,
            )
            await self.db.commit()
            return self.to_summary(job)
        except Exception:
            await self.db.rollback()
            raise

    async def update_status(
        self,
        job_id: int,
        status: JobStatus,
        *,
        user_id: int,
    ) -> JobSummary:
        return await self.update(
            job_id,
            JobUpdate(status=status),
            user_id=user_id,
        )

    async def delete(self, job_id: int, *, user_id: int) -> None:
        job = await self._get_or_raise(job_id)
        job.deleted_at = _utc_now()
        job.updated_at = _utc_now()
        try:
            snapshot = self._snapshot(job)
            snapshot["deleted_at"] = job.deleted_at.isoformat()
            version_no = await self.jobs.next_version_no(job.id)
            await self.jobs.add_version(
                job_id=job.id,
                version_no=version_no,
                snapshot=snapshot,
                change_reason="删除岗位",
                created_by=user_id,
            )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

    async def list_versions(self, job_id: int) -> list[JobVersionResponse]:
        await self._get_or_raise(job_id)
        rows = await self.jobs.list_versions(job_id)
        return [JobVersionResponse.model_validate(row) for row in rows]

    async def get_version(
        self, job_id: int, version_id: int
    ) -> JobVersionResponse:
        await self._get_or_raise(job_id)
        row = await self.jobs.get_version(job_id, version_id)
        if not row:
            raise ResourceNotFoundError("岗位版本不存在")
        return JobVersionResponse.model_validate(row)

    async def _get_or_raise(self, job_id: int) -> JobPosting:
        job = await self.jobs.get(job_id)
        if not job:
            raise ResourceNotFoundError("岗位不存在")
        return job
