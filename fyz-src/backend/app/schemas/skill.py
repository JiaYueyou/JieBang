"""技能抽取与任务 Schema。"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.core.agent_runtime import LLMDiscoveredSkill, LLMDiscoveredSkills


class SkillKind(str, Enum):
    required = "required"
    preferred = "preferred"


class VerificationStatus(str, Enum):
    verified = "verified"
    unverified = "unverified"


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
    status: str
    progress: int
    result: dict | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
