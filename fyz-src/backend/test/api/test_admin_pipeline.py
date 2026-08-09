"""Admin API contract for durable automatic refresh runs."""

import pytest


@pytest.mark.asyncio
async def test_admin_can_create_and_query_pipeline_run(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.api.v1.admin.start_pipeline_run", lambda _run_id: None)

    response = await client.post(
        "/api/v1/admin/pipeline/runs",
        headers=auth_headers,
        json={"source_ids": [4, 5]},
    )
    assert response.status_code == 200
    run = response.json()["data"]
    assert run["status"] == "queued"
    assert run["requested_sources"] == [4, 5]

    detail = await client.get(
        f"/api/v1/admin/pipeline/runs/{run['id']}", headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == run["id"]

    listing = await client.get("/api/v1/admin/pipeline/runs", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["data"][0]["id"] == run["id"]


@pytest.mark.asyncio
async def test_pipeline_runs_require_admin(client):
    response = await client.post(
        "/api/v1/admin/pipeline/runs", json={"source_ids": [4]},
    )
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_admin_can_configure_automatic_crawling(client, auth_headers):
    response = await client.put(
        "/api/v1/admin/data-sources/automation",
        headers=auth_headers,
        json={
            "enabled": True,
            "source_ids": [2, 4],
            "schedule_type": "weekly",
            "interval_minutes": 60,
            "run_time": "01:45",
            "weekdays": [0, 4],
            "max_records": 120,
            "max_pages": 6,
            "retry_count": 2,
            "retry_delay_minutes": 10,
            "timeout_seconds": 300,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source_ids"] == [2, 4]
    assert data["schedule_type"] == "weekly"
    assert data["max_records"] == 120

    detail = await client.get(
        "/api/v1/admin/data-sources/automation", headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["run_time"] == "01:45"
