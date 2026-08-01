"""技能抽取与任务 Schema。"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.agent_runtime import LLMDiscoveredSkill, LLMDiscoveredSkills
from app.core.time import as_utc
from app.domain.agent_status import AsyncTaskStatus


class SkillKind(str, Enum):
    required = "required"
    preferred = "preferred"


class VerificationStatus(str, Enum):
    verified = "verified"
    unverified = "unverified"
    rejected = "rejected"


class ExtractedSkill(BaseModel):
    name: str
    category: str
    kind: SkillKind
    confidence: float = Field(ge=0, le=1)
    evidence: str
    extraction_method: str = "rule"


class SkillExtractionOutput(BaseModel):
    skills: list[ExtractedSkill] = Field(default_factory=list)
    llm_enrichment: bool = False
    agent_run_id: str | None = None


class SkillSummary(BaseModel):
    id: int
    name: str
    canonical_name: str
    canonical_key: str
    category: str
    aliases: list[str]
    first_seen_at: datetime
    last_seen_at: datetime


class SkillFactResponse(BaseModel):
    id: int
    skill_id: int
    skill_name: str
    category: str
    kind: SkillKind
    importance: float
    frequency: int
    confidence: float
    evidence_text: str
    verification_status: VerificationStatus
    extraction_method: str
    source_count: int


class SkillFactReviewItem(SkillFactResponse):
    job_id: int | None
    raw_job_record_id: int | None
    job_title: str
    company: str | None
    source: str
    source_url: str | None
    reviewed_by: int | None
    reviewer_name: str | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime


class SkillFactReviewSummary(BaseModel):
    all: int
    unverified: int
    verified: int
    rejected: int


class SkillFactReviewList(BaseModel):
    items: list[SkillFactReviewItem]
    summary: SkillFactReviewSummary


class SkillFactReviewRequest(BaseModel):
    decision: VerificationStatus
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_decision(self):
        if self.decision == VerificationStatus.unverified:
            raise ValueError("审核决定只能是 verified 或 rejected")
        if self.decision == VerificationStatus.rejected and not (self.note or "").strip():
            raise ValueError("驳回时必须填写原因")
        if self.note is not None:
            self.note = self.note.strip() or None
        return self


class SkillFactBatchReviewRequest(SkillFactReviewRequest):
    fact_ids: list[int] = Field(min_length=1, max_length=100)


class SkillFactApproveAllRequest(BaseModel):
    keyword: str | None = Field(default=None, max_length=100)


class SkillFactBatchReviewResult(BaseModel):
    processed_count: int
    skipped_count: int
    fact_ids: list[int]


class JobExtractionResult(BaseModel):
    job_id: int
    facts: list[SkillFactResponse]
    llm_enrichment: bool
    agent_run_id: str | None = None


class DataImportRequest(BaseModel):
    files: list[str] = Field(
        default_factory=lambda: [
            "jd_crawl_ifly.json",
            "jd_crawl_zl.json",
            "jd_crawl2.json",
        ]
    )


class TaskStatusResponse(BaseModel):
    task_id: str
    task_type: str
    status: AsyncTaskStatus
    progress: int
    result: dict | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    _utc_times = field_validator(
        "created_at", "started_at", "finished_at", mode="before"
    )(as_utc)
