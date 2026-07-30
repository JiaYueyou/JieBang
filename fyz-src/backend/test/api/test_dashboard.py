async def test_dashboard_overview_uses_persisted_jobs_and_matches(
    client,
    auth_headers,
):
    job_response = await client.post(
        "/api/v1/jobs",
        headers=auth_headers,
        json={
            "title": "真实数据平台工程师",
            "level": "mid",
            "department": "数据平台组",
            "location": "合肥",
            "responsibilities": ["建设数据服务"],
            "requirements": ["熟悉 Python"],
            "skills": ["Python", "SQL"],
            "bonus_skills": [],
            "jd_text": "Python SQL 数据服务",
            "status": "open",
        },
    )
    assert job_response.status_code == 200
    job_id = job_response.json()["data"]["id"]

    from app.core.database import async_session
    from app.models import MatchRecord, Resume

    async with async_session() as db:
        resume = Resume(
            name="真实候选人",
            current_position="数据工程师",
            original_filename="real-dashboard.txt",
            storage_key="dashboard-test/real-dashboard.txt",
            content_type="text/plain",
            file_size=32,
            content_hash="d" * 64,
            created_by=1,
        )
        db.add(resume)
        await db.flush()
        db.add(
            MatchRecord(
                resume_id=resume.id,
                job_id=job_id,
                algorithm_version="dashboard-test-v1",
                score=50,
                matched_skills=["Python"],
                missing_skills=["SQL"],
                created_by=1,
            )
        )
        await db.commit()

    response = await client.get("/api/v1/dashboard/overview", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["heroCards"][0]["value"] == "1"
    assert data["heroCards"][1]["value"] == "1"
    assert data["kanban"][0]["job_id"] == job_id
    assert data["kanban"][0]["title"] == "真实数据平台工程师"
    assert data["kanban"][0]["total"] == 1
    assert data["kanban"][0]["evaluated"] == 1
    assert data["kanban"][0]["pending"] == 0
    assert data["kanban"][0]["coverage"] == 100
    assert data["kanban"][0]["headcount"] == 1
    assert data["kanban"][0]["skills"] == ["Python", "SQL"]
    assert sum(stage["count"] for stage in data["kanban"][0]["stages"]) == 1
    assert data["highMatches"][0]["name"] == "真实候选人"
    assert data["hotJobs"][0]["job_id"] == job_id
    assert data["hotJobs"][0]["demand"] == 1


async def test_dashboard_marks_unmatched_talent_as_pending_and_excludes_stale_job_matches(
    client,
    auth_headers,
):
    current_job_response = await client.post(
        "/api/v1/jobs",
        headers=auth_headers,
        json={
            "title": "当前在招岗位",
            "level": "mid",
            "department": "研发中心",
            "location": "合肥",
            "headcount": 2,
            "responsibilities": ["建设平台"],
            "requirements": ["熟悉 Python"],
            "skills": ["Python"],
            "bonus_skills": [],
            "jd_text": "Python 平台建设",
            "status": "open",
        },
    )
    current_job_id = current_job_response.json()["data"]["id"]

    from datetime import datetime

    from app.core.database import async_session
    from app.models import JobPosting, MatchRecord, Resume

    async with async_session() as db:
        stale_job = JobPosting(
            title="已删除岗位",
            level="mid",
            department="历史部门",
            responsibilities=[],
            requirements=[],
            jd_text="历史岗位",
            status="open",
            created_by=1,
            deleted_at=datetime.utcnow(),
        )
        resume = Resume(
            name="待重新评估候选人",
            current_position="平台工程师",
            original_filename="pending-dashboard.txt",
            storage_key="dashboard-test/pending-dashboard.txt",
            content_type="text/plain",
            file_size=32,
            content_hash="e" * 64,
            created_by=1,
        )
        db.add_all([stale_job, resume])
        await db.flush()
        db.add(
            MatchRecord(
                resume_id=resume.id,
                job_id=stale_job.id,
                algorithm_version="stale-dashboard-v1",
                score=95,
                matched_skills=["Python"],
                missing_skills=[],
                created_by=1,
            )
        )
        await db.commit()

    response = await client.get("/api/v1/dashboard/overview", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]

    current_job = next(
        item for item in data["kanban"] if item["job_id"] == current_job_id
    )
    assert current_job["total"] == 1
    assert current_job["evaluated"] == 0
    assert current_job["pending"] == 1
    assert current_job["coverage"] == 0
    assert next(
        stage["count"]
        for stage in current_job["stages"]
        if stage["kind"] == "pending"
    ) == 1
    assert data["heroCards"][2]["value"] == "0"
    assert data["highMatches"] == []


async def test_dashboard_requires_authentication(client):
    response = await client.get("/api/v1/dashboard/overview")
    assert response.status_code == 401
