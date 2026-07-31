from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class GraphEvidenceInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    evidence_id: str = Field(
        min_length=1,
        max_length=64,
        validation_alias=AliasChoices("evidence_id", "source_id"),
    )
    source: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=2000)


class SkillGraphCompletionInput(BaseModel):
    job_directions: list[str] = Field(default_factory=list, max_length=20)
    skill_area: str = Field(min_length=1, max_length=100)
    tech_stack: str = Field(min_length=1, max_length=100)
    evidence: list[GraphEvidenceInput] = Field(min_length=2, max_length=20)


class KnowledgePointOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    difficulty: Literal["easy", "medium", "hard"]
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(
        min_length=2,
        validation_alias=AliasChoices("evidence_ids", "source_ids"),
    )
    prerequisites: list[str] = Field(default_factory=list)


class TechPointOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    detail: str
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(
        min_length=2,
        validation_alias=AliasChoices("evidence_ids", "source_ids"),
    )
    knowledge_points: list[KnowledgePointOutput] = Field(default_factory=list)


class GraphEnrichmentOutput(BaseModel):
    skill_name: str
    job_directions: list[str] = Field(default_factory=list, max_length=20)
    skill_area: str | None = Field(default=None, max_length=100)
    tech_points: list[TechPointOutput] = Field(default_factory=list)
