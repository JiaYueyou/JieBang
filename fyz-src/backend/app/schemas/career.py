from pydantic import BaseModel, Field

from app.core.agent_runtime import (
    CareerAnalysisOutput,
    CareerAnalysisRequest,
    CareerRecommendation,
    LearningStep,
    ResumeProfile,
)


class ResumeExtractionResponse(BaseModel):
    filename: str
    text: str
    character_count: int
    warnings: list[str] = Field(default_factory=list)


class CareerAnalysisResponse(CareerAnalysisOutput):
    agent_run_id: str
    agent_status: str


__all__ = [
    "CareerAnalysisRequest",
    "CareerAnalysisResponse",
    "CareerRecommendation",
    "LearningStep",
    "ResumeProfile",
    "ResumeExtractionResponse",
]
