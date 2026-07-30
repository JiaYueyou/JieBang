"""Domain rules and shared contracts."""

from app.domain.statuses import (
    AGENT_RUN_TRANSITIONS,
    TASK_TRANSITIONS,
    AgentRunStatus,
    LegacyVerificationStatus,
    MachineValidationStatus,
    PublicationStatus,
    ReviewStatus,
    TaskStatus,
    TrustStage,
    ensure_transition,
)

__all__ = [
    "AGENT_RUN_TRANSITIONS",
    "TASK_TRANSITIONS",
    "AgentRunStatus",
    "LegacyVerificationStatus",
    "MachineValidationStatus",
    "PublicationStatus",
    "ReviewStatus",
    "TaskStatus",
    "TrustStage",
    "ensure_transition",
]
