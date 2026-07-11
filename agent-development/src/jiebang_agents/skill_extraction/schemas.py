from pydantic import BaseModel, Field


class LLMDiscoveredSkill(BaseModel):
    name: str
    category: str
    kind: str = Field(pattern="^(required|preferred)$")
    confidence: float = Field(ge=0, le=1)
    evidence: str


class LLMDiscoveredSkills(BaseModel):
    skills: list[LLMDiscoveredSkill] = Field(default_factory=list)
