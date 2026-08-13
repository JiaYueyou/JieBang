"""图谱同步 API 测试（不依赖真实 Neo4j）。"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.skill import TaskStatusResponse


def _mock_task_status(result: dict | None = None) -> TaskStatusResponse:
    return TaskStatusResponse(
        task_id=str(uuid.uuid4()),
        task_type="graph_sync",
        status="succeeded",
        progress=100,
        result=result or {},
        error_code=None,
        error_message=None,
        created_at=datetime.utcnow(),
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )


async def test_sync_graph_requires_auth(client):
    response = await client.post("/api/v1/graph/sync", json={"mode": "full"})
    assert response.status_code == 401


async def test_sync_graph_unauthenticated_detail(client):
    response = await client.post("/api/v1/graph/sync", json={"mode": "full"})
    data = response.json()
    assert data["code"] == 40100


async def test_sync_graph_enrich_disabled(client, auth_headers):
    mock_response = _mock_task_status()
    with patch("app.api.v1.graph.GraphTaskService.create_sync", new=AsyncMock(return_value=mock_response)) as mock_create:
        response = await client.post(
            "/api/v1/graph/sync",
            json={"mode": "full", "enrich_top_skills": False},
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["task_id"] == mock_response.task_id
    assert data["data"]["status"] == "succeeded"
    assert mock_create.call_args.kwargs["enrich_top_skills"] is False


async def test_sync_graph_enrich_enabled(client, auth_headers):
    mock_response = _mock_task_status(
        result={
            "snapshot_id": str(uuid.uuid4()),
            "metadata": {
                "enrichment": {
                    "enabled": True,
                    "candidates_total": 5,
                    "candidates_verified": 3,
                    "candidates_failed": 0,
                    "candidates_skipped": 2,
                    "tech_points_written": 4,
                    "knowledge_points_written": 7,
                }
            },
        }
    )
    with patch("app.api.v1.graph.GraphTaskService.create_sync", new=AsyncMock(return_value=mock_response)) as mock_create:
        response = await client.post(
            "/api/v1/graph/sync",
            json={"mode": "full", "enrich_top_skills": True},
            headers=auth_headers,
        )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["result"]["metadata"]["enrichment"]["candidates_total"] == 5
    assert data["data"]["result"]["metadata"]["enrichment"]["tech_points_written"] == 4
    assert mock_create.call_args.kwargs["enrich_top_skills"] is True


async def test_sync_graph_invalid_mode(client, auth_headers):
    response = await client.post(
        "/api/v1/graph/sync",
        json={"mode": "invalid_mode"},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_sync_graph_default_enrich_true(client, auth_headers):
    mock_response = _mock_task_status()
    with patch("app.api.v1.graph.GraphTaskService.create_sync", new=AsyncMock(return_value=mock_response)) as mock_create:
        response = await client.post(
            "/api/v1/graph/sync",
            json={"mode": "incremental"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    assert mock_create.call_args.kwargs["enrich_top_skills"] is True


async def test_enrichment_generation_runs_eager_task_in_background(client, auth_headers):
    mock_response = _mock_task_status()
    with patch(
        "app.api.v1.graph.GraphTaskService.create_sync",
        new=AsyncMock(return_value=mock_response),
    ) as mock_create:
        response = await client.post(
            "/api/v1/graph/enrichment/generate", headers=auth_headers
        )
    assert response.status_code == 200
    assert mock_create.call_args.kwargs["enrich_top_skills"] is True
    assert mock_create.call_args.kwargs["run_eager_in_background"] is True


async def test_enrichment_publication_runs_eager_task_in_background(client, auth_headers):
    mock_response = _mock_task_status()
    with patch(
        "app.api.v1.graph.GraphService.prepare_enrichment_publication",
        new=AsyncMock(return_value=2),
    ), patch(
        "app.api.v1.graph.GraphTaskService.create_sync",
        new=AsyncMock(return_value=mock_response),
    ) as mock_create:
        response = await client.post(
            "/api/v1/graph/enrichment/publish",
            json={"candidate_ids": [1, 2]},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert mock_create.call_args.kwargs["enrich_top_skills"] is False
    assert mock_create.call_args.kwargs["run_eager_in_background"] is True


def _mock_candidate_response(review_status: str) -> dict:
    now = datetime.utcnow()
    return {
        "id": 1, "snapshot_id": "snap-1", "skill_id": 1, "skill_name": "Python",
        "candidate_data": {}, "evidence_source_ids": ["1", "2"],
        "confidence": 0.88, "machine_validation_status": "passed",
        "review_status": review_status,
        "publication_status": "approved" if review_status == "approved" else "draft",
        "review_note": "ok", "reviewed_at": now, "published_at": None,
        "lock_version": 1, "agent_run_id": None, "created_at": now, "updated_at": now,
    }


async def test_review_enrichment_approve_triggers_auto_publication(client, auth_headers):
    mock_task = _mock_task_status()
    with patch(
        "app.api.v1.graph.GraphService.review_enrichment_candidate",
        new=AsyncMock(return_value=_mock_candidate_response("approved")),
    ), patch(
        "app.api.v1.graph.GraphService.prepare_enrichment_publication",
        new=AsyncMock(return_value=1),
    ) as mock_prepare, patch(
        "app.api.v1.graph.GraphTaskService.create_sync_in_background",
        new=AsyncMock(return_value=mock_task),
    ) as mock_sync:
        response = await client.patch(
            "/api/v1/graph/enrichment/candidates/1/review",
            json={"action": "approve", "note": "ok", "lock_version": 0},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert "自动触发 L4/L5 图谱发布" in response.json()["message"]
    assert mock_prepare.await_args.args == ([1],)
    assert mock_sync.await_count == 1
    assert mock_sync.await_args.kwargs["mode"] == "incremental"
    assert mock_sync.await_args.kwargs["enrich_top_skills"] is False


async def test_review_enrichment_reject_does_not_trigger_sync(client, auth_headers):
    with patch(
        "app.api.v1.graph.GraphService.review_enrichment_candidate",
        new=AsyncMock(return_value=_mock_candidate_response("rejected")),
    ), patch(
        "app.api.v1.graph.GraphTaskService.create_sync_in_background",
        new=AsyncMock(),
    ) as mock_sync, patch(
        "app.api.v1.graph.GraphService.prepare_enrichment_publication",
        new=AsyncMock(),
    ) as mock_prepare:
        response = await client.patch(
            "/api/v1/graph/enrichment/candidates/1/review",
            json={"action": "reject", "note": "证据不足", "lock_version": 0},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["message"] == "候选已驳回"
    assert mock_sync.await_count == 0
    assert mock_prepare.await_count == 0


async def test_reject_machine_failed_candidates_uses_server_reasons(client, auth_headers):
    with patch(
        "app.api.v1.graph.GraphService.reject_machine_failed_candidates",
        new=AsyncMock(return_value=[3, 5, 8]),
    ) as mock_reject:
        response = await client.post(
            "/api/v1/graph/enrichment/candidates/reject-machine-failed",
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "rejected_count": 3,
        "candidate_ids": [3, 5, 8],
    }
    assert mock_reject.await_count == 1
