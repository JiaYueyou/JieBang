"""基于 MySQL 可追溯事实的岗位洞察与趋势统计。"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AnalysisInsightDecision,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    StandardJob,
    StandardJobSource,
)
from app.core.exceptions import ResourceNotFoundError
from app.schemas.analysis import (
    AnalysisDataQuality,
    AnalysisOverview,
    AnalysisStats,
    CapabilityChangeInsight,
    EmergingJobInsight,
    EmergingSkill,
    HeatmapPoint,
    InsightDecision,
    InsightDecisionResponse,
    JobInsightsResponse,
    LocationDemand,
    TrendSeries,
)


@dataclass(frozen=True)
class ObservedJob:
    row: RawJobRecord
    observed_at: datetime
    used_fallback_time: bool
    salary_k: float | None

    @property
    def month(self) -> str:
        return self.observed_at.strftime("%Y-%m")


class AnalysisService:
    MIN_TREND_RECORDS = 10
    MIN_TREND_MONTHS = 2
    MIN_EMERGING_COUNT = 2
    MIN_STANDARD_JOB_SOURCES = 2

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def overview(
        self,
        *,
        months: int,
        keyword: str | None,
        city: str | None,
    ) -> AnalysisOverview:
        observed = await self._load_observed_jobs(keyword=keyword, city=city)
        labels = self._month_labels(observed, months)
        in_window = [item for item in observed if item.month in labels]
        facts = await self._load_verified_facts({item.row.id for item in in_window})
        fact_counts = self._fact_month_counts(
            facts, {item.row.id: item.month for item in in_window}
        )
        emerging = self._emerging_skills(facts, fact_counts, labels)
        heatmap_skills = [item.skill for item in emerging[:8]] or self._top_skill_names(facts, 8)
        salaries = [item.salary_k for item in in_window if item.salary_k is not None]
        return AnalysisOverview(
            stats=AnalysisStats(
                total_jobs=len(in_window),
                new_skills=len(emerging),
                average_salary_k=(
                    round(sum(salaries) / len(salaries), 1) if salaries else None
                ),
                active_cities=len({item.row.city for item in in_window if item.row.city}),
            ),
            months=labels,
            job_demand=self._job_demand(in_window, labels),
            salary=self._salary_trends(in_window, labels),
            heatmap_skills=heatmap_skills,
            heatmap=self._heatmap(fact_counts, labels, heatmap_skills),
            locations=[
                LocationDemand(city=name, value=count)
                for name, count in Counter(
                    item.row.city for item in in_window if item.row.city
                ).most_common(10)
            ],
            emerging_skills=emerging,
            data_quality=self._quality(observed=in_window, facts=facts),
        )

    async def job_insights(
        self, *, skill: str | None, limit: int, user_id: int
    ) -> JobInsightsResponse:
        observed = await self._load_observed_jobs(keyword=None, city=None)
        record_month = {item.row.id: item.month for item in observed}
        facts = await self._load_verified_facts(set(record_month))
        quality = self._quality(observed=observed, facts=facts)

        standard_jobs = list((await self.db.execute(
            select(StandardJob)
            .where(
                StandardJob.status == "active",
                StandardJob.source_count >= self.MIN_STANDARD_JOB_SOURCES,
            )
            .order_by(StandardJob.first_seen_at.desc(), StandardJob.source_count.desc())
        )).scalars())
        if not standard_jobs:
            quality.insufficient_data = True
            quality.notes.append("尚未生成满足来源阈值的标准岗位，请先完成岗位聚合或图谱同步。")
        sources = list((await self.db.execute(
            select(StandardJobSource).where(StandardJobSource.source_type == "raw")
        )).scalars())
        source_ids: dict[int, set[int]] = defaultdict(set)
        for source in sources:
            source_ids[source.standard_job_id].add(source.source_id)

        skills_by_raw: dict[int, list[Skill]] = defaultdict(list)
        for fact, fact_skill in facts:
            if fact.raw_job_record_id:
                skills_by_raw[fact.raw_job_record_id].append(fact_skill)
        decisions = list((await self.db.execute(
            select(AnalysisInsightDecision).where(
                AnalysisInsightDecision.insight_type == "emerging_job",
                AnalysisInsightDecision.created_by == user_id,
            )
        )).scalars())
        decision_by_target = {row.target_id: row.decision for row in decisions}

        needle = (skill or "").strip().casefold()
        emerging_jobs: list[EmergingJobInsight] = []
        for standard in standard_jobs:
            counts = Counter(
                fact_skill.name
                for raw_id in source_ids.get(standard.id, set())
                for fact_skill in skills_by_raw.get(raw_id, [])
            )
            core_skills = [name for name, _ in counts.most_common(6)]
            if needle and needle not in " ".join([standard.name, *core_skills]).casefold():
                continue
            confidence = min(99, 60 + standard.source_count * 6 + len(core_skills) * 2)
            emerging_jobs.append(EmergingJobInsight(
                id=standard.id,
                name=standard.name,
                core_skills=core_skills,
                description=(
                    standard.description
                    or f"由 {standard.source_count} 条独立岗位来源聚合形成。"
                ),
                confidence=confidence,
                source_count=standard.source_count,
                first_seen_at=standard.first_seen_at,
                decision=decision_by_target.get(standard.id),
            ))
            if len(emerging_jobs) >= limit:
                break

        return JobInsightsResponse(
            emerging_jobs=emerging_jobs,
            capability_changes=self._capability_changes(
                standard_jobs=standard_jobs,
                source_ids=source_ids,
                facts=facts,
                record_month=record_month,
                skill_filter=needle,
                limit=limit,
            ),
            data_quality=quality,
        )

    async def decide_emerging_job(
        self,
        *,
        standard_job_id: int,
        decision: InsightDecision,
        note: str | None,
        user_id: int,
    ) -> InsightDecisionResponse:
        standard = await self.db.get(StandardJob, standard_job_id)
        if not standard:
            raise ResourceNotFoundError("标准岗位不存在")
        row = (await self.db.execute(
            select(AnalysisInsightDecision).where(
                AnalysisInsightDecision.insight_type == "emerging_job",
                AnalysisInsightDecision.target_id == standard_job_id,
                AnalysisInsightDecision.created_by == user_id,
            )
        )).scalar_one_or_none()
        if row is None:
            row = AnalysisInsightDecision(
                insight_type="emerging_job",
                target_id=standard_job_id,
                decision=decision.value,
                note=note,
                created_by=user_id,
            )
            self.db.add(row)
        else:
            row.decision = decision.value
            row.note = note
            row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return InsightDecisionResponse(
            id=row.id,
            insight_type=row.insight_type,
            target_id=row.target_id,
            decision=InsightDecision(row.decision),
            note=row.note,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _load_observed_jobs(
        self, *, keyword: str | None, city: str | None
    ) -> list[ObservedJob]:
        rows = (await self.db.execute(
            select(RawJobRecord, SourceDocument).join(
                SourceDocument,
                RawJobRecord.source_document_id == SourceDocument.id,
            )
        )).all()
        needle = (keyword or "").strip().casefold()
        city_filter = (city or "").strip().casefold()
        result: list[ObservedJob] = []
        for row, document in rows:
            if needle and needle not in f"{row.title} {row.standardized_title or ''}".casefold():
                continue
            if city_filter and city_filter != (row.city or "").casefold():
                continue
            raw_time = (
                row.posted_at_text
                or document.source_meta.get("posted_at")
                or row.crawled_at_text
                or document.source_meta.get("crawled_at")
            )
            observed_at = self.parse_datetime(raw_time)
            result.append(ObservedJob(
                row=row,
                observed_at=observed_at or row.created_at,
                used_fallback_time=observed_at is None,
                salary_k=self.parse_salary_k(row.salary_text),
            ))
        return result

    async def _load_verified_facts(
        self, raw_ids: set[int]
    ) -> list[tuple[JobSkillFact, Skill]]:
        if not raw_ids:
            return []
        return list((await self.db.execute(
            select(JobSkillFact, Skill)
            .join(Skill, JobSkillFact.skill_id == Skill.id)
            .where(
                JobSkillFact.raw_job_record_id.in_(raw_ids),
                JobSkillFact.verification_status == "verified",
            )
        )).all())

    def _quality(
        self,
        *,
        observed: list[ObservedJob],
        facts: list[tuple[JobSkillFact, Skill]],
    ) -> AnalysisDataQuality:
        dates = [item.observed_at for item in observed]
        observed_months = len({item.month for item in observed})
        insufficient = (
            len(observed) < self.MIN_TREND_RECORDS
            or observed_months < self.MIN_TREND_MONTHS
        )
        notes: list[str] = []
        if len(observed) < self.MIN_TREND_RECORDS:
            notes.append(f"有效岗位样本少于 {self.MIN_TREND_RECORDS} 条。")
        if observed_months < self.MIN_TREND_MONTHS:
            notes.append(
                f"有效时间跨度少于 {self.MIN_TREND_MONTHS} 个月，暂不适合解释增长趋势。"
            )
        if any(item.used_fallback_time for item in observed):
            notes.append("部分岗位缺少发布时间，已回退使用导入时间。")
        return AnalysisDataQuality(
            total_records=len(observed),
            valid_time_records=sum(not item.used_fallback_time for item in observed),
            fallback_time_records=sum(item.used_fallback_time for item in observed),
            valid_salary_records=sum(item.salary_k is not None for item in observed),
            verified_skill_facts=len(facts),
            observed_months=observed_months,
            coverage_start=min(dates) if dates else None,
            coverage_end=max(dates) if dates else None,
            insufficient_data=insufficient,
            notes=notes,
        )

    @staticmethod
    def parse_datetime(value: object) -> datetime | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        normalized = text.replace("年", "-").replace("月", "-").replace("日", "")
        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None)
        except ValueError:
            pass
        for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m"):
            try:
                return datetime.strptime(normalized, pattern)
            except ValueError:
                continue
        return None

    @staticmethod
    def parse_salary_k(value: str | None) -> float | None:
        text = (value or "").replace(",", "").strip()
        if not text:
            return None
        range_match = re.search(
            r"(\d+(?:\.\d+)?)\s*([kK万]?)\s*[-~至—–]\s*(\d+(?:\.\d+)?)\s*([kK万])",
            text,
        )
        if range_match:
            low, low_unit, high, high_unit = range_match.groups()
            low_value = float(low) * (10 if (low_unit or high_unit) == "万" else 1)
            high_value = float(high) * (10 if high_unit == "万" else 1)
            midpoint = (low_value + high_value) / 2
            return round(midpoint, 2) if 1 <= midpoint <= 500 else None
        single = re.search(r"(\d+(?:\.\d+)?)\s*([kK万])", text)
        if not single:
            return None
        amount = float(single.group(1)) * (10 if single.group(2) == "万" else 1)
        return round(amount, 2) if 1 <= amount <= 500 else None

    @staticmethod
    def _month_labels(observed: list[ObservedJob], months: int) -> list[str]:
        anchor = max((item.observed_at for item in observed), default=datetime.utcnow())
        labels: list[str] = []
        for offset in range(months - 1, -1, -1):
            absolute = anchor.year * 12 + anchor.month - 1 - offset
            labels.append(f"{absolute // 12:04d}-{absolute % 12 + 1:02d}")
        return labels

    @staticmethod
    def _job_demand(
        observed: list[ObservedJob], labels: list[str]
    ) -> list[TrendSeries]:
        names = Counter(item.row.standardized_title or item.row.title for item in observed)
        result: list[TrendSeries] = []
        for name, _ in names.most_common(5):
            counts = Counter(
                item.month
                for item in observed
                if (item.row.standardized_title or item.row.title) == name
            )
            result.append(TrendSeries(
                name=name,
                values=[float(counts[label]) for label in labels],
            ))
        return result

    @staticmethod
    def _salary_trends(
        observed: list[ObservedJob], labels: list[str]
    ) -> list[TrendSeries]:
        valid = [item for item in observed if item.salary_k is not None]
        groups = Counter(item.row.city or "全国" for item in valid)
        result: list[TrendSeries] = []
        for city, _ in groups.most_common(5):
            by_month: dict[str, list[float]] = defaultdict(list)
            for item in valid:
                if (item.row.city or "全国") == city and item.salary_k is not None:
                    by_month[item.month].append(item.salary_k)
            result.append(TrendSeries(
                name=city,
                values=[
                    round(sum(by_month[label]) / len(by_month[label]), 1)
                    if by_month[label]
                    else 0
                    for label in labels
                ],
            ))
        return result

    @staticmethod
    def _fact_month_counts(
        facts: list[tuple[JobSkillFact, Skill]], record_month: dict[int, str]
    ) -> dict[str, Counter[str]]:
        result: dict[str, Counter[str]] = defaultdict(Counter)
        for fact, skill in facts:
            month = record_month.get(fact.raw_job_record_id or -1)
            if month:
                result[skill.name][month] += 1
        return result

    @staticmethod
    def _top_skill_names(
        facts: list[tuple[JobSkillFact, Skill]], limit: int
    ) -> list[str]:
        return [
            name for name, _ in Counter(skill.name for _, skill in facts).most_common(limit)
        ]

    def _emerging_skills(
        self,
        facts: list[tuple[JobSkillFact, Skill]],
        counts: dict[str, Counter[str]],
        labels: list[str],
    ) -> list[EmergingSkill]:
        observed_fact_months = {month for values in counts.values() for month in values}
        if len(labels) < 2 or len(observed_fact_months) < 2:
            return []
        window = min(3, max(1, len(labels) // 2))
        current_labels = labels[-window:]
        previous_labels = labels[-2 * window:-window]
        skill_by_name = {skill.name: skill for _, skill in facts}
        result: list[EmergingSkill] = []
        for name, monthly in counts.items():
            current = sum(monthly[label] for label in current_labels)
            previous = sum(monthly[label] for label in previous_labels)
            if current < self.MIN_EMERGING_COUNT or current <= previous:
                continue
            growth = (
                100.0
                if previous == 0
                else round((current - previous) * 100 / previous, 1)
            )
            result.append(EmergingSkill(
                id=skill_by_name[name].id,
                skill=name,
                category=skill_by_name[name].category,
                growth=growth,
                stage="成长期" if growth >= 50 else "成熟期",
                sparkline=[monthly[label] for label in labels[-6:]],
                current_count=current,
                previous_count=previous,
            ))
        return sorted(
            result,
            key=lambda item: (-item.growth, -item.current_count, item.skill),
        )

    @staticmethod
    def _heatmap(
        counts: dict[str, Counter[str]], labels: list[str], skills: list[str]
    ) -> list[HeatmapPoint]:
        return [
            HeatmapPoint(x=x, y=y, value=counts[skill][month])
            for y, skill in enumerate(skills)
            for x, month in enumerate(labels)
        ]

    @staticmethod
    def _capability_changes(
        *,
        standard_jobs: list[StandardJob],
        source_ids: dict[int, set[int]],
        facts: list[tuple[JobSkillFact, Skill]],
        record_month: dict[int, str],
        skill_filter: str,
        limit: int,
    ) -> list[CapabilityChangeInsight]:
        months = sorted(set(record_month.values()))
        if len(months) < 2:
            return []
        split = max(1, len(months) // 2)
        previous_months = set(months[:split])
        current_months = set(months[split:])
        skill_rows: dict[int, list[str]] = defaultdict(list)
        for fact, skill in facts:
            if fact.raw_job_record_id:
                skill_rows[fact.raw_job_record_id].append(skill.name)

        result: list[CapabilityChangeInsight] = []
        for standard in standard_jobs:
            previous: Counter[str] = Counter()
            current: Counter[str] = Counter()
            for raw_id in source_ids.get(standard.id, set()):
                month = record_month.get(raw_id)
                target = current if month in current_months else previous
                for name in skill_rows.get(raw_id, []):
                    target[name] += 1
            added = sorted(name for name in current if not previous[name])
            removed = sorted(name for name in previous if not current[name])
            modified = sorted(
                name
                for name in set(previous) & set(current)
                if abs(current[name] - previous[name]) / max(previous[name], 1) >= 0.5
            )
            if skill_filter and skill_filter not in " ".join(
                [standard.name, *added, *modified, *removed]
            ).casefold():
                continue
            if not (added or modified or removed):
                continue
            result.append(CapabilityChangeInsight(
                id=standard.id,
                job_id=standard.id,
                job=standard.name,
                period=f"{min(previous_months)} 至 {max(current_months)}",
                added=added,
                modified=modified,
                removed=removed,
            ))
            if len(result) >= limit:
                break
        return result
