"""Read-only catalog for crawled jobs and their traceable skill evidence."""

from math import ceil

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models import JobSkillFact, RawJobRecord, Skill, SourceDocument
from app.schemas.common import PageMeta
from app.schemas.job import (
    ObservedJobDetail,
    ObservedJobSkillEvidence,
    ObservedJobSummary,
)


class ObservedJobService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        city: str | None,
        source: str | None,
    ) -> tuple[list[ObservedJobSummary], PageMeta]:
        conditions = []
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(or_(
                RawJobRecord.title.ilike(pattern),
                RawJobRecord.standardized_title.ilike(pattern),
                RawJobRecord.company.ilike(pattern),
            ))
        if city:
            conditions.append(RawJobRecord.city == city.strip())
        if source:
            conditions.append(SourceDocument.source.ilike(f"%{source.strip()}%"))

        base = (
            select(RawJobRecord, SourceDocument)
            .join(SourceDocument, RawJobRecord.source_document_id == SourceDocument.id)
            .where(*conditions)
        )
        total = int((await self.db.scalar(
            select(func.count()).select_from(base.subquery())
        )) or 0)
        rows = (await self.db.execute(
            base.order_by(RawJobRecord.created_at.desc(), RawJobRecord.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all()
        fact_counts = await self._fact_counts({row.id for row, _ in rows})
        return [
            self._summary(row, document, fact_counts.get(row.id, {}))
            for row, document in rows
        ], PageMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total else 0,
        )

    async def get(self, raw_job_id: int) -> ObservedJobDetail:
        result = (await self.db.execute(
            select(RawJobRecord, SourceDocument)
            .join(SourceDocument, RawJobRecord.source_document_id == SourceDocument.id)
            .where(RawJobRecord.id == raw_job_id)
        )).one_or_none()
        if result is None:
            raise ResourceNotFoundError("采集岗位不存在")
        row, document = result
        facts = (await self.db.execute(
            select(JobSkillFact, Skill)
            .join(Skill, JobSkillFact.skill_id == Skill.id)
            .where(JobSkillFact.raw_job_record_id == raw_job_id)
            .order_by(
                JobSkillFact.verification_status.asc(),
                JobSkillFact.confidence.desc(),
                Skill.name.asc(),
            )
        )).all()
        counts: dict[str, int] = {}
        for fact, _ in facts:
            counts[fact.verification_status] = counts.get(fact.verification_status, 0) + 1
        summary = self._summary(row, document, counts)
        return ObservedJobDetail(
            **summary.model_dump(),
            jd_text=row.jd_text,
            responsibilities=row.responsibilities,
            requirements=row.requirements,
            skills=[
                ObservedJobSkillEvidence(
                    fact_id=fact.id,
                    skill_id=skill.id,
                    skill_name=skill.name,
                    category=skill.category,
                    kind=fact.kind,
                    confidence=fact.confidence,
                    evidence_text=fact.evidence_text,
                    verification_status=fact.verification_status,
                    extraction_method=fact.extraction_method,
                    source_count=fact.source_count,
                )
                for fact, skill in facts
            ],
        )

    async def _fact_counts(self, raw_ids: set[int]) -> dict[int, dict[str, int]]:
        if not raw_ids:
            return {}
        rows = (await self.db.execute(
            select(
                JobSkillFact.raw_job_record_id,
                JobSkillFact.verification_status,
                func.count(JobSkillFact.id),
            )
            .where(JobSkillFact.raw_job_record_id.in_(raw_ids))
            .group_by(
                JobSkillFact.raw_job_record_id,
                JobSkillFact.verification_status,
            )
        )).all()
        result: dict[int, dict[str, int]] = {}
        for raw_id, status, count in rows:
            if raw_id is not None:
                result.setdefault(raw_id, {})[status] = int(count)
        return result

    @staticmethod
    def _summary(
        row: RawJobRecord,
        document: SourceDocument,
        counts: dict[str, int],
    ) -> ObservedJobSummary:
        source_meta = document.source_meta or {}
        return ObservedJobSummary(
            id=row.id,
            title=row.title,
            standardized_title=row.standardized_title,
            company=row.company or document.company,
            city=row.city,
            salary_text=row.salary_text,
            experience_text=row.experience_text,
            education_text=row.education_text,
            source=document.source,
            source_url=document.url,
            posted_at=row.posted_at_text or source_meta.get("posted_at"),
            crawled_at=row.crawled_at_text or source_meta.get("crawled_at"),
            dedup_status=row.dedup_status,
            verified_skill_count=counts.get("verified", 0),
            pending_skill_count=counts.get("unverified", 0),
        )
