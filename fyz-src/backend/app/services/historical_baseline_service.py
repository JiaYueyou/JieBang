"""Build and publish immutable historical trend baselines."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AnalysisBaselineSkill,
    AnalysisBaselineSnapshot,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
)


@dataclass(frozen=True)
class BaselineBuildResult:
    version: str
    ready: bool
    status: str
    quality_summary: dict
    source_summary: dict


class HistoricalBaselineService:
    """Creates draft or active snapshots without modifying source job facts."""

    MIN_CLUSTERS = 500
    MIN_SOURCES = 3
    MIN_MONTHS = 3
    # 历史基线用于判断“过去是否已经稳定出现”，不能因人工审核队列
    # 尚未清空而把成熟技术误判为新技术。审核状态仍会被记录，但发布
    # 门槛采用质量合格、未驳回且技能可用的规则事实。
    MIN_REVIEWABLE_FACTS = 500

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build(
        self,
        *,
        version: str,
        period_start: date,
        period_end: date,
        activate: bool = False,
        created_by: int | None = None,
        persist: bool = True,
    ) -> BaselineBuildResult:
        if period_start > period_end:
            raise ValueError("period_start must not be later than period_end")
        if persist and await self.db.scalar(
            select(AnalysisBaselineSnapshot.id).where(
                AnalysisBaselineSnapshot.version == version
            )
        ):
            raise ValueError(f"baseline version already exists: {version}")

        start_at = datetime.combine(period_start, time.min)
        end_at = datetime.combine(period_end + timedelta(days=1), time.min)
        rows = list((await self.db.execute(
            select(RawJobRecord, SourceDocument)
            .join(SourceDocument, RawJobRecord.source_document_id == SourceDocument.id)
            .where(
                RawJobRecord.posted_at.is_not(None),
                RawJobRecord.posted_at >= start_at,
                RawJobRecord.posted_at < end_at,
                RawJobRecord.quality_status.in_(("accepted", "warning")),
                RawJobRecord.is_excluded.is_(False),
            )
        )).all())

        representatives = self._representative_rows(rows)
        raw_ids = set(representatives)
        fact_rows = []
        if raw_ids:
            fact_rows = list((await self.db.execute(
                select(JobSkillFact, Skill)
                .join(Skill, JobSkillFact.skill_id == Skill.id)
                .where(
                    JobSkillFact.raw_job_record_id.in_(raw_ids),
                    JobSkillFact.verification_status != "rejected",
                    Skill.validation_status.in_(("approved", "pending_review")),
                )
            )).all())

        source_counts = Counter(document.source for raw, document in representatives.values())
        periods = {
            raw.posted_at.strftime("%Y-%m")
            for raw, _ in representatives.values()
            if raw.posted_at is not None
        }
        quality_summary = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "deduplicated_cluster_count": len(representatives),
            "source_count": len(source_counts),
            "observed_month_count": len(periods),
            "reviewable_fact_count": len(fact_rows),
            "verified_fact_count": sum(
                fact.verification_status == "verified" for fact, _ in fact_rows
            ),
        }
        ready = (
            len(representatives) >= self.MIN_CLUSTERS
            and len(source_counts) >= self.MIN_SOURCES
            and len(periods) >= self.MIN_MONTHS
            and len(fact_rows) >= self.MIN_REVIEWABLE_FACTS
        )
        quality_summary["is_ready"] = ready
        source_summary = {name: count for name, count in source_counts.most_common()}
        if activate and not ready:
            raise ValueError("baseline does not meet publication thresholds")

        status = "active" if activate else "draft"
        if persist:
            snapshot = AnalysisBaselineSnapshot(
                version=version,
                status=status,
                period_start=period_start,
                period_end=period_end,
                source_summary=source_summary,
                quality_summary=quality_summary,
                created_by=created_by,
                activated_at=datetime.utcnow() if activate else None,
            )
            self.db.add(snapshot)
            await self.db.flush()
            for item in self._skill_rows(
                baseline_id=snapshot.id,
                representatives=representatives,
                fact_rows=fact_rows,
            ):
                self.db.add(item)
            if activate:
                await self.db.execute(
                    AnalysisBaselineSnapshot.__table__.update()
                    .where(
                        AnalysisBaselineSnapshot.status == "active",
                        AnalysisBaselineSnapshot.id != snapshot.id,
                    )
                    .values(status="retired")
                )
            await self.db.commit()
        return BaselineBuildResult(
            version=version,
            ready=ready,
            status=status,
            quality_summary=quality_summary,
            source_summary=source_summary,
        )

    @staticmethod
    def _representative_rows(
        rows: list[tuple[RawJobRecord, SourceDocument]],
    ) -> dict[int, tuple[RawJobRecord, SourceDocument]]:
        grouped: dict[tuple[str, str, str, str], tuple[RawJobRecord, SourceDocument]] = {}
        for raw, document in rows:
            if raw.posted_at is None:
                continue
            key = (
                str(raw.standard_job_id or raw.standardized_title or raw.title).casefold(),
                (raw.company or document.company or "unknown").strip().casefold(),
                (raw.city or "unknown").strip().casefold(),
                raw.posted_at.strftime("%Y-%m"),
            )
            existing = grouped.get(key)
            if existing is None or raw.id < existing[0].id:
                grouped[key] = (raw, document)
        return {raw.id: (raw, document) for raw, document in grouped.values()}

    @staticmethod
    def _skill_rows(
        *,
        baseline_id: int,
        representatives: dict[int, tuple[RawJobRecord, SourceDocument]],
        fact_rows: list[tuple[JobSkillFact, Skill]],
    ) -> list[AnalysisBaselineSkill]:
        by_skill: dict[int, dict] = defaultdict(
            lambda: {"skill": None, "raw_ids": set(), "companies": set(), "sources": set(), "periods": set()}
        )
        for fact, skill in fact_rows:
            raw_id = fact.raw_job_record_id
            if raw_id not in representatives:
                continue
            raw, document = representatives[raw_id]
            value = by_skill[skill.id]
            value["skill"] = skill
            value["raw_ids"].add(raw_id)
            value["companies"].add((raw.company or document.company or "unknown").casefold())
            value["sources"].add(document.source.casefold())
            value["periods"].add(raw.posted_at.strftime("%Y-%m"))
        denominator = max(len(representatives), 1)
        result: list[AnalysisBaselineSkill] = []
        for skill_id, value in by_skill.items():
            clusters = len(value["raw_ids"])
            companies = len(value["companies"] - {"unknown"})
            sources = len(value["sources"])
            periods = len(value["periods"])
            maturity = (
                "mature"
                if clusters >= 8 and companies >= 3 and sources >= 2 and periods >= 3
                else "established"
                if clusters >= 3 and companies >= 2 and sources >= 2 and periods >= 2
                else "observed"
            )
            result.append(AnalysisBaselineSkill(
                baseline_id=baseline_id,
                skill_id=skill_id,
                segment_key="all",
                cluster_count=clusters,
                company_count=companies,
                source_count=sources,
                active_period_count=periods,
                prevalence=round(clusters / denominator, 6),
                maturity_stage=maturity,
                evidence_summary={"periods": sorted(value["periods"])},
            ))
        return result
