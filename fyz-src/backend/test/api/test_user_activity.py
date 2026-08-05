"""收藏与浏览足迹真实数据链路测试。"""


def _job_payload():
    return {
        "title": "Python 后端工程师",
        "level": "mid",
        "department": "研发部",
        "company": "示例科技",
        "location": "合肥",
        "experience": "3-5年",
        "education": "本科",
        "salary_min": 18000,
        "salary_max": 28000,
        "responsibilities": ["开发 API"],
        "requirements": ["熟悉 Python"],
        "skills": ["Python", "FastAPI"],
        "bonus_skills": ["Docker"],
        "jd_text": "负责 Python API 开发",
        "status": "open",
    }


async def test_favorite_toggle_list_note_and_batch_delete(client, auth_headers):
    job = (
        await client.post("/api/v1/jobs", headers=auth_headers, json=_job_payload())
    ).json()["data"]

    toggled = await client.post(
        "/api/v1/favorites",
        headers=auth_headers,
        json={"target_type": "job", "target_id": job["id"]},
    )
    assert toggled.status_code == 200
    assert toggled.json()["data"]["active"] is True

    favorites = (
        await client.get("/api/v1/favorites", headers=auth_headers)
    ).json()["data"]
    assert len(favorites) == 1
    favorite = favorites[0]
    assert favorite["title"] == "Python 后端工程师"
    assert favorite["company"] == "示例科技"
    assert set(favorite["skills"]) == {"Python", "FastAPI", "Docker"}
    assert favorite["salary"] == "18K-28K · 12薪"

    updated = await client.put(
        f"/api/v1/favorites/{favorite['id']}/note",
        headers=auth_headers,
        json={"note": "下周安排候选人筛选"},
    )
    assert updated.status_code == 200
    favorites = (
        await client.get("/api/v1/favorites", headers=auth_headers)
    ).json()["data"]
    assert favorites[0]["note"] == "下周安排候选人筛选"

    deleted = await client.post(
        "/api/v1/favorites/batch-delete",
        headers=auth_headers,
        json={"ids": [favorite["id"]]},
    )
    assert deleted.json()["data"]["deleted"] == 1
    assert (
        await client.get("/api/v1/favorites", headers=auth_headers)
    ).json()["data"] == []


async def test_favorite_is_user_isolated_and_rejects_missing_target(client, auth_headers):
    missing = await client.post(
        "/api/v1/favorites",
        headers=auth_headers,
        json={"target_type": "job", "target_id": 9999},
    )
    assert missing.status_code == 404

    job = (
        await client.post("/api/v1/jobs", headers=auth_headers, json=_job_payload())
    ).json()["data"]
    await client.post(
        "/api/v1/favorites",
        headers=auth_headers,
        json={"target_type": "job", "target_id": job["id"]},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "normal", "password": "user123"},
    )
    other_headers = {
        "Authorization": f"Bearer {login.json()['data']['access_token']}"
    }
    assert (
        await client.get("/api/v1/favorites", headers=other_headers)
    ).json()["data"] == []


async def test_history_records_aggregate_and_support_delete(client, auth_headers):
    payload = {
        "type": "search",
        "targetId": "Python",
        "title": "搜索：Python",
        "description": "岗位洞察搜索",
        "source": "岗位管理",
        "url": "/jobs?tab=insight&skill=Python",
        "tags": ["Python", "岗位洞察"],
    }
    first = await client.post("/api/v1/history", headers=auth_headers, json=payload)
    second = await client.post("/api/v1/history", headers=auth_headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]

    history = (
        await client.get("/api/v1/history", headers=auth_headers)
    ).json()["data"]
    assert len(history) == 1
    assert history[0]["badge"] == "浏览 2 次"
    assert history[0]["dateKey"] == "today"

    insights = (
        await client.get("/api/v1/history/insights", headers=auth_headers)
    ).json()["data"]
    assert insights["focusStats"] == [
        {"label": "搜索", "percent": 100, "count": 2}
    ]
    assert insights["frequentRecords"] == [
        {"history_id": history[0]["id"], "count": 2}
    ]

    removed = await client.delete(
        f"/api/v1/history/{history[0]['id']}",
        headers=auth_headers,
    )
    assert removed.status_code == 204
    assert (
        await client.get("/api/v1/history", headers=auth_headers)
    ).json()["data"] == []


async def test_history_clear_and_authentication(client, auth_headers):
    await client.post(
        "/api/v1/history",
        headers=auth_headers,
        json={
            "type": "graph",
            "targetId": "python",
            "title": "Python 技能图谱",
            "url": "/graph?node=python",
        },
    )
    assert (await client.delete("/api/v1/history", headers=auth_headers)).status_code == 204
    assert (
        await client.get("/api/v1/history", headers=auth_headers)
    ).json()["data"] == []
    assert (await client.get("/api/v1/favorites")).status_code == 401
    assert (await client.get("/api/v1/history")).status_code == 401
