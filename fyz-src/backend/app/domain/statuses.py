"""Shared status contracts for FYZ tasks, agents, facts, and graph publishing.

Phase 0 freezes vocabulary only. Existing database columns remain strings so
the contracts can be adopted incrementally without a schema migration.
"""

from __future__ import annotations

from enum import Enum
from typing import TypeVar


class StringValueEnum(str, Enum):
    """Enum whose string representation is the persisted wire value."""

    def __str__(self) -> str:
        return self.value

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(item.value for item in cls)


class TaskStatus(StringValueEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class AgentRunStatus(StringValueEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    degraded = "degraded"
    failed = "failed"
    cancelled = "cancelled"


class LegacyVerificationStatus(StringValueEnum):
    """Compatibility values currently persisted by JobSkillFact."""

    unverified = "unverified"
    verified = "verified"
    rejected = "rejected"


class TrustStage(StringValueEnum):
    raw = "raw"
    extracted = "extracted"
    machine_validated = "machine_validated"
    human_approved = "human_approved"
    published = "published"
    rejected = "rejected"
    insufficient_evidence = "insufficient_evidence"
    expired = "expired"


class MachineValidationStatus(StringValueEnum):
    pending = "pending"
    passed = "passed"
    failed = "failed"
    insufficient_evidence = "insufficient_evidence"


class ReviewStatus(StringValueEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PublicationStatus(StringValueEnum):
    draft = "draft"
    ready = "ready"
    published = "published"
    failed = "failed"
    superseded = "superseded"


StatusT = TypeVar("StatusT", bound=StringValueEnum)


TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.queued: frozenset(
        {TaskStatus.running, TaskStatus.failed, TaskStatus.cancelled}
    ),
    TaskStatus.running: frozenset(
        {TaskStatus.succeeded, TaskStatus.failed, TaskStatus.cancelled}
    ),
    TaskStatus.succeeded: frozenset(),
    TaskStatus.failed: frozenset(),
    TaskStatus.cancelled: frozenset(),
}

AGENT_RUN_TRANSITIONS: dict[AgentRunStatus, frozenset[AgentRunStatus]] = {
    AgentRunStatus.queued: frozenset(
        {
            AgentRunStatus.running,
            AgentRunStatus.failed,
            AgentRunStatus.cancelled,
        }
    ),
    AgentRunStatus.running: frozenset(
        {
            AgentRunStatus.succeeded,
            AgentRunStatus.degraded,
            AgentRunStatus.failed,
            AgentRunStatus.cancelled,
        }
    ),
    AgentRunStatus.succeeded: frozenset(),
    AgentRunStatus.degraded: frozenset(),
    AgentRunStatus.failed: frozenset(),
    AgentRunStatus.cancelled: frozenset(),
}


def ensure_transition(
    current: StatusT,
    target: StatusT,
    transitions: dict[StatusT, frozenset[StatusT]],
) -> None:
    """Reject an invalid status transition without mutating application state."""

    if current == target:
        return
    if target not in transitions.get(current, frozenset()):
        raise ValueError(f"invalid status transition: {current.value} -> {target.value}")
