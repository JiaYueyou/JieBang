async def _create_job(client, headers):
    response = await client.post("/api/v1/jobs", headers=headers, json={
        "title": "Python 后端工程师", "level": "mid", "department": "研发部",
        "responsibilities": ["开发 API"], "requirements": ["熟悉 Python 和 Redis"],
        "skills": ["Python", "Redis"], "bonus_skills": [], "jd_text": "Python Redis",
        "status": "open",
    })
    assert response.status_code == 200


async def test_resume_match_explanation_and_controlled_download(client, auth_headers):
    await _create_job(client, auth_headers)
    uploaded = await client.post(
        "/api/v1/resumes", headers=auth_headers,
        data={"name": "张三", "current_position": "Python 开发"},
        files={"file": ("zhangsan.txt", "拥有 Python 和 MySQL 项目经验".encode(), "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    created = uploaded.json()["data"]
    assert created["skills"] == ["MySQL", "Python"]
    assert created["matches"][0]["score"] == 50
    assert created["matches"][0]["matched"] == ["Python"]
    assert created["matches"][0]["missing"] == ["Redis"]

    talents = (await client.get("/api/v1/talents", headers=auth_headers)).json()["data"]
    assert talents[0]["name"] == "张三"
    assert talents[0]["match_id"] == created["matches"][0]["id"]

    details = await client.get(f"/api/v1/talents/{created['id']}/details", headers=auth_headers)
    assert details.status_code == 200, details.text
    assert details.json()["data"]["parsed_text"]
    assert details.json()["data"]["skills"][0]["evidence_text"]

    selected = await client.post(
        f"/api/v1/resumes/{created['id']}/matches",
        headers=auth_headers,
        json={"job_ids": [created["matches"][0]["job_id"]]},
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["data"][0]["matched"] == ["Python"]

    explanation = await client.post(f"/api/v1/matches/{talents[0]['match_id']}/explanation", headers=auth_headers)
    assert explanation.status_code == 200, explanation.text
    assert explanation.json()["data"]["score"] == 50
    assert explanation.json()["data"]["generation_mode"] == "template"

    downloaded = await client.get(f"/api/v1/resumes/{created['id']}/file", headers=auth_headers)
    assert downloaded.status_code == 200
    assert downloaded.content == "拥有 Python 和 MySQL 项目经验".encode()

    login = await client.post("/api/v1/auth/login", json={"username": "normal", "password": "user123"})
    other = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    denied = await client.get(f"/api/v1/resumes/{created['id']}/file", headers=other)
    assert denied.status_code == 404


async def test_recalculate_matches_covers_jobs_created_after_resume_upload(
    client,
    auth_headers,
):
    await _create_job(client, auth_headers)
    uploaded = await client.post(
        "/api/v1/resumes",
        headers=auth_headers,
        data={"name": "待刷新候选人", "current_position": "Python 开发"},
        files={
            "file": (
                "refresh.txt",
                "拥有 Python 和 MySQL 项目经验".encode(),
                "text/plain",
            )
        },
    )
    assert uploaded.status_code == 200
    assert len(uploaded.json()["data"]["matches"]) == 1

    second_job = await client.post(
        "/api/v1/jobs",
        headers=auth_headers,
        json={
            "title": "数据平台工程师",
            "level": "mid",
            "department": "数据平台组",
            "responsibilities": ["建设数据服务"],
            "requirements": ["熟悉 SQL"],
            "skills": ["SQL"],
            "bonus_skills": [],
            "jd_text": "SQL 数据服务",
            "status": "open",
        },
    )
    assert second_job.status_code == 200

    refreshed = await client.post(
        "/api/v1/matches/recalculate",
        headers=auth_headers,
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["data"] == {
        "resumes_processed": 1,
        "matches_upserted": 2,
    }

    talents = (
        await client.get("/api/v1/talents", headers=auth_headers)
    ).json()["data"]
    assert set(talents[0]["targetJobs"]) == {
        "Python 后端工程师",
        "数据平台工程师",
    }


async def test_resume_upload_requires_authentication(client):
    response = await client.post("/api/v1/resumes", files={"file": ("resume.txt", b"Python", "text/plain")})
    assert response.status_code == 401
