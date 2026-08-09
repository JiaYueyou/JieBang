from datetime import datetime
from pydantic import BaseModel, Field


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
