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


async def test_resume_upload_requires_authentication(client):
    response = await client.post("/api/v1/resumes", files={"file": ("resume.txt", b"Python", "text/plain")})
    assert response.status_code == 401
