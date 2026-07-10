"""智能 JD 生成 Agent 的请求、草稿与审计响应。"""

from datetime import datetime
from enum import Enum

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.skill import TaskStatusResponse


class JDGenerationMode(str, Enum):
    requirements = "requirements"
    profile = "profile"


class GenerateJDRequest(BaseModel):
    mode: JDGenerationMode = JDGenerationMode.requirements
    title: str = Field(min_length=1, max_length=120)
    level: str | None = Field(default=None, max_length=30)
    department: str | None = Field(default=None, max_length=100)
    skills_input: str = Field(default="", max_length=3000)
    location: str | None = Field(default=None, max_length=100)
    company: str | None = Field(default=None, max_length=150)
    headcount: int | None = Field(default=None, ge=1, le=10000)


class GeneratedJDDraft(BaseModel):
    """尚未发布、可由管理员修改的岗位草稿。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    standardized_title: str | None = Field(default=None, max_length=120)
    level: str = Field(min_length=1, max_length=30)
    department: str = Field(min_length=1, max_length=100)
    responsibilities: list[str] = Field(min_length=1, max_length=8)
    requirements: list[str] = Field(min_length=1, max_length=8)
    skills: list[str] = Field(default_factory=list, max_length=20)
    bonus_skills: list[str] = Field(default_factory=list, max_length=12)
    jd_text: str = Field(min_length=1, max_length=12000)
    assumptions: list[str] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=8)
    generation_mode: str = Field(pattern="^(llm|template)$")


class LLMGeneratedJDDraft(BaseModel):
    """仅包含模型可生成字段的宽容接收契约。

    最终草稿中的岗位名称、职级、部门和生成方式由服务端控制，不能由模型覆盖。
    这里允许模型省略可回填字段，以便将不完整但可用的响应合并到安全模板中。
    """

    model_config = ConfigDict(extra="ignore")

    standardized_title: str | None = Field(default=None, max_length=120)
    title: str | None = Field(default=None, max_length=120)
    responsibilities: Any = Field(default_factory=list)
    requirements: Any = Field(default_factory=list)
    skills: Any = Field(default_factory=list)
    bonus_skills: Any = Field(default_factory=list)
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


class JDGenerationTaskResponse(BaseModel):
    task: TaskStatusResponse
    agent_run_id: str


class AgentRunResponse(BaseModel):
    id: str
    agent_type: str
    provider: str
    model: str
    prompt_version: str
    input_summary: str
    structured_output: dict | None
    status: str
    duration_ms: int | None
    retry_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    finished_at: datetime | None
