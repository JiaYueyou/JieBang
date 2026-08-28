<<<<<<< HEAD
"""简历接口集成测试。"""

from httpx import AsyncClient


def resume_payload(name: str = "后端开发简历") -> dict:
    return {
        "name": name,
        "target_position": "Python 后端工程师",
        "personal_info": {"name": "测试用户", "email": "test@example.com"},
        "skills": [{"name": "Python", "level": "advanced"}],
        "self_evaluation": "熟悉异步 Web 开发",
    }


async def test_resume_crud_and_duplicate(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/resume", json=resume_payload(), headers=auth_headers)
    assert created.status_code == 200
    resume_id = created.json()["data"]["id"]

    listed = await client.get("/api/v1/resume/resumes", headers=auth_headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["data"]] == [resume_id]

    detail = await client.get(f"/api/v1/resume/{resume_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["target_position"] == "Python 后端工程师"

    updated = await client.put(f"/api/v1/resume/{resume_id}", json={"name": "更新后的简历"})
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "更新后的简历"

    duplicated = await client.post(f"/api/v1/resume/{resume_id}/duplicate")
    assert duplicated.status_code == 200
    assert duplicated.json()["data"]["id"] != resume_id

    deleted = await client.delete(f"/api/v1/resume/{resume_id}")
    assert deleted.status_code == 200


async def test_resume_requires_auth_and_validates_payload(client: AsyncClient, auth_headers: dict):
    assert (await client.get("/api/v1/resume/resumes")).status_code == 401
    assert (await client.post("/api/v1/resume", json={"name": ""}, headers=auth_headers)).status_code == 422


async def test_resume_upload(client: AsyncClient, auth_headers: dict, monkeypatch):
    from app.services.resume_service import ResumeService

    async def fake_parse(self, user_id, content, filename):
        return {
            "resume": {"id": 9, "name": filename},
            "extracted_skills": ["Python"],
            "parse_accuracy": 0.9,
        }

    monkeypatch.setattr(ResumeService, "parse_upload", fake_parse)
    response = await client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.pdf", b"pdf-content", "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["extracted_skills"] == ["Python"]
=======
import pytest


@pytest.mark.asyncio
async def test_resume_crud_and_duplicate(client, auth_headers):
    payload = {
        "name": "Backend Resume",
        "target_position": "Python Engineer",
        "personal_info": {
            "name": "Test Candidate", "email": "candidate@example.com",
            "phone": "13800138000", "location": "Beijing",
        },
        "job_intent": {
            "desired_position": "Backend Engineer", "desired_city": "Beijing",
            "salary_expectation": "20K", "work_mode": "fulltime",
        },
        "education": [{"school": "Test University", "degree": "Bachelor", "major": "CS"}],
        "work_experience": [{"company": "Test Co", "position": "Engineer", "skills": ["Python"]}],
        "projects": [{"name": "JTT", "role": "Developer", "technologies": ["FastAPI"]}],
        "skills": [{"name": "Python", "category": "language"}],
        "self_evaluation": "Reliable",
    }
    created = await client.post("/api/v1/resume", json=payload, headers=auth_headers)
    assert created.status_code == 200
    resume = created.json()["data"]
    assert resume["personal_info"]["email"] == "candidate@example.com"
    resume_id = resume["id"]

    listed = await client.get("/api/v1/resume/resumes", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["id"] == resume_id for item in listed.json()["data"])

    detail = await client.get(f"/api/v1/resume/{resume_id}", headers=auth_headers)
    assert detail.json()["data"]["skills"][0]["name"] == "Python"

    updated = await client.put(
        f"/api/v1/resume/{resume_id}",
        json={"name": "Updated Resume", "self_evaluation": "Updated"},
        headers=auth_headers,
    )
    assert updated.json()["data"]["name"] == "Updated Resume"

    duplicated = await client.post(f"/api/v1/resume/{resume_id}/duplicate", headers=auth_headers)
    assert duplicated.status_code == 200
    duplicate_id = duplicated.json()["data"]["id"]
    assert duplicate_id != resume_id

    deleted = await client.delete(f"/api/v1/resume/{resume_id}", headers=auth_headers)
    assert deleted.status_code == 200
    missing = await client.get(f"/api/v1/resume/{resume_id}", headers=auth_headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_resume_endpoints_require_authentication(client):
    response = await client.get("/api/v1/resume/resumes")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_resume_create_validation(client, auth_headers):
    response = await client.post("/api/v1/resume", json={"name": ""}, headers=auth_headers)
    assert response.status_code == 422

>>>>>>> b568d5178201726754523d39b83e833d55cbaa23
