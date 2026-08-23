import pytest


@pytest.mark.asyncio
async def test_learning_path_crud(client, auth_headers):
    payload = {
        "name": "Python Path",
        "position_id": "python-backend",
        "position_name": "Python Engineer",
        "steps": [{
            "id": "step-1", "order": 1, "title": "Python Basics",
            "description": "Learn syntax", "duration": "2",
            "resources": [], "completed": False,
        }],
    }
    created = await client.post("/api/v1/learning/paths", json=payload, headers=auth_headers)
    assert created.status_code == 200, created.text
    path_id = created.json()["data"]["id"]

    listed = await client.get("/api/v1/learning/paths", headers=auth_headers)
    assert any(item["id"] == path_id for item in listed.json()["data"])

    detail = await client.get(f"/api/v1/learning/paths/{path_id}", headers=auth_headers)
    assert detail.json()["data"]["position_id"] == "python-backend"

    update = await client.put(
        f"/api/v1/learning/paths/{path_id}",
        json={"name": "Updated Path", "steps": []}, headers=auth_headers,
    )
    assert update.json()["data"]["name"] == "Updated Path"

    deleted = await client.delete(f"/api/v1/learning/paths/{path_id}", headers=auth_headers)
    assert deleted.status_code == 200
    missing = await client.get(f"/api/v1/learning/paths/{path_id}", headers=auth_headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_learning_path_rejects_missing_name(client, auth_headers):
    response = await client.post(
        "/api/v1/learning/paths", json={"position_id": "x"}, headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_favorite_add_duplicate_filter_check_and_remove(client, auth_headers):
    payload = {
        "item_type": "position", "item_id": "job-1", "title": "Python Engineer",
        "summary": "Backend role", "metadata": {"city": "Beijing"}, "tags": ["python"],
    }
    created = await client.post("/api/v1/favorites", json=payload, headers=auth_headers)
    assert created.status_code == 200
    favorite_id = created.json()["data"]["id"]

    duplicate = await client.post("/api/v1/favorites", json=payload, headers=auth_headers)
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["id"] == favorite_id

    listed = await client.get("/api/v1/favorites?type=position", headers=auth_headers)
    assert len(listed.json()["data"]) == 1
    assert listed.json()["data"][0]["metadata"]["city"] == "Beijing"

    checked = await client.get(
        "/api/v1/favorites/check?item_type=position&item_id=job-1", headers=auth_headers
    )
    assert checked.json()["data"] is True

    removed = await client.delete(f"/api/v1/favorites/{favorite_id}", headers=auth_headers)
    assert removed.status_code == 200
    checked_again = await client.get(
        "/api/v1/favorites/check?item_type=position&item_id=job-1", headers=auth_headers
    )
    assert checked_again.json()["data"] is False
    missing = await client.delete("/api/v1/favorites/99999", headers=auth_headers)
    assert missing.json()["code"] == 404

