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
