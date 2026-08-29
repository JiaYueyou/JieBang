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

