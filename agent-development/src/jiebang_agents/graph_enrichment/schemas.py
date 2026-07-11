from typing import Literal

from pydantic import BaseModel, Field


class GraphEvidenceInput(BaseModel):
    source_id: int
    source: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=2000)


class SkillGraphCompletionInput(BaseModel):
    job_directions: list[str] = Field(default_factory=list, max_length=20)
    skill_area: str = Field(min_length=1, max_length=100)
    tech_stack: str = Field(min_length=1, max_length=100)
    evidence: list[GraphEvidenceInput] = Field(min_length=2, max_length=20)


class KnowledgePointOutput(BaseModel):
    name: str
    description: str
    difficulty: Literal["easy", "medium", "hard"]
    confidence: float = Field(ge=0, le=1)
    source_ids: list[int] = Field(min_length=2)
    prerequisites: list[str] = Field(default_factory=list)


class TechPointOutput(BaseModel):
    name: str
    detail: str
    confidence: float = Field(ge=0, le=1)
    source_ids: list[int] = Field(min_length=2)
    knowledge_points: list[KnowledgePointOutput] = Field(default_factory=list)


class GraphEnrichmentOutput(BaseModel):
    skill_name: str
    job_directions: list[str] = Field(default_factory=list, max_length=20)
    skill_area: str | None = Field(default=None, max_length=100)
    tech_points: list[TechPointOutput] = Field(default_factory=list)
