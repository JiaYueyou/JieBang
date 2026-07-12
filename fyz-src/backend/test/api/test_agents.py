async def test_jd_generation_requires_authentication(client):
    response = await client.post(
        "/api/v1/agents/jd-generations",
        json={"title": "Java 开发工程师"},
    )
    assert response.status_code == 401


async def test_jd_generation_task_returns_editable_template_and_agent_audit(client, auth_headers):
    response = await client.post(
        "/api/v1/agents/jd-generations",
        headers=auth_headers,
        json={
            "mode": "requirements",
            "title": "Java 开发工程师",
            "level": "mid",
            "department": "研发中心",
            "skills_input": "Java, Spring Boot",
        },
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["task"]["status"] == "succeeded"
    assert payload["task"]["result"]["generation_mode"] == "template"
    assert payload["task"]["result"]["title"] == "Java 开发工程师"

    run = await client.get(
        f"/api/v1/agents/runs/{payload['agent_run_id']}", headers=auth_headers
    )
    assert run.status_code == 200
    assert run.json()["data"]["agent_type"] == "jd_generation"
    assert run.json()["data"]["status"] == "degraded"


async def test_career_planning_async_task_returns_degraded_result(client, auth_headers):
    from test.api.test_jobs import create_job

    await create_job(client, auth_headers, title="Python 工程师", skills=["Python", "Redis"])
    response = await client.post(
        "/api/v1/agents/career-plannings", headers=auth_headers,
        json={"skill_text": "Python"},
    )
    assert response.status_code == 200
    created = response.json()["data"]
    assert created["task"]["status"] == "succeeded"
    assert created["task"]["result"]["agent_status"] == "degraded"
    assert created["task"]["result"]["warnings"]


async def test_match_explanation_async_task_uses_saved_snapshot(client, auth_headers):
    from test.api.test_jobs import create_job

    await create_job(client, auth_headers, title="Python 工程师", skills=["Python", "Redis"])
    uploaded = await client.post(
        "/api/v1/resumes", headers=auth_headers,
        files={"file": ("resume.txt", "Python 项目经验".encode(), "text/plain")},
    )
    match = uploaded.json()["data"]["matches"][0]
    response = await client.post(
        "/api/v1/agents/match-explanations", headers=auth_headers,
        json={"match_id": match["id"]},
    )
    assert response.status_code == 200
    created = response.json()["data"]
    result = created["task"]["result"]
    assert created["task"]["status"] == "succeeded"
    assert result["score"] == match["score"]
    assert result["generation_mode"] == "template"
