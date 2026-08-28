from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class MatchEvidenceResponse(BaseModel):
    id: int
    evidence_type: str
    skill_name: str
    evidence_text: str
    source_ref: dict


class MatchResponse(BaseModel):
    id: int
    resume_id: int
    job_id: int
    job_title: str
    job_department: str = ""
    job_level: str = ""
    score: int
    matched: list[str]
    missing: list[str]
    algorithm_version: str
    urgent: bool = False
    evidence: list[MatchEvidenceResponse] = Field(default_factory=list)


class ResumeSkillDetailResponse(BaseModel):
    name: str
    category: str
    confidence: float
    evidence_text: str
    extraction_method: str


class ResumeCreatedResponse(BaseModel):
    id: int
    name: str
    filename: str
    skills: list[str]
    warnings: list[str]
    matches: list[MatchResponse]


class TalentResponse(BaseModel):
    id: int
    resume_id: int
    match_id: int
    name: str
    position: str
    score: int
    isNew: bool
    experience: str
    education: str
    department: str
    matched: list[str]
    missing: list[str]
    targetJobs: list[str]
    targetJobIds: list[int]
    resumeFile: str
    uploadDate: str
    urgent: bool = False
    company: str = ""
    location: str = ""
    phone: str = ""
    email: str = ""
    matches: list[MatchResponse] = Field(default_factory=list)


class TalentDetailResponse(TalentResponse):
    file_size: int
    content_type: str | None = None
    parsed_text: str = ""
    profile: dict = Field(default_factory=dict)
    parse_warnings: list[str] = Field(default_factory=list)
    skills: list[ResumeSkillDetailResponse] = Field(default_factory=list)
    matches: list[MatchResponse] = Field(default_factory=list)


class ResumeMatchRequest(BaseModel):
    job_ids: list[int] = Field(min_length=1, max_length=30)


class TalentUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=160)
    current_position: str = Field(default="", max_length=120)
    experience: str = Field(default="", max_length=100)
    education: str = Field(default="", max_length=100)
    department: str = Field(default="", max_length=100)
    company: str = Field(default="", max_length=150)
    location: str = Field(default="", max_length=100)

    @field_validator("name", "phone", "email", "current_position", "experience", "education", "department", "company", "location", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str:
        return str(value or "").strip()


class MatchExplanationResponse(BaseModel):
    match_id: int
    resume_id: int
    job_id: int
    job_title: str
    score: int
    matched_skills: list[str]
    missing_skills: list[str]
    summary: str
    strengths: list[dict]
    gaps: list[dict]
    risks: list[dict]
    interview_suggestions: list[str]
    generation_mode: str
    warnings: list[str]
    agent_run_id: str
    evidence: list[MatchEvidenceResponse] = Field(default_factory=list)
