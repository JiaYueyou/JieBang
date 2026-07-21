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
