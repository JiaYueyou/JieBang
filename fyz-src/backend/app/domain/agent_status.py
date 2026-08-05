"""Shared persisted status contracts for Agent runs and asynchronous tasks."""

from enum import Enum


class AsyncTaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class AgentRunStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    degraded = "degraded"
    failed = "failed"
    cancelled = "cancelled"
