"""基于 MySQL 可追溯事实的岗位洞察与趋势统计。"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

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
    AnalysisBaseline,
    AnalysisDataQuality,
    AnalysisOverview,
    AnalysisStats,
    CapabilityChangeInsight,
    EmergingJobInsight,
    EmergingSkill,
    HeatmapPoint,
    InsightDecision,
    InsightDecisionResponse,
    JobReferenceStandard,
    JobInsightsResponse,
    LocationDemand,
    TechnologyStackBaseline,
    TrendWindow,
    TrendSeries,
)


@dataclass(frozen=True)
class ObservedJob:
    row: RawJobRecord
    observed_at: datetime
    used_fallback_time: bool
    salary_k: float | None
    cluster_key: str
    company_key: str
    location_key: str

    @property
    def month(self) -> str:
        return self.observed_at.strftime("%Y-%m")

    def bucket(self, granularity: str) -> str:
        return (
            self.observed_at.strftime("%Y-%m-%d")
            if granularity == "day"
            else self.month
        )

    def evidence_unit(self, granularity: str) -> str:
        return (
            f"{self.bucket(granularity)}|{self.cluster_key}|"
            f"{self.company_key}|{self.location_key}"
        )


class AnalysisService:
    MIN_TREND_RECORDS = 10
    MIN_TREND_MONTHS = 2
    MIN_EMERGING_COUNT = 2
    MIN_STANDARD_JOB_SOURCES = 2
    WINDOW_CONFIG = {
        TrendWindow.days_15: ("近 15 天", "day", 15),
        TrendWindow.month_1: ("近 1 个月", "day", 30),
        TrendWindow.months_3: ("近 3 个月", "month", 3),
        TrendWindow.months_6: ("近 6 个月", "month", 6),
    }
    STACK_LABELS = {
        "backend": "后端开发",
        "frontend": "前端开发",
        "fullstack": "全栈开发",
        "data": "数据工程",
        "ai": "人工智能",
        "mobile": "移动开发",
        "devops": "云原生与运维",
        "embedded": "嵌入式",
        "test": "测试与质量",
        "product": "产品与业务",
        "other": "其他",
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def overview(
        self,
        *,
        window: TrendWindow,
        keyword: str | None,
        city: str | None,
    ) -> AnalysisOverview:
        observed = await self._load_observed_jobs(keyword=keyword, city=city)
        window_label, granularity, length = self.WINDOW_CONFIG[window]
        labels = self._window_labels(observed, granularity, length)
        raw_in_window = [
            item for item in observed if item.bucket(granularity) in labels
        ]
        in_window = self._deduplicate_observed(raw_in_window, granularity)
        facts = await self._load_verified_facts({item.row.id for item in raw_in_window})
        fact_counts = self._fact_month_counts(
            facts,
            {item.row.id: item for item in raw_in_window},
            granularity,
        )
        emerging = self._emerging_skills(
            facts,
            fact_counts,
            labels,
            {item.row.id: item for item in raw_in_window},
            granularity,
        )
        quality = self._quality(
            observed=raw_in_window,
            deduplicated=in_window,
            facts=facts,
            granularity=granularity,
        )
        if fact_counts and not self._has_comparison_baseline(fact_counts, labels):
            quality.insufficient_data = True
            quality.notes.append(
                "对比期缺少已确认技能事实，不输出新兴技能增长结论。"
            )
        heatmap_skills = [item.skill for item in emerging[:8]] or self._top_skill_names(facts, 8)
        salaries = [item.salary_k for item in in_window if item.salary_k is not None]
        return AnalysisOverview(
            window=window,
            window_label=window_label,
            granularity=granularity,
            stats=AnalysisStats(
                total_jobs=len(in_window),
                new_skills=len(emerging),
                average_salary_k=(
                    round(sum(salaries) / len(salaries), 1) if salaries else None
                ),
                active_cities=len({item.row.city for item in in_window if item.row.city}),
            ),
            months=labels,
            job_demand=self._job_demand(in_window, labels, granularity),
            salary=self._salary_trends(in_window, labels, granularity),
            heatmap_skills=heatmap_skills,
            heatmap=self._heatmap(fact_counts, labels, heatmap_skills),
            locations=[
                LocationDemand(city=name, value=count)
                for name, count in Counter(
                    item.row.city for item in in_window if item.row.city
                ).most_common(10)
            ],
            emerging_skills=emerging,
            data_quality=quality,
            baseline=await self._load_reference_baseline(),
        )

    async def job_insights(
        self, *, skill: str | None, limit: int, user_id: int
    ) -> JobInsightsResponse:
        observed = await self._load_observed_jobs(keyword=None, city=None)
        record_month = {item.row.id: item.month for item in observed}
        facts = await self._load_verified_facts(set(record_month))
        quality = self._quality(
            observed=observed,
            deduplicated=self._deduplicate_observed(observed, "month"),
            facts=facts,
            granularity="month",
        )

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
            baseline=self._build_reference_baseline(
                standard_jobs=standard_jobs,
                source_ids=source_ids,
                facts=facts,
            ),
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
        mappings = dict((await self.db.execute(
            select(StandardJobSource.source_id, StandardJobSource.standard_job_id)
            .where(StandardJobSource.source_type == "raw")
        )).all())
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
            title_key = self._normalize_key(row.standardized_title or row.title)
            company_key = self._normalize_key(row.company or document.company)
            city_key = self._normalize_key(row.city)
            result.append(ObservedJob(
                row=row,
                observed_at=observed_at or row.created_at,
                used_fallback_time=observed_at is None,
                salary_k=self.parse_salary_k(row.salary_text),
                cluster_key=(
                    f"standard:{mappings[row.id]}"
                    if row.id in mappings
                    else f"fallback:{title_key}|{company_key}|{city_key}"
                ),
                company_key=company_key or f"unknown:{row.id}",
                location_key=city_key or "unknown",
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

    async def _load_reference_baseline(self) -> AnalysisBaseline:
        standard_jobs = list((await self.db.execute(
            select(StandardJob)
            .where(
                StandardJob.status == "active",
                StandardJob.source_count >= self.MIN_STANDARD_JOB_SOURCES,
            )
            .order_by(StandardJob.source_count.desc(), StandardJob.name)
        )).scalars())
        sources = list((await self.db.execute(
            select(StandardJobSource).where(StandardJobSource.source_type == "raw")
        )).scalars())
        source_ids: dict[int, set[int]] = defaultdict(set)
        for source in sources:
            source_ids[source.standard_job_id].add(source.source_id)
        raw_ids = {
            raw_id
            for standard in standard_jobs
            for raw_id in source_ids.get(standard.id, set())
        }
        facts = await self._load_verified_facts(raw_ids)
        return self._build_reference_baseline(
            standard_jobs=standard_jobs,
            source_ids=source_ids,
            facts=facts,
        )

    def _build_reference_baseline(
        self,
        *,
        standard_jobs: list[StandardJob],
        source_ids: dict[int, set[int]],
        facts: list[tuple[JobSkillFact, Skill]],
    ) -> AnalysisBaseline:
        skills_by_raw: dict[int, list[str]] = defaultdict(list)
        for fact, skill in facts:
            if fact.raw_job_record_id:
                skills_by_raw[fact.raw_job_record_id].append(skill.name)

        job_standards: list[JobReferenceStandard] = []
        stack_jobs: Counter[str] = Counter()
        stack_sources: Counter[str] = Counter()
        stack_skills: dict[str, Counter[str]] = defaultdict(Counter)
        for standard in standard_jobs:
            skill_counts = Counter(
                skill_name
                for raw_id in source_ids.get(standard.id, set())
                for skill_name in skills_by_raw.get(raw_id, [])
            )
            core_skills = [name for name, _ in skill_counts.most_common(8)]
            stack_key = standard.stack or "other"
            stack_jobs[stack_key] += 1
            stack_sources[stack_key] += standard.source_count
            stack_skills[stack_key].update(skill_counts)
            job_standards.append(JobReferenceStandard(
                id=standard.id,
                name=standard.name,
                stack=stack_key,
                stack_label=self._stack_label(stack_key),
                level=standard.level,
                aliases=list(standard.aliases or []),
                core_skills=core_skills,
                source_count=standard.source_count,
                description=standard.description,
                first_seen_at=standard.first_seen_at,
                last_seen_at=standard.last_seen_at,
            ))

        technology_stacks = [
            TechnologyStackBaseline(
                key=stack_key,
                label=self._stack_label(stack_key),
                standard_job_count=job_count,
                source_count=stack_sources[stack_key],
                top_skills=[
                    name for name, _ in stack_skills[stack_key].most_common(8)
                ],
            )
            for stack_key, job_count in sorted(
                stack_jobs.items(),
                key=lambda item: (-item[1], self._stack_label(item[0])),
            )
        ]
        unique_skills = {skill.id for _, skill in facts}
        baseline_at = max(
            (standard.last_seen_at for standard in standard_jobs),
            default=None,
        )
        return AnalysisBaseline(
            version="standard-job-v1",
            source_note=(
                "来源于 MySQL 标准岗位、岗位来源映射及已确认技能事实；"
                "仅纳入至少 2 条独立来源的有效标准岗位。"
            ),
            minimum_source_count=self.MIN_STANDARD_JOB_SOURCES,
            standard_job_count=len(job_standards),
            technology_stack_count=len(technology_stacks),
            verified_skill_count=len(unique_skills),
            verified_fact_count=len(facts),
            baseline_at=baseline_at,
            technology_stacks=technology_stacks,
            job_standards=job_standards,
        )

    def _quality(
        self,
        *,
        observed: list[ObservedJob],
        deduplicated: list[ObservedJob],
        facts: list[tuple[JobSkillFact, Skill]],
        granularity: str,
    ) -> AnalysisDataQuality:
        dates = [item.observed_at for item in observed]
        observed_months = len({item.month for item in observed})
        observed_periods = len({
            item.bucket(granularity)
            for item in observed
        })
        insufficient = (
            len(deduplicated) < self.MIN_TREND_RECORDS
            or observed_periods < self.MIN_TREND_MONTHS
        )
        notes: list[str] = []
        if len(deduplicated) < self.MIN_TREND_RECORDS:
            notes.append(f"有效岗位样本少于 {self.MIN_TREND_RECORDS} 条。")
        if observed_periods < self.MIN_TREND_MONTHS:
            period_name = "统计日" if granularity == "day" else "统计月"
            notes.append(
                f"有效时间跨度少于 {self.MIN_TREND_MONTHS} 个{period_name}，"
                "暂不适合解释增长趋势。"
            )
        if any(item.used_fallback_time for item in observed):
            notes.append("部分岗位缺少发布时间，已回退使用导入时间。")
        duplicate_records = max(0, len(observed) - len(deduplicated))
        if duplicate_records:
            period_basis = "统计日" if granularity == "day" else "月份"
            notes.append(
                f"已按{period_basis}、岗位簇、企业和地点合并 {duplicate_records} 条重复观测，"
                "避免转载放大趋势。"
            )
        return AnalysisDataQuality(
            total_records=len(observed),
            deduplicated_records=len(deduplicated),
            duplicate_records=duplicate_records,
            independent_job_clusters=len({item.cluster_key for item in deduplicated}),
            independent_companies=len({
                item.company_key
                for item in deduplicated
                if not item.company_key.startswith("unknown:")
            }),
            valid_time_records=sum(not item.used_fallback_time for item in observed),
            fallback_time_records=sum(item.used_fallback_time for item in observed),
            valid_salary_records=sum(item.salary_k is not None for item in observed),
            verified_skill_facts=len(facts),
            observed_months=observed_months,
            observed_periods=observed_periods,
            period_unit=granularity,
            coverage_start=min(dates) if dates else None,
            coverage_end=max(dates) if dates else None,
            insufficient_data=insufficient,
            notes=notes,
        )

    @staticmethod
    def _normalize_key(value: str | None) -> str:
        return re.sub(r"\s+", "", (value or "").strip().casefold())

    @classmethod
    def _stack_label(cls, key: str) -> str:
        return cls.STACK_LABELS.get(key, key or cls.STACK_LABELS["other"])

    @staticmethod
    def _deduplicate_observed(
        observed: list[ObservedJob],
        granularity: str,
    ) -> list[ObservedJob]:
        grouped: dict[str, ObservedJob] = {}
        for item in observed:
            evidence_unit = item.evidence_unit(granularity)
            current = grouped.get(evidence_unit)
            if current is None or (
                current.used_fallback_time and not item.used_fallback_time
            ):
                grouped[evidence_unit] = item
        return sorted(
            grouped.values(),
            key=lambda item: (item.observed_at, item.row.id),
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
    def _window_labels(
        observed: list[ObservedJob],
        granularity: str,
        length: int,
    ) -> list[str]:
        anchor = max((item.observed_at for item in observed), default=datetime.utcnow())
        if granularity == "day":
            return [
                (anchor - timedelta(days=offset)).strftime("%Y-%m-%d")
                for offset in range(length - 1, -1, -1)
            ]
        labels: list[str] = []
        for offset in range(length - 1, -1, -1):
            absolute = anchor.year * 12 + anchor.month - 1 - offset
            labels.append(f"{absolute // 12:04d}-{absolute % 12 + 1:02d}")
        return labels

    @staticmethod
    def _job_demand(
        observed: list[ObservedJob],
        labels: list[str],
        granularity: str,
    ) -> list[TrendSeries]:
        names = Counter(item.row.standardized_title or item.row.title for item in observed)
        result: list[TrendSeries] = []
        for name, _ in names.most_common(5):
            counts = Counter(
                item.bucket(granularity)
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
        observed: list[ObservedJob],
        labels: list[str],
        granularity: str,
    ) -> list[TrendSeries]:
        valid = [item for item in observed if item.salary_k is not None]
        groups = Counter(item.row.city or "全国" for item in valid)
        result: list[TrendSeries] = []
        for city, _ in groups.most_common(5):
            by_month: dict[str, list[float]] = defaultdict(list)
            for item in valid:
                if (item.row.city or "全国") == city and item.salary_k is not None:
                    by_month[item.bucket(granularity)].append(item.salary_k)
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
        facts: list[tuple[JobSkillFact, Skill]],
        observed_by_raw: dict[int, ObservedJob],
        granularity: str,
    ) -> dict[str, Counter[str]]:
        units: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for fact, skill in facts:
            observed = observed_by_raw.get(fact.raw_job_record_id or -1)
            if observed:
                units[skill.name][observed.bucket(granularity)].add(
                    observed.evidence_unit(granularity)
                )
        return {
            skill: Counter({month: len(values) for month, values in by_month.items()})
            for skill, by_month in units.items()
        }

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
        observed_by_raw: dict[int, ObservedJob],
        granularity: str,
    ) -> list[EmergingSkill]:
        if not self._has_comparison_baseline(counts, labels):
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
            current_companies: set[str] = set()
            previous_companies: set[str] = set()
            for fact, fact_skill in facts:
                if fact_skill.name != name:
                    continue
                observed = observed_by_raw.get(fact.raw_job_record_id or -1)
                if observed is None or observed.company_key.startswith("unknown:"):
                    continue
                observed_period = observed.bucket(granularity)
                if observed_period in current_labels:
                    current_companies.add(observed.company_key)
                if observed_period in previous_labels:
                    previous_companies.add(observed.company_key)
            # A zero count has no denominator, while a single-company
            # comparison is too fragile to support a market growth claim.
            # Preserve the observation and its evidence, but withhold the
            # percentage until both periods have independent-company support.
            comparable = (
                previous > 0
                and len(previous_companies) >= 2
                and len(current_companies) >= 2
            )
            growth = (
                round((current - previous) * 100 / previous, 1)
                if comparable
                else None
            )
            result.append(EmergingSkill(
                id=skill_by_name[name].id,
                skill=name,
                category=skill_by_name[name].category,
                growth=growth,
                stage=(
                    "新出现"
                    if previous == 0
                    else "待观察"
                    if growth is None
                    else "成长期" if growth >= 50 else "成熟期"
                ),
                sparkline=[monthly[label] for label in labels[-6:]],
                current_count=current,
                previous_count=previous,
                current_companies=len(current_companies),
                previous_companies=len(previous_companies),
                evidence_note=(
                    f"本期 {current} 个独立岗位簇、{len(current_companies)} 家企业；"
                    f"上期 {previous} 个独立岗位簇、{len(previous_companies)} 家企业"
                    + (
                        "；独立企业不足 2 家，暂不计算增长率"
                        if previous > 0 and not comparable
                        else ""
                    )
                ),
            ))
        return sorted(
            result,
            key=lambda item: (
                item.growth is None,
                -(item.growth or 0),
                -item.current_count,
                item.skill,
            ),
        )

    @staticmethod
    def _has_comparison_baseline(
        counts: dict[str, Counter[str]],
        labels: list[str],
    ) -> bool:
        if len(labels) < 2:
            return False
        observed_fact_months = {
            month
            for monthly in counts.values()
            for month, count in monthly.items()
            if count > 0
        }
        window = min(3, max(1, len(labels) // 2))
        current_labels = set(labels[-window:])
        previous_labels = set(labels[-2 * window:-window])
        return bool(
            observed_fact_months & current_labels
            and observed_fact_months & previous_labels
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
            standard_source_ids = source_ids.get(standard.id, set())
            previous_source_ids = {
                raw_id
                for raw_id in standard_source_ids
                if record_month.get(raw_id) in previous_months
            }
            current_source_ids = {
                raw_id
                for raw_id in standard_source_ids
                if record_month.get(raw_id) in current_months
            }
            # A capability delta is only meaningful when the same standard
            # job has observations on both sides of the comparison. Treating
            # a one-sided first observation as a full set of additions is a
            # baseline-availability error, not a real dynamic update.
            if not previous_source_ids or not current_source_ids:
                continue
            previous: Counter[str] = Counter()
            current: Counter[str] = Counter()
            for raw_id in standard_source_ids:
                month = record_month.get(raw_id)
                target = current if month in current_months else previous
                for name in skill_rows.get(raw_id, []):
                    target[name] += 1
            previous_total = len(previous_source_ids)
            current_total = len(current_source_ids)
            added = sorted(
                name
                for name in current
                if not previous[name] and current[name] / current_total >= 0.5
            )
            removed = sorted(
                name
                for name in previous
                if not current[name] and previous[name] / previous_total >= 0.5
            )
            modified = sorted(
                name
                for name in set(previous) & set(current)
                if abs(
                    current[name] / current_total
                    - previous[name] / previous_total
                ) >= 0.5
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
