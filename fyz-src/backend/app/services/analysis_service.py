"""基于 MySQL 可追溯事实的岗位洞察与趋势统计。"""

from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AnalysisBaselineSkill,
    AnalysisBaselineSnapshot,
    AnalysisInsightDecision,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    StandardJob,
    StandardJobSource,
)
from app.core.exceptions import ResourceNotFoundError
from app.core.database import TESTING
from app.core.time import utc_now_naive
from app.domain.skill_dictionary import HISTORICALLY_ESTABLISHED_SKILLS
from app.domain.job_standardizer import normalize_city_names
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
    JobReferenceStandardPage,
    JobInsightsResponse,
    LocationDemand,
    TechnologyStackBaseline,
    TrendWindow,
    TrendSeries,
)


_REFERENCE_BASELINE_CACHE_TTL_SECONDS = 60
_reference_baseline_cache: dict[str, tuple[float, AnalysisBaseline]] = {}


@dataclass(frozen=True)
class ObservedJob:
    row: RawJobRecord
    observed_at: datetime
    used_fallback_time: bool
    salary_k: float | None
    cluster_key: str
    company_key: str
    location_key: str
    source_key: str

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
    MIN_VERIFIED_FACTS = 20
    MIN_BASELINE_FACTS = 12
    MIN_BASELINE_SOURCES = 2
    # Legacy thresholds retained for compatibility with the older helper
    # methods; overview() uses the tiered NEW_SKILL_* rules below.
    MIN_EMERGING_COUNT = 10
    MIN_EMERGING_COMPANIES = 3
    MIN_EMERGING_SOURCES = 2
    MIN_EMERGING_PERIODS = 2
    MIN_EMERGING_CANDIDATE_COUNT = 2
    MIN_EMERGING_CANDIDATE_PERIODS = 2
    MIN_NEW_JOB_CLUSTERS = 3
    MIN_NEW_JOB_COMPANIES = 2
    MIN_NEW_JOB_SOURCES = 2
    MIN_NEW_JOB_PERIODS = 2
    JOB_MATURE_MIN_CLUSTERS = 5
    JOB_MATURE_MIN_PERIODS = 3
    JOB_ESTABLISHED_MIN_CLUSTERS = 3
    JOB_ESTABLISHED_MIN_PERIODS = 2
    NEW_SKILL_STRONG_MIN_CLUSTERS = 3
    NEW_SKILL_STRONG_MIN_COMPANIES = 2
    NEW_SKILL_STRONG_MIN_SOURCES = 2
    NEW_SKILL_STRONG_MIN_PERIODS = 2
    NEW_SKILL_MIN_CONFIDENCE = 0.75
    NEW_SKILL_MEDIUM_MIN_CLUSTERS = 2
    NEW_SKILL_MEDIUM_MIN_PERIODS = 2
    EMERGING_CANDIDATE_CATEGORIES = {
        "programming_language", "framework", "tool", "library", "database",
        "cloud", "人工智能", "Machine Learning", "通信技术", "技术平台",
        "domain_knowledge",
    }
    EMERGING_CANDIDATE_EXCLUDED = {
        "数据分析", "Excel", "Word", "PPT", "办公软件", "沟通能力",
        "商务谈判", "产品运营", "项目管理", "区域覆盖", "数据敏感度",
    }
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
        emerging_page: int = 1,
        emerging_page_size: int = 10,
        new_job_page: int = 1,
        new_job_page_size: int = 10,
        new_job_keyword: str | None = None,
    ) -> AnalysisOverview:
        observed = await self._load_observed_jobs(keyword=keyword, city=city)
        window_label, granularity, length = self.WINDOW_CONFIG[window]
        labels = self._window_labels(observed, granularity, length)
        # 窗口起始时间：观察窗口之前的完整历史数据作为固定基线
        anchor = max((item.observed_at for item in observed), default=utc_now_naive())
        if granularity == "day":
            window_start = anchor - timedelta(days=length - 1)
        else:
            total = anchor.year * 12 + anchor.month - 1 - (length - 1)
            window_start = datetime(total // 12, total % 12 + 1, 1)
        raw_in_window = [item for item in observed if item.observed_at >= window_start]
        baseline_observed = [
            item for item in observed if item.observed_at < window_start
        ]
        in_window = self._deduplicate_observed(raw_in_window, granularity)
        active_baseline, active_baseline_skills = await self._load_active_trend_baseline()

        # A long window often covers the complete imported data set.  In that
        # case, treating "before the selected window" as the only baseline
        # produces an empty comparison and labels established technologies as
        # new.  Reserve the first half of the selected monthly window as an
        # internal comparison period when no earlier history is available.
        signal_observed = raw_in_window
        signal_labels = labels
        used_internal_baseline = False
        if (
            active_baseline is None
            and granularity == "month"
            and not baseline_observed
            and len(labels) >= 4
        ):
            split = max(1, len(labels) // 2)
            baseline_label_set = set(labels[:split])
            signal_label_set = set(labels[split:])
            baseline_observed = [
                item for item in raw_in_window if item.month in baseline_label_set
            ]
            signal_observed = [
                item for item in raw_in_window if item.month in signal_label_set
            ]
            signal_labels = labels[split:]
            used_internal_baseline = bool(baseline_observed and signal_observed)

        window_facts = await self._load_verified_facts(
            {item.row.id for item in raw_in_window}
        )
        window_trend_facts = await self._load_candidate_facts(
            {item.row.id for item in raw_in_window}
        )
        facts = await self._load_verified_facts({item.row.id for item in signal_observed})
        candidate_facts = await self._load_candidate_facts(
            {item.row.id for item in signal_observed}
        )
        # 历史基线：窗口之前全部历史中的已确认事实（固定基线集合）
        baseline_facts = await self._load_verified_facts(
            {item.row.id for item in baseline_observed}
        )
        baseline_candidate_facts = await self._load_candidate_facts(
            {item.row.id for item in baseline_observed}
        )
        baseline_counts = self._fact_month_counts(
            baseline_facts,
            {item.row.id: item for item in baseline_observed},
            granularity,
        )
        # Any reviewable historical occurrence is enough to disprove "new".
        # Verification status can change between imports, so the historical
        # seen-set deliberately combines verified and pending-review facts.
        baseline_skill_names = set(baseline_counts.keys()) | {
            skill.name for _, skill in baseline_candidate_facts
        }
        if active_baseline is not None:
            baseline_skill_names = {
                skill.name for _, skill in active_baseline_skills
            }
        candidate_counts = self._fact_month_counts(
            candidate_facts,
            {item.row.id: item for item in signal_observed},
            granularity,
        )
        candidate_baseline_counts = self._fact_month_counts(
            baseline_candidate_facts,
            {item.row.id: item for item in baseline_observed},
            granularity,
        )
        emerging = self._classify_new_skill_signals(
            candidate_facts,
            candidate_counts,
            signal_labels,
            {item.row.id: item for item in signal_observed},
            granularity,
            baseline_skill_names=(
                set(candidate_baseline_counts) | baseline_skill_names
            ),
        )
        confirmed_emerging_total = sum(item.stage == "新出现" for item in emerging)
        new_jobs, new_job_observation_total = await self._new_jobs(
            signal_observed, baseline_observed
        )
        new_job_needle = (new_job_keyword or "").strip().casefold()
        if new_job_needle:
            new_jobs = [
                job
                for job in new_jobs
                if new_job_needle in " ".join(
                    [job.name, *job.core_skills, job.description]
                ).casefold()
            ]
        # 分页：统计/排序仍基于全量（算法依赖），仅响应与渲染按页截断
        emerging_total = len(emerging)
        heatmap_skills = [
            item.skill for item in emerging
            if item.stage == "新出现"
        ][:8] or self._top_skill_names(facts, 8)
        emerging = emerging[
            (emerging_page - 1) * emerging_page_size :
            (emerging_page - 1) * emerging_page_size + emerging_page_size
        ]
        new_jobs_total = len(new_jobs)
        new_jobs = new_jobs[
            (new_job_page - 1) * new_job_page_size :
            (new_job_page - 1) * new_job_page_size + new_job_page_size
        ]
        quality = self._quality(
            observed=raw_in_window,
            deduplicated=in_window,
            facts=window_facts,
            reviewable_facts=window_trend_facts,
            granularity=granularity,
        )
        if active_baseline is not None:
            baseline_ready = bool(active_baseline.quality_summary.get("is_ready"))
            baseline_notes = ([] if baseline_ready else [
                f"已激活基线 {active_baseline.version} 未通过数据质量校验。"
            ])
        else:
            baseline_ready, baseline_notes = self._baseline_ready(
                baseline_facts=baseline_facts,
                baseline_observed_by_raw={
                    item.row.id: item for item in baseline_observed
                },
            )
            if used_internal_baseline and not baseline_ready:
                baseline_notes.append("已使用所选窗口前半段作为内部历史对照期。")
        if len(facts) < self.MIN_VERIFIED_FACTS:
            quality.insufficient_data = True
        if not baseline_ready:
            quality.insufficient_data = True
            quality.notes.extend(baseline_notes)
        if quality.insufficient_data and emerging:
            quality.notes.append(
                "技能趋势采用分层证据展示；数据不足时仅降低证据等级，不隐藏首次出现信号。"
            )
        salaries = [item.salary_k for item in in_window if item.salary_k is not None]
        reference_baseline = await self._load_reference_baseline(
            historical_end=(active_baseline.period_end if active_baseline else None),
        )
        if active_baseline is not None:
            reference_baseline.version = active_baseline.version
            reference_baseline.baseline_at = active_baseline.activated_at
            reference_baseline.source_note = (
                f"趋势判定使用冻结历史基线 {active_baseline.version}；"
                "岗位成熟度只使用基线截止日前的 MySQL 岗位观测，"
                "按持续月份和独立岗位簇计算。"
            )
        # 岗位明细由独立分页接口按需加载，概览只携带摘要与技术栈。
        reference_baseline.job_standards = []
        return AnalysisOverview(
            window=window,
            window_label=window_label,
            granularity=granularity,
            stats=AnalysisStats(
                total_jobs=len(in_window),
                new_skills=confirmed_emerging_total,
                average_salary_k=(
                    round(sum(salaries) / len(salaries), 1) if salaries else None
                ),
                active_cities=len(self._location_counts(in_window)),
            ),
            months=labels,
            job_demand=self._job_demand(in_window, labels, granularity),
            salary=self._salary_trends(in_window, labels, granularity),
            heatmap_skills=heatmap_skills,
            heatmap=self._heatmap(
                self._fact_month_counts(
                    window_trend_facts,
                    {item.row.id: item for item in raw_in_window},
                    granularity,
                ),
                labels,
                heatmap_skills,
            ),
            locations=[
                LocationDemand(city=name, value=count)
                for name, count in self._location_counts(in_window).most_common(10)
            ],
            emerging_skills=emerging,
            emerging_total=emerging_total,
            new_jobs=new_jobs,
            new_jobs_total=new_jobs_total,
            new_job_observation_total=new_job_observation_total,
            data_quality=quality,
            baseline=reference_baseline,
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
        row.updated_at = utc_now_naive()
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
        requested_cities = normalize_city_names(city)
        city_filter = requested_cities[0] if requested_cities else None
        result: list[ObservedJob] = []
        for row, document in rows:
            if needle and needle not in f"{row.title} {row.standardized_title or ''}".casefold():
                continue
            if city_filter and city_filter not in normalize_city_names(row.city):
                continue
            # 时间解析优先级：已解析的 datetime 字段（posted_at/crawled_at）
            # > 文本字段 > 来源元数据 > 导入时间（最后兜底并标记）。
            raw_time = (
                row.posted_at
                or row.crawled_at
                or self.parse_datetime(
                    row.posted_at_text
                    or document.source_meta.get("posted_at")
                    or row.crawled_at_text
                    or document.source_meta.get("crawled_at")
                )
            )
            observed_at = (
                raw_time
                if isinstance(raw_time, datetime)
                else self.parse_datetime(raw_time)
            )
            used_fallback_time = observed_at is None
            if observed_at is None:
                observed_at = row.created_at
            elif observed_at.tzinfo is not None:
                # 统一为 naive（UTC）时间，避免 aware/naive 混用比较
                observed_at = observed_at.astimezone(timezone.utc).replace(tzinfo=None)
            title_key = self._normalize_key(row.standardized_title or row.title)
            company_key = self._normalize_key(row.company or document.company)
            city_key = self._normalize_key("|".join(normalize_city_names(row.city)))
            result.append(ObservedJob(
                row=row,
                observed_at=observed_at,
                used_fallback_time=used_fallback_time,
                salary_k=self.parse_salary_k(row.salary_text),
                cluster_key=(
                    f"standard:{mappings[row.id]}"
                    if row.id in mappings
                    else f"fallback:{title_key}|{company_key}|{city_key}"
                ),
                company_key=company_key or f"unknown:{row.id}",
                location_key=city_key or "unknown",
                source_key=self._normalize_key(document.source) or "unknown",
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

    async def _load_candidate_facts(
        self, raw_ids: set[int]
    ) -> list[tuple[JobSkillFact, Skill]]:
        """Load reviewable facts for clearly labelled emerging-skill candidates.

        Candidate signals may include unverified rule extractions, but never
        rejected facts or low-quality/excluded job records.  They are kept
        separate from confirmed trend facts and are rendered as ``待历史核验``.
        """
        if not raw_ids:
            return []
        return list((await self.db.execute(
            select(JobSkillFact, Skill)
            .join(Skill, JobSkillFact.skill_id == Skill.id)
            .join(RawJobRecord, RawJobRecord.id == JobSkillFact.raw_job_record_id)
            .where(
                JobSkillFact.raw_job_record_id.in_(raw_ids),
                or_(
                    JobSkillFact.verification_status == "verified",
                    and_(
                        JobSkillFact.verification_status != "rejected",
                        RawJobRecord.quality_status.in_(("accepted", "warning")),
                        RawJobRecord.is_excluded.is_(False),
                    ),
                ),
                Skill.validation_status.in_(("approved", "pending_review")),
            )
        )).all())

    async def _load_active_trend_baseline(
        self,
    ) -> tuple[AnalysisBaselineSnapshot | None, list[tuple[AnalysisBaselineSkill, Skill]]]:
        snapshot = (await self.db.execute(
            select(AnalysisBaselineSnapshot)
            .where(AnalysisBaselineSnapshot.status == "active")
            .order_by(AnalysisBaselineSnapshot.activated_at.desc(), AnalysisBaselineSnapshot.id.desc())
        )).scalars().first()
        if snapshot is None:
            return None, []
        rows = list((await self.db.execute(
            select(AnalysisBaselineSkill, Skill)
            .join(Skill, AnalysisBaselineSkill.skill_id == Skill.id)
            .where(
                AnalysisBaselineSkill.baseline_id == snapshot.id,
                AnalysisBaselineSkill.segment_key == "all",
            )
        )).all())
        return snapshot, rows

    async def _load_reference_baseline(
        self,
        *,
        observed: list[ObservedJob] | None = None,
        historical_end: date | None = None,
    ) -> AnalysisBaseline:
        cache_key = None if TESTING else (
            historical_end.isoformat() if observed is None and historical_end else (
                "current" if observed is None else None
            )
        )
        if cache_key:
            cached = _reference_baseline_cache.get(cache_key)
            if cached and time.monotonic() - cached[0] < _REFERENCE_BASELINE_CACHE_TTL_SECONDS:
                return cached[1].model_copy(deep=True)
        observed = observed if observed is not None else await self._load_observed_jobs(
            keyword=None, city=None
        )
        standard_jobs = list((await self.db.execute(
            select(StandardJob)
            .where(
                StandardJob.status == "active",
                StandardJob.source_count >= self.MIN_STANDARD_JOB_SOURCES,
            )
            .order_by(StandardJob.source_count.desc(), StandardJob.name)
        )).scalars())
        evidence_by_standard: dict[int, list[ObservedJob]] = defaultdict(list)
        for item in observed:
            if historical_end is not None and item.observed_at.date() > historical_end:
                continue
            if item.cluster_key.startswith("standard:"):
                evidence_by_standard[int(item.cluster_key.split(":", 1)[1])].append(item)
        standard_jobs = [
            standard for standard in standard_jobs
            if evidence_by_standard.get(standard.id)
        ]
        source_ids: dict[int, set[int]] = {
            standard.id: {
                item.row.id for item in evidence_by_standard[standard.id]
            }
            for standard in standard_jobs
        }
        facts = await self._load_verified_facts({
            raw_id for values in source_ids.values() for raw_id in values
        })
        baseline = self._build_reference_baseline(
            standard_jobs=standard_jobs,
            source_ids=source_ids,
            facts=facts,
            evidence_by_standard=evidence_by_standard,
        )
        if cache_key:
            _reference_baseline_cache[cache_key] = (
                time.monotonic(), baseline.model_copy(deep=True)
            )
        return baseline

    async def list_reference_standards(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        stack: str | None,
    ) -> JobReferenceStandardPage:
        active_baseline, _ = await self._load_active_trend_baseline()
        baseline = await self._load_reference_baseline(
            historical_end=(active_baseline.period_end if active_baseline else None)
        )
        needle = (keyword or "").strip().casefold()
        stack_key = (stack or "").strip()
        rows = [
            standard
            for standard in baseline.job_standards
            if (not stack_key or standard.stack == stack_key)
            and (
                not needle
                or needle in " ".join([
                    standard.name,
                    standard.stack_label,
                    *standard.aliases,
                    *standard.core_skills,
                ]).casefold()
            )
        ]
        total = len(rows)
        start = (page - 1) * page_size
        return JobReferenceStandardPage(
            items=rows[start:start + page_size],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size if total else 0,
        )

    def _build_reference_baseline(
        self,
        *,
        standard_jobs: list[StandardJob],
        source_ids: dict[int, set[int]],
        facts: list[tuple[JobSkillFact, Skill]],
        evidence_by_standard: dict[int, list[ObservedJob]] | None = None,
    ) -> AnalysisBaseline:
        evidence_by_standard = evidence_by_standard or {}
        skills_by_raw: dict[int, list[str]] = defaultdict(list)
        for fact, skill in facts:
            if fact.raw_job_record_id:
                skills_by_raw[fact.raw_job_record_id].append(skill.name)

        job_standards: list[JobReferenceStandard] = []
        stack_jobs: Counter[str] = Counter()
        stack_sources: Counter[str] = Counter()
        stack_skills: dict[str, Counter[str]] = defaultdict(Counter)
        for standard in standard_jobs:
            evidence = evidence_by_standard.get(standard.id, [])
            # 岗位成熟度采用总体口径，不按城市或行业切分；同一标准岗位、
            # 企业和月份只计一个持续性证据单元。地域仍保留给需求分布图。
            clusters = {
                f"{item.month}|{item.cluster_key}|{item.company_key}"
                for item in evidence
            }
            companies = {
                item.company_key for item in evidence
                if not item.company_key.startswith("unknown:")
            }
            periods = {item.month for item in evidence}
            maturity_stage = self._job_maturity_stage(
                cluster_count=len(clusters), active_period_count=len(periods)
            )
            skill_counts = Counter(
                skill_name
                for raw_id in source_ids.get(standard.id, set())
                for skill_name in skills_by_raw.get(raw_id, [])
            )
            core_skills = [name for name, _ in skill_counts.most_common(8)]
            stack_key = standard.stack or "other"
            stack_jobs[stack_key] += 1
            stack_sources[stack_key] += len(clusters)
            stack_skills[stack_key].update(skill_counts)
            job_standards.append(JobReferenceStandard(
                id=standard.id,
                name=standard.name,
                stack=stack_key,
                stack_label=self._stack_label(stack_key),
                level=standard.level,
                aliases=list(standard.aliases or []),
                core_skills=core_skills,
                source_count=len(clusters),
                company_count=len(companies),
                active_period_count=len(periods),
                maturity_stage=maturity_stage,
                description=standard.description,
                first_seen_at=min(
                    (item.observed_at for item in evidence),
                    default=standard.first_seen_at,
                ),
                last_seen_at=max(
                    (item.observed_at for item in evidence),
                    default=standard.last_seen_at,
                ),
            ))

        job_standards.sort(key=lambda item: (
            {"mature": 0, "established": 1, "observed": 2}.get(
                item.maturity_stage, 9
            ),
            -item.source_count,
            item.name,
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
            (standard.last_seen_at for standard in job_standards),
            default=None,
        )
        return AnalysisBaseline(
            version="standard-job-v1",
            source_note=(
                "来源于 MySQL 标准岗位、岗位来源映射及已确认技能事实；"
                "仅纳入至少 2 条岗位证据的有效标准岗位，成熟度按持续月份和独立岗位簇判定。"
            ),
            minimum_source_count=self.MIN_STANDARD_JOB_SOURCES,
            standard_job_count=len(job_standards),
            technology_stack_count=len(technology_stacks),
            verified_skill_count=len(unique_skills),
            verified_fact_count=len(facts),
            mature_job_count=sum(
                item.maturity_stage == "mature" for item in job_standards
            ),
            established_job_count=sum(
                item.maturity_stage == "established" for item in job_standards
            ),
            baseline_at=baseline_at,
            technology_stacks=technology_stacks,
            job_standards=job_standards,
        )

    @staticmethod
    def _job_maturity_stage(
        *, cluster_count: int, active_period_count: int
    ) -> str:
        """Classify persistence separately from source-market diversity."""
        if (
            cluster_count >= AnalysisService.JOB_MATURE_MIN_CLUSTERS
            and active_period_count >= AnalysisService.JOB_MATURE_MIN_PERIODS
        ):
            return "mature"
        if (
            cluster_count >= AnalysisService.JOB_ESTABLISHED_MIN_CLUSTERS
            and active_period_count >= AnalysisService.JOB_ESTABLISHED_MIN_PERIODS
        ):
            return "established"
        return "observed"

    def _quality(
        self,
        *,
        observed: list[ObservedJob],
        deduplicated: list[ObservedJob],
        facts: list[tuple[JobSkillFact, Skill]],
        granularity: str,
        reviewable_facts: list[tuple[JobSkillFact, Skill]] | None = None,
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
        if len(facts) < self.MIN_VERIFIED_FACTS:
            notes.append(
                f"当前窗口已确认技能事实少于 {self.MIN_VERIFIED_FACTS} 条。"
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
            reviewable_skill_facts=len(reviewable_facts or facts),
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
        anchor = max((item.observed_at for item in observed), default=utc_now_naive())
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
        groups = AnalysisService._location_counts(valid)
        result: list[TrendSeries] = []
        for city, _ in groups.most_common(5):
            by_month: dict[str, list[float]] = defaultdict(list)
            for item in valid:
                if city in normalize_city_names(item.row.city) and item.salary_k is not None:
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
    def _location_counts(observed: list[ObservedJob]) -> Counter[str]:
        counts: Counter[str] = Counter()
        for item in observed:
            counts.update(normalize_city_names(item.row.city))
        return counts

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
        *,
        baseline_skill_names: set[str],
        baseline_totals: dict[str, int],
        baseline_months: int,
        baseline_company_counts: dict[str, int],
    ) -> list[EmergingSkill]:
        """仅发布满足多源持续性门槛的新增技能。

        - 基线 = 观察窗口之前的完整历史（固定基线集合）；
        已在基线中出现的成熟或增长技能应进入独立的需求变化视图，
        不得混入“新兴技能”列表。
        """
        current_labels = set(labels)
        skill_by_name = {skill.name: skill for _, skill in facts}
        result: list[EmergingSkill] = []
        for name, monthly in counts.items():
            current = sum(monthly[label] for label in labels)
            if current < self.MIN_EMERGING_COUNT:
                continue
            baseline_total = baseline_totals.get(name, 0)
            baseline_avg = round(baseline_total / max(baseline_months, 1), 2)
            current_companies = self._evidence_companies(
                facts, name, observed_by_raw, current_labels, granularity
            )
            current_sources = self._evidence_sources(
                facts, name, observed_by_raw, current_labels, granularity
            )
            current_periods = self._evidence_periods(
                facts, name, observed_by_raw, current_labels, granularity
            )
            is_new = name not in baseline_skill_names
            if (
                not is_new
                or len(current_companies) < self.MIN_EMERGING_COMPANIES
                or len(current_sources) < self.MIN_EMERGING_SOURCES
                or len(current_periods) < self.MIN_EMERGING_PERIODS
            ):
                continue
            window_months = max(len(labels), 1)
            current_avg = round(current / window_months, 2)
            growth = (
                round((current_avg - baseline_avg) * 100 / baseline_avg, 1)
                if baseline_avg > 0
                else None
            )
            stage = "新出现"
            note = (
                f"本期 {current} 个独立岗位簇、{len(current_companies)} 家企业；"
                f"历史基线期共 {baseline_total} 个岗位簇、"
                f"{baseline_company_counts.get(name, 0)} 家企业（约 {baseline_months} 个月）"
            )
            if is_new:
                note += "；历史基线中未出现，判定为新增技能"
            result.append(EmergingSkill(
                id=skill_by_name[name].id,
                skill=name,
                category=skill_by_name[name].category,
                growth=growth,
                stage=stage,
                sparkline=[monthly[label] for label in labels[-6:]],
                current_count=current,
                previous_count=baseline_total,
                current_companies=len(current_companies),
                previous_companies=baseline_company_counts.get(name, 0),
                evidence_note=note,
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

    def _classify_new_skill_signals(
        self,
        facts: list[tuple[JobSkillFact, Skill]],
        counts: dict[str, Counter[str]],
        labels: list[str],
        observed_by_raw: dict[int, ObservedJob],
        granularity: str,
        *,
        baseline_skill_names: set[str],
    ) -> list[EmergingSkill]:
        """Classify every dataset-first-seen technical skill by evidence strength.

        Fact review and market trend evidence answer different questions.  A
        fact may still await manual review while repeated appearances across
        companies, sources and periods already form a useful trend signal.
        Therefore review status is retained as evidence, but is not an all-or-
        nothing display gate.
        """
        current_labels = set(labels)
        skill_by_name = {skill.name: skill for _, skill in facts}
        facts_by_name: dict[str, list[JobSkillFact]] = defaultdict(list)
        for fact, skill in facts:
            facts_by_name[skill.name].append(fact)

        result: list[EmergingSkill] = []
        for name, monthly in counts.items():
            skill = skill_by_name[name]
            if (
                name in baseline_skill_names
                or name in self.EMERGING_CANDIDATE_EXCLUDED
                or skill.category not in self.EMERGING_CANDIDATE_CATEGORIES
            ):
                continue
            current = sum(monthly[label] for label in labels)
            if current < 1:
                continue
            companies = self._evidence_companies(
                facts, name, observed_by_raw, current_labels, granularity
            )
            sources = self._evidence_sources(
                facts, name, observed_by_raw, current_labels, granularity
            )
            periods = self._evidence_periods(
                facts, name, observed_by_raw, current_labels, granularity
            )
            skill_facts = facts_by_name[name]
            average_confidence = (
                sum(float(fact.confidence or 0) for fact in skill_facts)
                / max(len(skill_facts), 1)
            )
            strong = (
                current >= self.NEW_SKILL_STRONG_MIN_CLUSTERS
                and len(companies) >= self.NEW_SKILL_STRONG_MIN_COMPANIES
                and len(sources) >= self.NEW_SKILL_STRONG_MIN_SOURCES
                and len(periods) >= self.NEW_SKILL_STRONG_MIN_PERIODS
                and skill.validation_status == "approved"
                and average_confidence >= self.NEW_SKILL_MIN_CONFIDENCE
            )
            medium = (
                current >= self.NEW_SKILL_MEDIUM_MIN_CLUSTERS
                and len(periods) >= self.NEW_SKILL_MEDIUM_MIN_PERIODS
                and (len(companies) >= 2 or len(sources) >= 2)
            )
            historically_established = name.casefold() in {
                item.casefold() for item in HISTORICALLY_ESTABLISHED_SKILLS
            }
            stage = (
                "成熟技术"
                if historically_established
                else "新出现"
                if strong
                else "新出现·待确认"
                if medium
                else "新出现·单源观察"
            )
            sparkline = [monthly[label] for label in labels[-6:]]
            recent_share = (
                sum(sparkline[-2:]) / current if current else 0
            )
            trend_score = round(min(100, (
                25 * min(current / 5, 1)
                + 25 * min(len(companies) / 3, 1)
                + 20 * min(len(sources) / 2, 1)
                + 20 * min(len(periods) / 2, 1)
                + 10 * recent_share
            )))
            result.append(EmergingSkill(
                id=skill.id,
                skill=name,
                category=skill.category,
                growth=None,
                stage=stage,
                sparkline=sparkline,
                current_count=current,
                previous_count=0,
                current_companies=len(companies),
                previous_companies=0,
                current_sources=len(sources),
                current_periods=len(periods),
                trend_score=trend_score,
                evidence_note=(
                    f"已命中历史成熟技术目录；本期 {current} 个独立岗位簇、"
                    f"{len(companies)} 家企业、{len(sources)} 个来源，覆盖 "
                    f"{len(periods)} 个统计周期。不能因本地冻结基线缺样而标记为新技术。"
                    if historically_established
                    else (
                        f"冻结历史基线中未出现；本期 {current} 个独立岗位簇、"
                        f"{len(companies)} 家企业、{len(sources)} 个来源，覆盖 "
                        f"{len(periods)} 个统计周期，平均抽取置信度 "
                        f"{average_confidence:.0%}。该结论表示数据集中首次出现，"
                        "不等同于技术在行业中首次发明。"
                    )
                ),
            ))
        stage_order = {
            "新出现": 0,
            "新出现·待确认": 1,
            "新出现·单源观察": 2,
            "成熟技术": 3,
        }
        return sorted(
            result,
            key=lambda item: (
                stage_order.get(item.stage, 9),
                -item.trend_score,
                -item.current_count,
                item.skill,
            ),
        )

    def _emerging_skill_candidates(
        self,
        facts: list[tuple[JobSkillFact, Skill]],
        counts: dict[str, Counter[str]],
        labels: list[str],
        observed_by_raw: dict[int, ObservedJob],
        granularity: str,
        *,
        baseline_skill_names: set[str],
        already_reported: set[str],
    ) -> list[EmergingSkill]:
        """Return early signals without lowering the confirmed-emerging bar."""
        current_labels = set(labels)
        skill_by_name = {skill.name: skill for _, skill in facts}
        result: list[EmergingSkill] = []
        for name, monthly in counts.items():
            skill = skill_by_name[name]
            current = sum(monthly[label] for label in labels)
            periods = self._evidence_periods(
                facts, name, observed_by_raw, current_labels, granularity
            )
            if (
                name in baseline_skill_names
                or name in already_reported
                or name in self.EMERGING_CANDIDATE_EXCLUDED
                or skill.category not in self.EMERGING_CANDIDATE_CATEGORIES
                or current < self.MIN_EMERGING_CANDIDATE_COUNT
                or len(periods) < self.MIN_EMERGING_CANDIDATE_PERIODS
            ):
                continue
            companies = self._evidence_companies(
                facts, name, observed_by_raw, current_labels, granularity
            )
            sources = self._evidence_sources(
                facts, name, observed_by_raw, current_labels, granularity
            )
            result.append(EmergingSkill(
                id=skill.id,
                skill=name,
                category=skill.category,
                growth=None,
                stage="待历史核验",
                sparkline=[monthly[label] for label in labels[-6:]],
                current_count=current,
                previous_count=0,
                current_companies=len(companies),
                previous_companies=0,
                evidence_note=(
                    f"本期 {current} 个独立岗位簇、{len(companies)} 家企业、"
                    f"{len(sources)} 个来源，覆盖 {len(periods)} 个统计周期；"
                    "历史基线未覆盖不等同于技术新兴；尚未满足完整历史校验和人工确认，"
                    "仅列为待历史核验信号。"
                ),
            ))
        return sorted(result, key=lambda item: (-item.current_count, item.skill))

    @staticmethod
    def _baseline_company_counts(
        facts: list[tuple[JobSkillFact, Skill]],
        observed_by_raw: dict[int, ObservedJob],
    ) -> dict[str, int]:
        companies: dict[str, set[str]] = defaultdict(set)
        for fact, skill in facts:
            observed = observed_by_raw.get(fact.raw_job_record_id or -1)
            if observed is not None and not observed.company_key.startswith("unknown:"):
                companies[skill.name].add(observed.company_key)
        return {name: len(values) for name, values in companies.items()}

    def _baseline_ready(
        self,
        *,
        baseline_facts: list[tuple[JobSkillFact, Skill]],
        baseline_observed_by_raw: dict[int, ObservedJob],
    ) -> tuple[bool, list[str]]:
        """基线必须有足够已确认事实并覆盖多个来源，避免快照误作历史。"""
        raw_ids = {
            fact.raw_job_record_id
            for fact, _ in baseline_facts
            if fact.raw_job_record_id is not None
        }
        sources = {
            baseline_observed_by_raw[raw_id].source_key
            for raw_id in raw_ids
            if raw_id in baseline_observed_by_raw
            and baseline_observed_by_raw[raw_id].source_key != "unknown"
        }
        notes: list[str] = []
        if len(baseline_facts) < self.MIN_BASELINE_FACTS:
            notes.append(
                f"历史基线已确认技能事实少于 {self.MIN_BASELINE_FACTS} 条，"
                "暂不判定新增技能。"
            )
        if len(sources) < self.MIN_BASELINE_SOURCES:
            notes.append(
                f"历史基线独立来源少于 {self.MIN_BASELINE_SOURCES} 个，"
                "暂不判定新增技能。"
            )
        return not notes, notes

    def _candidate_baseline_ready(self, baseline_observed: list[ObservedJob]) -> bool:
        """Candidate comparison needs historical coverage, not fact confirmation."""
        sources = {
            item.source_key for item in baseline_observed
            if item.source_key != "unknown"
        }
        periods = {item.month for item in baseline_observed}
        return (
            len(baseline_observed) >= self.MIN_TREND_RECORDS
            and len(sources) >= self.MIN_BASELINE_SOURCES
            and len(periods) >= self.MIN_TREND_MONTHS
        )

    @staticmethod
    def _evidence_companies(
        facts: list[tuple[JobSkillFact, Skill]],
        skill_name: str,
        observed_by_raw: dict[int, ObservedJob],
        labels: set[str] | None,
        granularity: str,
    ) -> set[str]:
        """统计某技能在指定时段（labels=None 表示全部）出现的独立企业集合。"""
        companies: set[str] = set()
        for fact, fact_skill in facts:
            if fact_skill.name != skill_name:
                continue
            observed = observed_by_raw.get(fact.raw_job_record_id or -1)
            if observed is None or observed.company_key.startswith("unknown:"):
                continue
            if labels is None or observed.bucket(granularity) in labels:
                companies.add(observed.company_key)
        return companies

    @staticmethod
    def _evidence_sources(
        facts: list[tuple[JobSkillFact, Skill]],
        skill_name: str,
        observed_by_raw: dict[int, ObservedJob],
        labels: set[str] | None,
        granularity: str,
    ) -> set[str]:
        return {
            observed.source_key
            for fact, fact_skill in facts
            if fact_skill.name == skill_name
            and (observed := observed_by_raw.get(fact.raw_job_record_id or -1))
            and observed.source_key != "unknown"
            and (labels is None or observed.bucket(granularity) in labels)
        }

    @staticmethod
    def _evidence_periods(
        facts: list[tuple[JobSkillFact, Skill]],
        skill_name: str,
        observed_by_raw: dict[int, ObservedJob],
        labels: set[str] | None,
        granularity: str,
    ) -> set[str]:
        return {
            observed.bucket(granularity)
            for fact, fact_skill in facts
            if fact_skill.name == skill_name
            and (observed := observed_by_raw.get(fact.raw_job_record_id or -1))
            and (labels is None or observed.bucket(granularity) in labels)
        }

    async def _new_jobs(
        self,
        window_observed: list[ObservedJob],
        baseline_observed: list[ObservedJob],
    ) -> tuple[list[EmergingJobInsight], int]:
        """窗口内出现、但历史基线中不存在的标准岗位 → 新增岗位。

        标准岗位维度使用 ObservedJob.cluster_key（"standard:{id}"），
        与 _load_observed_jobs 的 StandardJobSource 映射保持一致。
        """
        baseline_ids = {
            int(item.cluster_key.split(":", 1)[1])
            for item in baseline_observed
            if item.cluster_key.startswith("standard:")
        }
        window_by_standard: dict[int, list[ObservedJob]] = defaultdict(list)
        for item in window_observed:
            if not item.cluster_key.startswith("standard:"):
                continue
            standard_id = int(item.cluster_key.split(":", 1)[1])
            if standard_id not in baseline_ids:
                window_by_standard[standard_id].append(item)
        if not window_by_standard:
            return [], 0
        standards = list((await self.db.execute(
            select(StandardJob).where(StandardJob.id.in_(window_by_standard.keys()))
        )).scalars())
        raw_ids = {
            item.row.id
            for items in window_by_standard.values()
            for item in items
        }
        facts = await self._load_verified_facts(raw_ids)
        skills_by_raw: dict[int, list[str]] = defaultdict(list)
        for fact, skill in facts:
            if fact.raw_job_record_id:
                skills_by_raw[fact.raw_job_record_id].append(skill.name)
        result: list[EmergingJobInsight] = []
        observation_total = len(window_by_standard)
        for standard in standards:
            items = window_by_standard[standard.id]
            companies = {
                item.company_key for item in items
                if not item.company_key.startswith("unknown:")
            }
            sources = {item.source_key for item in items if item.source_key != "unknown"}
            periods = {item.month for item in items}
            clusters = {
                item.evidence_unit("month")
                for item in items
            }
            # Keep every first-observed standard job in the overview.  The old
            # implementation silently discarded single-source or single-month
            # observations, which made the displayed total describe only a
            # small high-confidence subset rather than the factual number of
            # newly observed jobs.  Confidence and evidence counts retain the
            # distinction between an observation and cross-market confirmation.
            skill_counts = Counter(
                skill_name
                for item in items
                for skill_name in skills_by_raw.get(item.row.id, [])
            )
            result.append(EmergingJobInsight(
                id=standard.id,
                name=standard.name,
                core_skills=[name for name, _ in skill_counts.most_common(8)],
                description=(
                    f"本期 {len(clusters)} 个独立岗位簇、{len(companies)} 家企业、"
                    f"{len(sources)} 个来源、覆盖 {len(periods)} 个月。"
                ),
                confidence=min(100, 40 + len(clusters) * 8 + len(companies) * 10),
                source_count=len(sources),
                first_seen_at=standard.first_seen_at,
                decision=None,
            ))
        # 稳定排序：最新出现优先、来源数多优先，保证分页顺序确定
        result.sort(
            key=lambda item: (
                item.first_seen_at,
                item.source_count,
                item.id,
            ),
            reverse=True,
        )
        return result, observation_total

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
        # Compare two equally sized, recent windows instead of splitting the
        # entire history in half. Old sparse observations (for example 2024)
        # must not dominate a current capability update in 2026.
        window_size = min(2, len(months) // 2)
        previous_months = set(months[-window_size * 2:-window_size])
        current_months = set(months[-window_size:])
        skill_rows: dict[int, list[Skill]] = defaultdict(list)
        for fact, skill in facts:
            if fact.raw_job_record_id and AnalysisService._is_capability_skill(skill):
                skill_rows[fact.raw_job_record_id].append(skill)

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
            previous = Counter(
                skill.name for raw_id in previous_source_ids
                for skill in skill_rows.get(raw_id, [])
            )
            current = Counter(
                skill.name for raw_id in current_source_ids
                for skill in skill_rows.get(raw_id, [])
            )
            previous_total = len(previous_source_ids)
            current_total = len(current_source_ids)
            added = sorted(
                name
                for name, count in current.items()
                if count >= 2
                and current[name] / current_total >= 0.3
                and previous[name] / previous_total <= 0.15
            )
            removed = sorted(
                name for name, count in previous.items()
                if current_total >= 2
                and count >= 2
                and previous[name] / previous_total >= 0.4
                and current[name] / current_total <= 0.15
            )
            strengthened = sorted(
                name
                for name in set(previous) & set(current)
                if previous_total >= 2
                and current_total >= 2
                and previous[name] >= 2
                and current[name] >= 2
                and current[name] / current_total
                    - previous[name] / previous_total >= 0.25
            )
            weakened = sorted(
                name
                for name in set(previous) & set(current)
                if previous_total >= 2
                and current_total >= 2
                and previous[name] >= 2
                and current[name] >= 2
                and previous[name] / previous_total
                    - current[name] / current_total >= 0.25
            )
            modified = sorted([*strengthened, *weakened])
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
                period=(
                    f"{min(previous_months)}—{max(previous_months)} 对比 "
                    f"{min(current_months)}—{max(current_months)}"
                ),
                added=added,
                modified=modified,
                strengthened=strengthened,
                weakened=weakened,
                removed=removed,
                previous_sample_count=previous_total,
                current_sample_count=current_total,
            ))
        result.sort(
            key=lambda item: (
                item.current_sample_count + item.previous_sample_count,
                len(item.added) + len(item.modified) + len(item.removed),
                item.job_id,
            ),
            reverse=True,
        )
        return result[:limit]

    @staticmethod
    def _is_capability_skill(skill: Skill) -> bool:
        """Exclude generic soft-skill labels from technical capability deltas."""
        category = (skill.category or "").strip().casefold()
        excluded = {
            "soft_skill", "软技能", "沟通", "通用能力", "communication",
            "collaboration", "coordination", "language", "语言技能",
            "团队合作", "团队协作",
        }
        return category not in excluded and "软技能" not in category
