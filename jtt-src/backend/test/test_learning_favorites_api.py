<<<<<<< HEAD
"""学习路径和收藏接口集成测试。"""

from httpx import AsyncClient


async def test_learning_path_crud(client: AsyncClient, auth_headers: dict):
    payload = {
        "name": "Python 进阶路线",
        "position_id": "raw-1",
        "position_name": "后端工程师",
        "steps": [{
            "id": "step-1", "order": 1, "title": "异步编程",
            "duration": "1周", "resources": [], "completed": False,
        }],
    }
    created = await client.post("/api/v1/learning/paths", json=payload, headers=auth_headers)
    assert created.status_code == 200
    path_id = created.json()["data"]["id"]
    assert (await client.get("/api/v1/learning/paths", headers=auth_headers)).status_code == 200
    assert (await client.get(f"/api/v1/learning/paths/{path_id}")).status_code == 200

    updated = await client.put(f"/api/v1/learning/paths/{path_id}", json={"name": "新路线"})
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "新路线"
    assert (await client.delete(f"/api/v1/learning/paths/{path_id}")).status_code == 200


async def test_learning_path_accepts_legacy_numeric_position_id(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/learning/paths",
        json={"name": "兼容旧客户端", "position_id": 1, "position_name": "后端工程师", "steps": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["position_id"] == "1"


async def test_learning_assistant_endpoints(client: AsyncClient, auth_headers: dict, monkeypatch):
    from app.services.learning_service import LearningService

    async def chat(self, message, context, history):
        return {"reply": "建议先学习基础", "follow_up_questions": []}

    async def resources(self, names):
        return {"skills": {name: [] for name in names}}

    async def quiz(self, path_id, step_ids, count):
        return {"questions": [{"id": "q1", "question": "Python 是什么？"}]}

    async def generate_path(self, position_name, missing_skills, matched_skills, resume_id):
        return {
            "name": f"{position_name}学习路径", "position_id": "",
            "position_name": position_name, "steps": [], "total_duration": "0周",
        }

    monkeypatch.setattr(LearningService, "chat", chat)
    monkeypatch.setattr(LearningService, "recommend_resources", resources)
    monkeypatch.setattr(LearningService, "generate_quiz", quiz)
    monkeypatch.setattr(LearningService, "generate_path", generate_path)

    chat_res = await client.post("/api/v1/learning/assistant/chat", json={"message": "如何学习？"})
    assert chat_res.status_code == 200
    resource_res = await client.post(
        "/api/v1/learning/assistant/recommend-resources", json={"skill_names": ["Python"]}
    )
    assert resource_res.status_code == 200
    quiz_res = await client.post(
        "/api/v1/learning/assistant/quiz",
        json={"path_id": 1, "step_ids": [], "question_count": 1},
    )
    assert quiz_res.status_code == 200
    path_res = await client.post(
        "/api/v1/learning/assistant/generate-path",
        json={
            "position_name": "后端工程师", "missing_skills": ["Redis"],
            "matched_skills": ["Python"], "resume_id": None,
        },
        headers=auth_headers,
    )
    assert path_res.status_code == 200
    assert path_res.json()["data"]["position_name"] == "后端工程师"


async def test_favorite_add_check_list_delete(client: AsyncClient, auth_headers: dict):
    payload = {
        "item_type": "position", "item_id": "raw-1", "title": "后端工程师",
        "summary": "岗位摘要", "metadata": {"city": "合肥"}, "tags": ["重点"],
=======
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
>>>>>>> b568d5178201726754523d39b83e833d55cbaa23
    }
    created = await client.post("/api/v1/favorites", json=payload, headers=auth_headers)
    assert created.status_code == 200
    favorite_id = created.json()["data"]["id"]

    duplicate = await client.post("/api/v1/favorites", json=payload, headers=auth_headers)
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["id"] == favorite_id

<<<<<<< HEAD
    checked = await client.get(
        "/api/v1/favorites/check", params={"item_type": "position", "item_id": "raw-1"},
        headers=auth_headers,
    )
    assert checked.json()["data"] is True
    listed = await client.get("/api/v1/favorites", params={"type": "position"}, headers=auth_headers)
    assert len(listed.json()["data"]) == 1
    assert (await client.delete(f"/api/v1/favorites/{favorite_id}", headers=auth_headers)).status_code == 200
    missing = await client.delete("/api/v1/favorites/999", headers=auth_headers)
    assert missing.json()["code"] == 404
=======
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

>>>>>>> b568d5178201726754523d39b83e833d55cbaa23
