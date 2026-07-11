from test.api.test_jobs import create_job


async def test_career_analysis_requires_authentication(client):
    response = await client.post("/api/v1/career/analyses", json={"skill_text": "Python"})
    assert response.status_code == 401


async def test_resume_text_extraction_and_degraded_career_plan(client, auth_headers):
    extracted = await client.post(
        "/api/v1/career/resume-extractions",
        headers=auth_headers,
        files={"file": ("resume.md", "三年 Python 与 FastAPI 项目经验".encode("utf-8"), "text/markdown")},
    )
    assert extracted.status_code == 200
    resume_text = extracted.json()["data"]["text"]
    job = (await create_job(
        client,
        auth_headers,
        title="Python 平台工程师",
        skills=["Python", "FastAPI", "Redis"],
        bonus_skills=[],
    )).json()["data"]

    response = await client.post(
        "/api/v1/career/analyses",
        headers=auth_headers,
        json={
            "skill_text": "Python, FastAPI",
            "resume_text": resume_text,
            "enterprise_tech": "Redis",
            "internal_jobs": ["Python 平台工程师"],
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    row = data["recommendations"][0]
    assert row["job_id"] == job["id"]
    assert row["current_match"] == 67
    assert row["internal"] is True
    assert row["learning_plan"][0]["skill"] == "Redis"
    run = await client.get(f"/api/v1/agents/runs/{data['agent_run_id']}", headers=auth_headers)
    assert run.json()["data"]["status"] == "degraded"


async def test_career_analysis_rejects_empty_input(client, auth_headers):
    response = await client.post("/api/v1/career/analyses", headers=auth_headers, json={})
    assert response.status_code == 422
