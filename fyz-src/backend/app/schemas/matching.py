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
    evidence: list[MatchEvidenceResponse] = Field(default_factory=list)


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
