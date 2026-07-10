"""岗位洞察与趋势分析响应契约。"""

from datetime import datetime

from enum import Enum

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


class EmergingSkill(BaseModel):
    id: int
    skill: str
    category: str
    growth: float
    stage: str
    sparkline: list[int]
    current_count: int
    previous_count: int


class AnalysisDataQuality(BaseModel):
    total_records: int
    valid_time_records: int
    fallback_time_records: int
    valid_salary_records: int
    verified_skill_facts: int
    observed_months: int
    coverage_start: datetime | None
    coverage_end: datetime | None
    insufficient_data: bool
    notes: list[str] = Field(default_factory=list)


class AnalysisOverview(BaseModel):
    stats: AnalysisStats
    months: list[str]
    job_demand: list[TrendSeries]
    salary: list[TrendSeries]
    heatmap_skills: list[str]
    heatmap: list[HeatmapPoint]
    locations: list[LocationDemand]
    emerging_skills: list[EmergingSkill]
    data_quality: AnalysisDataQuality


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
    removed: list[str]


class JobInsightsResponse(BaseModel):
    emerging_jobs: list[EmergingJobInsight]
    capability_changes: list[CapabilityChangeInsight]
    data_quality: AnalysisDataQuality
