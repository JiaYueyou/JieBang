"""Admin-facing job data quality schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class DataQualitySummary(BaseModel):
    total: int
    accepted: int
    warning: int
    rejected: int
    pending: int
    near_duplicates: int
    excluded: int
    average_quality_score: float
    flag_counts: dict[str, int]


class RawJobQualityItem(BaseModel):
    id: int
    title: str
    standard_job_id: int | None
    standardized_title: str | None
    company: str | None
    source: str
    source_url: str | None
    posted_at: datetime | None
    crawled_at: datetime | None
    posted_at_text: str | None
    crawled_at_text: str | None
    quality_score: float
    freshness_score: float
    source_trust_score: float
    quality_status: str
    quality_flags: list[str]
    dedup_status: str
    near_duplicate_group_id: str | None
    near_duplicate_score: float
    is_excluded: bool
    exclusion_reason: str | None
    quality_evaluated_at: datetime | None


class DataQualityList(BaseModel):
    items: list[RawJobQualityItem]
    summary: DataQualitySummary


class DataQualityDecisionRequest(BaseModel):
    action: str = Field(pattern="^(exclude|restore)$")
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_reason(self):
        if self.action == "exclude" and not (self.reason or "").strip():
            raise ValueError("排除低质量记录时必须填写原因")
        self.reason = (self.reason or "").strip() or None
        return self
