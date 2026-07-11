from pydantic import BaseModel, ConfigDict, Field


class CareerAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_text: str = Field(default="", max_length=6000)
    resume_text: str = Field(default="", max_length=20000)
    enterprise_tech: str = Field(default="", max_length=6000)
    internal_jobs: list[str] = Field(default_factory=list, max_length=30)
    target_job_ids: list[int] = Field(default_factory=list, max_length=30)
    time_budget_weeks: int = Field(default=12, ge=1, le=52)


class ResumeProfile(BaseModel):
    current_role: str = Field(default="待确认", max_length=120)
    years_experience: float | None = Field(default=None, ge=0, le=60)
    education: str | None = Field(default=None, max_length=100)
    skills: list[str] = Field(default_factory=list, max_length=50)
    project_highlights: list[str] = Field(default_factory=list, max_length=8)
    strengths: list[str] = Field(default_factory=list, max_length=8)
    assumptions: list[str] = Field(default_factory=list, max_length=8)


class CareerPlanCandidate(BaseModel):
    job_id: int
    job: str
    current_match: int = Field(ge=0, le=100)
    after_match: int = Field(ge=0, le=100)
    recommend_score: int = Field(ge=0, le=100)
    existing: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    internal: bool = False


class LearningStep(BaseModel):
    skill: str
    time: str
    difficulty: str = Field(pattern="^(easy|medium|hard)$")
    resources: list[str] = Field(default_factory=list, max_length=6)


class CareerRecommendation(BaseModel):
    rank: int = Field(ge=1)
    job_id: int
    job: str
    recommend_score: int = Field(ge=0, le=100)
    current_match: int = Field(ge=0, le=100)
    after_match: int = Field(ge=0, le=100)
    existing: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    learning_plan: list[LearningStep] = Field(default_factory=list, max_length=12)
    suggested_project: str = Field(default="", max_length=500)
    total_time: str = Field(default="", max_length=50)
    internal: bool = False
    explanation: str = Field(default="", max_length=1200)


class CareerAnalysisOutput(BaseModel):
    resume_profile: ResumeProfile
    recommendations: list[CareerRecommendation] = Field(default_factory=list, max_length=10)
    warnings: list[str] = Field(default_factory=list, max_length=10)


class LLMRecommendation(BaseModel):
    job_id: int
    learning_plan: list[LearningStep] = Field(default_factory=list, max_length=12)
    suggested_project: str = Field(default="", max_length=500)
    total_time: str = Field(default="", max_length=50)
    explanation: str = Field(default="", max_length=1200)


class LLMCareerAnalysis(BaseModel):
    resume_profile: ResumeProfile = Field(default_factory=ResumeProfile)
    recommendations: list[LLMRecommendation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
