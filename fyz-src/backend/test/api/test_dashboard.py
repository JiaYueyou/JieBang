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
    from app.models import MatchRecord, RawJobRecord, Resume, Skill, SourceDocument, StandardJob, StandardJobSource, JobSkillFact

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
        # 爬取数据：热门岗位数据源（2 条同标准岗位记录 + 1 条技能事实）
        standard = StandardJob(
            name="数据仓库工程师", canonical_key="data-warehouse-dashboard-test",
            aliases=[], stack="data", level="middle", description="",
            source_count=2, status="active",
        )
        skill = Skill(
            name="SQL", canonical_name="SQL", canonical_key="sql-dashboard-test",
            category="database", aliases=[],
        )
        db.add_all([standard, skill])
        await db.flush()
        for index, source_name in enumerate(("来源A", "来源B"), start=1):
            document = SourceDocument(
                source=source_name, url=f"https://dash.test/{index}",
                title="数据仓库工程师", content_fingerprint=f"dash-{index:064d}",
                content_summary="SQL", source_meta={"posted_at": "2026-07-15"},
            )
            db.add(document)
            await db.flush()
            raw = RawJobRecord(
                source_document_id=document.id, title="数据仓库工程师",
                standardized_title="数据仓库工程师", company="数据企业",
                city="北京", jd_text="SQL 数据仓库建模", responsibilities="",
                requirements="SQL", keywords="SQL", posted_at_text="2026-07-15",
                dedup_status="unique", quality_status="accepted",
                standard_job_id=standard.id, normalized_data={},
            )
            db.add(raw)
            await db.flush()
            db.add(StandardJobSource(
                standard_job_id=standard.id, source_type="raw",
                source_id=raw.id, original_title=raw.title, confidence=0.95,
            ))
            db.add(JobSkillFact(
                raw_job_record_id=raw.id, skill_id=skill.id, kind="required",
                importance=0.9, frequency=1, confidence=0.96,
                evidence_text="SQL", verification_status="verified",
                extraction_method="rule", source_count=2,
            ))
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
    # 热门岗位来自爬取数据（RawJobRecord → 标准岗位聚合）
    assert data["hotJobs"][0]["title"] == "数据仓库工程师"
    assert data["hotJobs"][0]["standard_job_id"] == standard.id
    assert "job_id" not in data["hotJobs"][0]
    assert data["hotJobs"][0]["demand"] == 2
    assert data["hotJobs"][0]["city"] == "北京"
    assert "SQL" in data["hotJobs"][0]["core_skills"]
    assert data["hotJobsTotal"] >= 1


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


async def test_dashboard_hot_jobs_and_emerging_skills_pagination(client, auth_headers):
    """热门岗位与技能涌现两区块支持分页参数，返回 total 与切片。"""
    from app.core.database import async_session
    from app.models import RawJobRecord, Skill, SourceDocument, StandardJob, StandardJobSource

    async with async_session() as db:
        for i, (title, canonical) in enumerate(
            (("分页岗位甲", "page-job-a"), ("分页岗位乙", "page-job-b"))
        ):
            standard = StandardJob(
                name=title, canonical_key=canonical, aliases=[],
                stack="backend", level="middle", description="",
                source_count=1, status="active",
            )
            skill = Skill(
                name=f"技能{i}", canonical_name=f"技能{i}",
                canonical_key=f"page-skill-{i}", category="backend", aliases=[],
            )
            db.add_all([standard, skill])
            await db.flush()
            document = SourceDocument(
                source="分页来源", url=f"https://page.test/{i}",
                title=title, content_fingerprint=f"page-{i:064d}",
                content_summary="", source_meta={"posted_at": "2026-07-15"},
            )
            db.add(document)
            await db.flush()
            raw = RawJobRecord(
                source_document_id=document.id, title=title,
                standardized_title=title, company="分页企业", city="上海",
                jd_text=f"{title} 技能", responsibilities="", requirements="",
                keywords="", posted_at_text="2026-07-15", dedup_status="unique",
                quality_status="accepted", standard_job_id=standard.id,
                normalized_data={},
            )
            db.add(raw)
            await db.flush()
            db.add(StandardJobSource(
                standard_job_id=standard.id, source_type="raw",
                source_id=raw.id, original_title=title, confidence=0.95,
            ))
        await db.commit()

    response = await client.get(
        "/api/v1/dashboard/overview",
        headers=auth_headers,
        params={"hot_jobs_page": 1, "hot_jobs_page_size": 1,
                "emerging_page": 1, "emerging_page_size": 1},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["hotJobs"]) == 1
    assert data["hotJobsTotal"] >= 2
    assert len(data["emergingSkills"]) <= 1
    assert data["emergingSkillsTotal"] >= 0
