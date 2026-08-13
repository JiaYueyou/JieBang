"""岗位洞察与趋势分析响应契约。"""

from datetime import datetime

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AnalysisStats(BaseModel):
    total_jobs: int
    new_skills: int
    average_salary_k: float | None
    active_cities: int


class TrendSeries(BaseModel):
    name: str
    values: list[float]


class HeatmapPoint(BaseModel):
    x: int
    y: int
    value: int


class LocationDemand(BaseModel):
    city: str
    value: int


class TrendWindow(str, Enum):
    days_15 = "15d"
    month_1 = "1m"
    months_3 = "3m"
    months_6 = "6m"


class TechnologyStackBaseline(BaseModel):
    key: str
    label: str
    standard_job_count: int
    source_count: int
    top_skills: list[str]


class JobReferenceStandard(BaseModel):
    id: int
    name: str
    stack: str
    stack_label: str
    level: str
    aliases: list[str]
    core_skills: list[str]
    source_count: int
    company_count: int = 0
    active_period_count: int = 0
    maturity_stage: str = "observed"
    description: str
    first_seen_at: datetime
    last_seen_at: datetime


class AnalysisBaseline(BaseModel):
    version: str
    source_note: str
    minimum_source_count: int
    standard_job_count: int
    technology_stack_count: int
    verified_skill_count: int
    verified_fact_count: int
    mature_job_count: int = 0
    established_job_count: int = 0
    baseline_at: datetime | None
    technology_stacks: list[TechnologyStackBaseline]
    job_standards: list[JobReferenceStandard]


class JobReferenceStandardPage(BaseModel):
    items: list[JobReferenceStandard] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
    total_pages: int


class EmergingSkill(BaseModel):
    id: int
    skill: str
    category: str
    growth: float | None = None
    stage: str
    sparkline: list[int]
    current_count: int
    previous_count: int
    current_companies: int
    previous_companies: int
    current_sources: int = 0
    current_periods: int = 0
    trend_score: int = 0
    evidence_note: str


class AnalysisDataQuality(BaseModel):
    total_records: int
    deduplicated_records: int
    duplicate_records: int
    independent_job_clusters: int
    independent_companies: int
    valid_time_records: int
    fallback_time_records: int
    valid_salary_records: int
    verified_skill_facts: int
    reviewable_skill_facts: int
    observed_months: int
    observed_periods: int
    period_unit: str
    coverage_start: datetime | None
    coverage_end: datetime | None
    insufficient_data: bool
    notes: list[str] = Field(default_factory=list)


class AnalysisOverview(BaseModel):
    window: TrendWindow
    window_label: str
    granularity: str
    stats: AnalysisStats
    months: list[str]
    job_demand: list[TrendSeries]
    salary: list[TrendSeries]
    heatmap_skills: list[str]
    heatmap: list[HeatmapPoint]
    locations: list[LocationDemand]
    emerging_skills: list[EmergingSkill]
    emerging_total: int = 0
    new_jobs: list["EmergingJobInsight"] = Field(default_factory=list)
    new_jobs_total: int = 0
    new_job_observation_total: int = 0
    data_quality: AnalysisDataQuality
    baseline: AnalysisBaseline


class EmergingJobInsight(BaseModel):
    id: int
    name: str
    core_skills: list[str]
    description: str
    confidence: int
    source_count: int
    first_seen_at: datetime
    decision: str | None = None


class InsightDecision(str, Enum):
    confirmed = "confirmed"
    ignored = "ignored"
    planned = "planned"


class InsightDecisionRequest(BaseModel):
    decision: InsightDecision
    note: str | None = Field(default=None, max_length=1000)


class InsightDecisionResponse(BaseModel):
    id: int
    insight_type: str
    target_id: int
    decision: InsightDecision
    note: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime


class CapabilityChangeInsight(BaseModel):
    id: int
    job_id: int
    job: str
    period: str
    added: list[str]
    modified: list[str]
    strengthened: list[str] = Field(default_factory=list)
    weakened: list[str] = Field(default_factory=list)
    removed: list[str]
    change_type: Literal["comparison"] = "comparison"
    previous_sample_count: int = 0
    current_sample_count: int = 0


class JobInsightsResponse(BaseModel):
    emerging_jobs: list[EmergingJobInsight]
    capability_changes: list[CapabilityChangeInsight]
    data_quality: AnalysisDataQuality
    baseline: AnalysisBaseline
