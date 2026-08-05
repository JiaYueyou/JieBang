import pytest

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


def test_phase0_status_values_are_stable():
    assert TaskStatus.values() == (
        "queued",
        "running",
        "succeeded",
        "failed",
        "cancelled",
    )
    assert "success" not in TaskStatus.values()
    assert "success" not in AgentRunStatus.values()
    assert LegacyVerificationStatus.values() == (
        "unverified",
        "verified",
        "rejected",
    )
    assert TrustStage.values() == (
        "raw",
        "extracted",
        "machine_validated",
        "human_approved",
        "published",
        "rejected",
        "insufficient_evidence",
        "expired",
    )
    assert MachineValidationStatus.values() == (
        "pending",
        "passed",
        "failed",
        "insufficient_evidence",
    )
    assert ReviewStatus.values() == ("pending", "approved", "rejected")
    assert PublicationStatus.values() == (
        "draft",
        "ready",
        "published",
        "failed",
        "superseded",
    )


def test_task_transition_contract():
    ensure_transition(TaskStatus.queued, TaskStatus.running, TASK_TRANSITIONS)
    ensure_transition(TaskStatus.running, TaskStatus.succeeded, TASK_TRANSITIONS)

    with pytest.raises(
        ValueError,
        match="invalid status transition: succeeded -> running",
    ):
        ensure_transition(TaskStatus.succeeded, TaskStatus.running, TASK_TRANSITIONS)


def test_agent_degraded_is_a_terminal_outcome():
    ensure_transition(
        AgentRunStatus.running,
        AgentRunStatus.degraded,
        AGENT_RUN_TRANSITIONS,
    )
    assert AGENT_RUN_TRANSITIONS[AgentRunStatus.degraded] == frozenset()
