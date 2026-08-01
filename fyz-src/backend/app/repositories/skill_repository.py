"""技能、事实、来源和任务数据访问。"""

from __future__ import annotations

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utc_now_naive
from app.models import (
    AgentRun,
    AsyncTask,
    JobPosting,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    User,
)


class SkillRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_skills(self, *, page: int, page_size: int, keyword: str | None, category: str | None):
        filters = []
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(or_(Skill.name.like(pattern), Skill.canonical_name.like(pattern)))
        if category:
            filters.append(Skill.category == category)
        total = await self.db.scalar(select(func.count(Skill.id)).where(*filters))
        rows = await self.db.execute(
            select(Skill).where(*filters).order_by(Skill.name)
            .offset((page - 1) * page_size).limit(page_size)
        )
        return list(rows.scalars()), int(total or 0)

    async def get_skill(self, skill_id: int) -> Skill | None:
        return await self.db.get(Skill, skill_id)

    async def get_or_create_skill(
        self,
        *,
        name: str,
        canonical_key: str,
        category: str,
        aliases: list[str],
        validation_status: str = "approved",
    ) -> Skill:
        row = (await self.db.execute(select(Skill).where(Skill.canonical_key == canonical_key))).scalar_one_or_none()
        now = utc_now_naive()
        if row:
            row.last_seen_at = now
            merged = sorted(set(row.aliases or []) | set(aliases))
            row.aliases = merged
            return row
        row = Skill(
            name=name, canonical_name=name, canonical_key=canonical_key,
            category=category, aliases=aliases, first_seen_at=now, last_seen_at=now,
            validation_status=validation_status,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_source_by_fingerprint(self, fingerprint: str) -> SourceDocument | None:
        return (await self.db.execute(
            select(SourceDocument).where(SourceDocument.content_fingerprint == fingerprint)
        )).scalar_one_or_none()

    async def get_source_by_identity(
        self,
        *,
        source: str,
        external_id: str,
    ) -> SourceDocument | None:
        return (
            await self.db.execute(
                select(SourceDocument).where(
                    SourceDocument.source == source,
                    SourceDocument.external_id == external_id,
                )
            )
        ).scalar_one_or_none()

    async def add_source_and_raw(self, *, source: SourceDocument, raw: RawJobRecord) -> RawJobRecord:
        self.db.add(source)
        await self.db.flush()
        raw.source_document_id = source.id
        self.db.add(raw)
        await self.db.flush()
        return raw

    async def replace_facts(self, *, job_id: int | None, raw_job_record_id: int | None) -> None:
        query = delete(JobSkillFact)
        query = query.where(
            JobSkillFact.job_id == job_id
            if job_id is not None
            else JobSkillFact.raw_job_record_id == raw_job_record_id
        )
        await self.db.execute(query)

    async def add_fact(self, fact: JobSkillFact) -> JobSkillFact:
        self.db.add(fact)
        await self.db.flush()
        return fact

    async def list_job_facts(self, job_id: int) -> list[JobSkillFact]:
        rows = await self.db.execute(
            select(JobSkillFact).options(selectinload(JobSkillFact.skill))
            .where(JobSkillFact.job_id == job_id).order_by(JobSkillFact.confidence.desc())
        )
        return list(rows.scalars())

    @staticmethod
    def _review_query():
        return (
            select(
                JobSkillFact,
                Skill,
                RawJobRecord,
                SourceDocument,
                JobPosting,
                User.username,
            )
            .join(Skill, Skill.id == JobSkillFact.skill_id)
            .outerjoin(RawJobRecord, RawJobRecord.id == JobSkillFact.raw_job_record_id)
            .outerjoin(
                SourceDocument,
                SourceDocument.id == RawJobRecord.source_document_id,
            )
            .outerjoin(JobPosting, JobPosting.id == JobSkillFact.job_id)
            .outerjoin(User, User.id == JobSkillFact.reviewed_by)
        )

    async def list_fact_reviews(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None,
        keyword: str | None,
    ):
        filters = []
        if status:
            filters.append(JobSkillFact.verification_status == status)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(
                or_(
                    Skill.name.like(pattern),
                    JobSkillFact.evidence_text.like(pattern),
                    RawJobRecord.title.like(pattern),
                    JobPosting.title.like(pattern),
                )
            )
        total = await self.db.scalar(
            select(func.count(JobSkillFact.id))
            .select_from(JobSkillFact)
            .join(Skill, Skill.id == JobSkillFact.skill_id)
            .outerjoin(RawJobRecord, RawJobRecord.id == JobSkillFact.raw_job_record_id)
            .outerjoin(JobPosting, JobPosting.id == JobSkillFact.job_id)
            .where(*filters)
        )
        rows = await self.db.execute(
            self._review_query()
            .where(*filters)
            .order_by(JobSkillFact.created_at.desc(), JobSkillFact.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        summary_rows = await self.db.execute(
            select(
                JobSkillFact.verification_status,
                func.count(JobSkillFact.id),
            ).group_by(JobSkillFact.verification_status)
        )
        return rows.all(), int(total or 0), {
            str(status_value): int(count)
            for status_value, count in summary_rows.all()
        }

    async def get_fact_review(self, fact_id: int):
        return (
            await self.db.execute(
                self._review_query().where(JobSkillFact.id == fact_id)
            )
        ).one_or_none()

    async def get_fact(self, fact_id: int) -> JobSkillFact | None:
        return await self.db.get(JobSkillFact, fact_id)

    async def get_fact_for_update(self, fact_id: int) -> JobSkillFact | None:
        return (
            await self.db.execute(
                select(JobSkillFact)
                .where(JobSkillFact.id == fact_id)
                .with_for_update()
            )
        ).scalar_one_or_none()

    async def get_facts_for_review(
        self, *, fact_ids: list[int] | None = None, keyword: str | None = None
    ) -> list[JobSkillFact]:
        filters = [JobSkillFact.verification_status == "unverified"]
        query = (
            select(JobSkillFact)
            .join(Skill, Skill.id == JobSkillFact.skill_id)
            .outerjoin(RawJobRecord, RawJobRecord.id == JobSkillFact.raw_job_record_id)
            .outerjoin(JobPosting, JobPosting.id == JobSkillFact.job_id)
        )
        if fact_ids is not None:
            filters.append(JobSkillFact.id.in_(fact_ids))
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(
                or_(
                    Skill.name.like(pattern),
                    JobSkillFact.evidence_text.like(pattern),
                    RawJobRecord.title.like(pattern),
                    JobPosting.title.like(pattern),
                )
            )
        rows = await self.db.execute(
            query.where(*filters).order_by(JobSkillFact.id).with_for_update()
        )
        return list(rows.scalars().unique())

    async def add_agent_run(self, run: AgentRun) -> None:
        self.db.add(run)
        await self.db.flush()


class TaskRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, task: AsyncTask) -> AsyncTask:
        self.db.add(task)
        await self.db.flush()
        return task

    async def get(self, task_id: str) -> AsyncTask | None:
        return await self.db.get(AsyncTask, task_id)
