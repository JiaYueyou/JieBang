from pydantic import BaseModel, ConfigDict, Field, field_validator


class MatchEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    evidence_type: str
    skill_name: str
    evidence_text: str = Field(max_length=1000)
    source_ref: dict = Field(default_factory=dict)

    @field_validator("evidence_id", mode="before")
    @classmethod
    def normalize_evidence_id(cls, value) -> str:
        return str(value)


class MatchExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    match_id: int
    resume_id: int
    job_id: int
    job_title: str
    score: int = Field(ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    evidence: list[MatchEvidenceInput] = Field(default_factory=list)


class ExplanationItem(BaseModel):
    title: str = Field(max_length=120)
    explanation: str = Field(max_length=600)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("evidence_ids", mode="before")
    @classmethod
    def normalize_evidence_ids(cls, value) -> list[str]:
        return [str(item) for item in (value or [])]


class LLMMatchExplanation(BaseModel):
    summary: str = Field(max_length=1000)
    strengths: list[ExplanationItem] = Field(default_factory=list, max_length=10)
    gaps: list[ExplanationItem] = Field(default_factory=list, max_length=10)
    risks: list[ExplanationItem] = Field(default_factory=list, max_length=8)
    interview_suggestions: list[str] = Field(default_factory=list, max_length=10)


class MatchExplanationOutput(LLMMatchExplanation):
    match_id: int
    resume_id: int
    job_id: int
    job_title: str
    score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    generation_mode: str = Field(pattern="^(llm|template)$")
    warnings: list[str] = Field(default_factory=list)
