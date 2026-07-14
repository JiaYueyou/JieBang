import asyncio


async def wait_for_task(client, headers, task_id):
    for _ in range(200):
        response = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
        task = response.json()["data"]
        if task["status"] in {"succeeded", "failed"}:
            return task
        await asyncio.sleep(0.05)
    raise AssertionError(f"task {task_id} did not finish")


async def test_jd_generation_requires_authentication(client):
    response = await client.post(
        "/api/v1/agents/jd-generations",
        json={"title": "Java 开发工程师"},
    )
    assert response.status_code == 401


async def test_jd_input_suggestion_requires_authentication(client):
    response = await client.post(
        "/api/v1/agents/jd-input-suggestions",
        json={"title": "Java 开发工程师", "mode": "requirements"},
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
    assert payload["task"]["status"] == "queued"
    task = await wait_for_task(client, auth_headers, payload["task"]["task_id"])
    assert task["status"] == "succeeded"
    assert task["result"]["generation_mode"] == "template"
    assert task["result"]["title"] == "Java 开发工程师"

    run = await client.get(
        f"/api/v1/agents/runs/{payload['agent_run_id']}", headers=auth_headers
    )
    assert run.status_code == 200
    assert run.json()["data"]["agent_type"] == "jd_generation"
    assert run.json()["data"]["status"] == "degraded"


async def test_jd_input_suggestion_returns_title_specific_editable_fallback(client, auth_headers):
    response = await client.post(
        "/api/v1/agents/jd-input-suggestions",
        headers=auth_headers,
        json={
            "mode": "requirements",
            "title": "Java 开发工程师",
            "level": "senior",
            "department": "后台开发组",
        },
    )

    assert response.status_code == 200
    created = response.json()["data"]
    task = await wait_for_task(client, auth_headers, created["task"]["task_id"])
    assert task["status"] == "succeeded"
    assert task["result"]["suggestions"] == [
        "Java", "Spring Boot", "MySQL", "Redis", "微服务架构"
    ]
    assert task["result"]["generation_mode"] == "template"
    run = await client.get(
        f"/api/v1/agents/runs/{created['agent_run_id']}", headers=auth_headers
    )
    assert run.json()["data"]["agent_type"] == "jd_input_suggestion"
    assert run.json()["data"]["status"] == "degraded"


async def test_agent_run_is_only_visible_to_its_creator(client, auth_headers):
    created = await client.post(
        "/api/v1/agents/jd-generations",
        headers=auth_headers,
        json={"title": "Java 开发工程师"},
    )
    run_id = created.json()["data"]["agent_run_id"]
    await wait_for_task(
        client, auth_headers, created.json()["data"]["task"]["task_id"]
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "normal", "password": "user123"},
    )
    other_headers = {
        "Authorization": f"Bearer {login.json()['data']['access_token']}"
    }

    response = await client.get(
        f"/api/v1/agents/runs/{run_id}", headers=other_headers
    )

    assert response.status_code == 404


async def test_career_planning_async_task_returns_degraded_result(client, auth_headers):
    from test.api.test_jobs import create_job

    await create_job(client, auth_headers, title="Python 工程师", skills=["Python", "Redis"])
    response = await client.post(
        "/api/v1/agents/career-plannings", headers=auth_headers,
        json={"skill_text": "Python"},
    )
    assert response.status_code == 200
    created = response.json()["data"]
    task = await wait_for_task(client, auth_headers, created["task"]["task_id"])
    assert task["status"] == "succeeded"
    assert task["result"]["agent_status"] == "degraded"
    assert task["result"]["warnings"]


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
    task = await wait_for_task(client, auth_headers, created["task"]["task_id"])
    result = task["result"]
    assert task["status"] == "succeeded"
    assert result["score"] == match["score"]
    assert result["generation_mode"] == "template"
