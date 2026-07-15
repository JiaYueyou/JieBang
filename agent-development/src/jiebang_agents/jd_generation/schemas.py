"""JD Generation 的输入与结构化输出契约。"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JDGenerationMode(str, Enum):
    requirements = "requirements"
    profile = "profile"


class JDGenerationTarget(str, Enum):
    public = "public"
    internal = "internal"


class GenerateJDRequest(BaseModel):
    target: JDGenerationTarget = JDGenerationTarget.public
    mode: JDGenerationMode = JDGenerationMode.requirements
    title: str = Field(min_length=1, max_length=120)
    level: str | None = Field(default=None, max_length=30)
    department: str | None = Field(default=None, max_length=100)
    skills_input: str = Field(default="", max_length=3000)
    location: str | None = Field(default=None, max_length=100)
    company: str | None = Field(default=None, max_length=150)
    headcount: int | None = Field(default=None, ge=1, le=10000)
    internal_reason: str | None = Field(default=None, max_length=300)
    receiving_manager: str | None = Field(default=None, max_length=100)


class JDInputSuggestionRequest(BaseModel):
    target: JDGenerationTarget = JDGenerationTarget.public
    mode: JDGenerationMode = JDGenerationMode.requirements
    title: str = Field(min_length=2, max_length=120)
    level: str | None = Field(default=None, max_length=30)
    department: str | None = Field(default=None, max_length=100)


class JDInputSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=120)
    target: JDGenerationTarget
    mode: JDGenerationMode
    suggestions: list[str] = Field(min_length=1, max_length=10)
    generation_mode: str = Field(pattern="^(llm|template)$")
    warnings: list[str] = Field(default_factory=list, max_length=8)


class LLMJDInputSuggestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    suggestions: Any = Field(default_factory=list)
    warnings: Any = Field(default_factory=list)


class GeneratedJDDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    target: JDGenerationTarget
    standardized_title: str | None = Field(default=None, max_length=120)
    level: str = Field(min_length=1, max_length=30)
    department: str = Field(min_length=1, max_length=100)
    responsibilities: list[str] = Field(min_length=1, max_length=8)
    requirements: list[str] = Field(min_length=1, max_length=8)
    skills: list[str] = Field(default_factory=list, max_length=20)
    bonus_skills: list[str] = Field(default_factory=list, max_length=12)
    trainable_skills: list[str] = Field(default_factory=list, max_length=12)
    transfer_profile: list[str] = Field(default_factory=list, max_length=8)
    manager_confirmations: list[str] = Field(default_factory=list, max_length=8)
    jd_text: str = Field(min_length=1, max_length=12000)
    assumptions: list[str] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=8)
    generation_mode: str = Field(pattern="^(llm|template)$")


class LLMGeneratedJDDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    standardized_title: str | None = Field(default=None, max_length=120)
    title: str | None = Field(default=None, max_length=120)
    responsibilities: Any = Field(default_factory=list)
    requirements: Any = Field(default_factory=list)
    skills: Any = Field(default_factory=list)
    bonus_skills: Any = Field(default_factory=list)
    trainable_skills: Any = Field(default_factory=list)
    transfer_profile: Any = Field(default_factory=list)
    manager_confirmations: Any = Field(default_factory=list)
    jd_text: str | None = Field(default=None, max_length=12000)
    assumptions: Any = Field(default_factory=list)
    warnings: Any = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if not normalized.get("title"):
            normalized["title"] = normalized.get("position_name") or normalized.get("job_title")
        return normalized
