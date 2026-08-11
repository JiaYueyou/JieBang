"""Admin queries and reversible decisions for raw job data quality."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from math import ceil

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.core.time import utc_now
from app.models import JobSkillFact, RawJobRecord, SourceDocument
from app.schemas.common import PageMeta
from app.schemas.data_quality import (
    DataQualityList,
    DataQualitySummary,
    RawJobQualityItem,
)
from app.services.import_service import ImportService
from app.services.task_status_cache import bump_cache_generations


class DataQualityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_records(
        self,
        *,
        page: int,
        page_size: int,
        source: str | None = None,
        quality_status: str | None = None,
        quality_flag: str | None = None,
        near_duplicate_group_id: str | None = None,
        posted_from: datetime | None = None,
        posted_to: datetime | None = None,
        excluded: bool | None = None,
    ) -> tuple[DataQualityList, PageMeta]:
        filters = []
        if source:
            filters.append(SourceDocument.source == source)
        if quality_status:
            filters.append(RawJobRecord.quality_status == quality_status)
        if near_duplicate_group_id:
            filters.append(
                RawJobRecord.near_duplicate_group_id == near_duplicate_group_id
            )
        if posted_from:
            filters.append(RawJobRecord.posted_at >= posted_from)
        if posted_to:
            filters.append(RawJobRecord.posted_at <= posted_to)
        if excluded is not None:
            filters.append(RawJobRecord.is_excluded.is_(excluded))

        statement = (
            select(RawJobRecord, SourceDocument)
            .join(
                SourceDocument,
                SourceDocument.id == RawJobRecord.source_document_id,
            )
            .where(*filters)
            .order_by(
                RawJobRecord.quality_score.asc(),
                RawJobRecord.id.desc(),
            )
        )
        rows = (await self.db.execute(statement)).all()
        if quality_flag:
            rows = [
                row for row in rows if quality_flag in (row[0].quality_flags or [])
            ]
        total = len(rows)
        selected = rows[(page - 1) * page_size : page * page_size]
        items = [
            self._item(raw, source_row)
            for raw, source_row in selected
        ]
        return (
            DataQualityList(items=items, summary=await self.summary()),
            PageMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=ceil(total / page_size) if total else 0,
            ),
        )

    async def summary(self) -> DataQualitySummary:
        rows = list((await self.db.execute(select(RawJobRecord))).scalars())
        statuses = Counter(row.quality_status for row in rows)
        flags = Counter(
            flag for row in rows for flag in (row.quality_flags or [])
        )
        average = (
            round(sum(float(row.quality_score or 0) for row in rows) / len(rows), 4)
            if rows
            else 0
        )
        return DataQualitySummary(
            total=len(rows),
            accepted=statuses["accepted"],
            warning=statuses["warning"],
            rejected=statuses["rejected"],
            pending=statuses["pending"],
            near_duplicates=sum(
                row.dedup_status == "near_duplicate" for row in rows
            ),
            excluded=sum(bool(row.is_excluded) for row in rows),
            average_quality_score=average,
            flag_counts=dict(sorted(flags.items())),
        )

    async def decide(
        self,
        record_id: int,
        *,
        action: str,
        reason: str | None,
        user_id: int,
    ) -> RawJobQualityItem:
        raw = await self.db.get(RawJobRecord, record_id)
        if raw is None:
            raise ResourceNotFoundError("原始岗位记录不存在")
        if action == "exclude":
            raw.is_excluded = True
            raw.exclusion_reason = reason
            raw.excluded_by = user_id
            raw.excluded_at = utc_now()
            facts = (
                await self.db.execute(
                    select(JobSkillFact).where(
                        JobSkillFact.raw_job_record_id == raw.id,
                        JobSkillFact.verification_status != "rejected",
                    )
                )
            ).scalars()
            for fact in facts:
                fact.verification_status = "unverified"
        else:
            raw.is_excluded = False
            raw.exclusion_reason = None
            raw.excluded_by = None
            raw.excluded_at = None
            await ImportService(self.db)._cross_validate_facts([])
        await self.db.commit()
        await bump_cache_generations("analysis", "dashboard")
        source = await self.db.get(SourceDocument, raw.source_document_id)
        return self._item(raw, source)

    @staticmethod
    def _item(raw: RawJobRecord, source: SourceDocument) -> RawJobQualityItem:
        return RawJobQualityItem(
            id=raw.id,
            title=raw.title,
            standard_job_id=raw.standard_job_id,
            standardized_title=raw.standardized_title,
            company=raw.company,
            source=source.source,
            source_url=source.url,
            posted_at=raw.posted_at,
            crawled_at=raw.crawled_at,
            posted_at_text=raw.posted_at_text,
            crawled_at_text=raw.crawled_at_text,
            quality_score=raw.quality_score,
            freshness_score=raw.freshness_score,
            source_trust_score=raw.source_trust_score,
            quality_status=raw.quality_status,
            quality_flags=raw.quality_flags or [],
            dedup_status=raw.dedup_status,
            near_duplicate_group_id=raw.near_duplicate_group_id,
            near_duplicate_score=raw.near_duplicate_score,
            is_excluded=raw.is_excluded,
            exclusion_reason=raw.exclusion_reason,
            quality_evaluated_at=raw.quality_evaluated_at,
        )
