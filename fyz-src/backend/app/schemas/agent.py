"""后端 Agent API 响应，并复用独立 Agent 包的输入输出契约。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.agent_runtime import (
    GenerateJDRequest,
    GeneratedJDDraft,
    JDGenerationMode,
    JDGenerationTarget,
    JDInputSuggestion,
    JDInputSuggestionRequest,
    LLMGeneratedJDDraft,
    LLMJDInputSuggestion,
)
from app.core.time import as_utc
from app.domain.agent_status import AgentRunStatus
from app.schemas.skill import TaskStatusResponse


class JDGenerationTaskResponse(BaseModel):
    task: TaskStatusResponse
    agent_run_id: str


class AgentTaskResponse(BaseModel):
    task: TaskStatusResponse
    agent_run_id: str


class MatchExplanationTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    match_id: int


class AgentRunResponse(BaseModel):
    id: str
    agent_type: str
    provider: str
    model: str
    prompt_version: str
    input_summary: str
    structured_output: dict | None
    status: AgentRunStatus
    duration_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    retry_count: int
    error_code: str | None
    error_message: str | None
    created_by: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    _utc_times = field_validator(
        "created_at", "started_at", "finished_at", mode="before"
    )(as_utc)


__all__ = [
    "JDGenerationMode",
    "JDGenerationTarget",
    "GenerateJDRequest",
    "GeneratedJDDraft",
    "JDInputSuggestionRequest",
    "JDInputSuggestion",
    "LLMGeneratedJDDraft",
    "LLMJDInputSuggestion",
    "JDGenerationTaskResponse",
    "AgentRunResponse",
    "AgentTaskResponse",
    "MatchExplanationTaskRequest",
]
