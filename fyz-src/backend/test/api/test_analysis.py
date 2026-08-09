async def test_analysis_requires_authentication(client):
    overview = await client.get("/api/v1/analysis/overview")
    insights = await client.get("/api/v1/analysis/job-insights")
    assert overview.status_code == 401
    assert insights.status_code == 401


async def test_empty_analysis_response_is_explicit_about_data_quality(
    client, auth_headers
):
    response = await client.get(
        "/api/v1/analysis/overview?window=6m&keyword=Java&city=杭州",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["months"]) == 6
    assert data["stats"]["total_jobs"] == 0
    assert data["data_quality"]["insufficient_data"] is True
    assert data["job_demand"] == []
    assert data["emerging_skills"] == []


async def test_empty_job_insights_return_stable_contract(client, auth_headers):
    response = await client.get(
        "/api/v1/analysis/job-insights?skill=Rust&limit=10",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["emerging_jobs"] == []
    assert data["capability_changes"] == []
    assert data["data_quality"]["insufficient_data"] is True
    assert any("标准岗位" in note for note in data["data_quality"]["notes"])


async def test_decision_requires_an_existing_standard_job(client, auth_headers):
    response = await client.put(
        "/api/v1/analysis/emerging-jobs/999/decision",
        headers=auth_headers,
        json={"decision": "confirmed", "note": "人工确认"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == 40400


async def test_decision_rejects_invalid_value(client, auth_headers):
    response = await client.put(
        "/api/v1/analysis/emerging-jobs/1/decision",
        headers=auth_headers,
        json={"decision": "invalid"},
    )
    assert response.status_code == 422


async def test_overview_deduplicates_reposted_jobs_by_cluster_and_company(
    client, auth_headers
):
    from app.core.database import async_session
    from app.models import (
        JobSkillFact,
        RawJobRecord,
        Skill,
        SourceDocument,
        StandardJob,
        StandardJobSource,
    )

    async with async_session() as db:
        standard = StandardJob(
            name="数据工程师",
            canonical_key="data-engineer-analysis-test",
            aliases=[],
            stack="data",
            level="middle",
            description="",
            source_count=2,
            status="active",
        )
        skill = Skill(
            name="Python",
            canonical_name="Python",
            canonical_key="python-analysis-test",
            category="backend",
            aliases=[],
        )
        db.add_all([standard, skill])
        await db.flush()
        for index, source_name in enumerate(("zhaopin", "iflytek"), start=1):
            document = SourceDocument(
                source=source_name,
                external_id=f"duplicate-{index}",
                url=f"https://example.test/{index}",
                title="数据工程师",
                company="同一企业",
                content_fingerprint=f"analysis-duplicate-{index}",
                content_summary="Python 数据处理",
                source_meta={"posted_at": "2026-07-01"},
            )
            db.add(document)
            await db.flush()
            raw = RawJobRecord(
                source_document_id=document.id,
                title="数据工程师",
                standardized_title="数据工程师",
                company="同一企业",
                city="合肥",
                salary_text="20K-30K",
                jd_text="Python 数据处理",
                responsibilities="",
                requirements="Python",
                keywords="Python",
                posted_at_text="2026-07-01",
                dedup_status="unique",
                normalized_data={},
            )
            db.add(raw)
            await db.flush()
            db.add_all([
                StandardJobSource(
                    standard_job_id=standard.id,
                    source_type="raw",
                    source_id=raw.id,
                    original_title=raw.title,
                    confidence=1.0,
                ),
                JobSkillFact(
                    raw_job_record_id=raw.id,
                    skill_id=skill.id,
                    kind="required",
                    importance=0.9,
                    frequency=1,
                    confidence=0.95,
                    evidence_text="Python",
                    verification_status="verified",
                    extraction_method="rule",
                    source_count=2,
                ),
            ])
        await db.commit()

    response = await client.get(
        "/api/v1/analysis/overview?window=1m",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    quality = data["data_quality"]
    assert quality["total_records"] == 2
    assert quality["deduplicated_records"] == 1
    assert quality["duplicate_records"] == 1
    assert quality["independent_job_clusters"] == 1
    assert quality["independent_companies"] == 1
    assert data["stats"]["total_jobs"] == 1
    assert data["stats"]["new_skills"] == 0
    assert data["emerging_skills"] == []
    assert quality["insufficient_data"] is True
    assert any("样本" in note for note in quality["notes"])
    assert max(point["value"] for point in data["heatmap"]) == 1


async def test_analysis_rejects_unsupported_trend_window(client, auth_headers):
    response = await client.get(
        "/api/v1/analysis/overview?window=12m",
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_reference_standards_support_server_side_pagination(client, auth_headers):
    response = await client.get(
        "/api/v1/analysis/reference-standards",
        params={"page": 1, "page_size": 5, "keyword": "Python", "stack": "backend"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5
    assert data["total_pages"] == (
        (data["total"] + data["page_size"] - 1) // data["page_size"]
        if data["total"] else 0
    )


async def test_analysis_supports_required_trend_windows(client, auth_headers):
    expected = {
        "15d": (15, "day"),
        "1m": (30, "day"),
        "3m": (3, "month"),
        "6m": (6, "month"),
    }
    for window, (label_count, granularity) in expected.items():
        response = await client.get(
            f"/api/v1/analysis/overview?window={window}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["window"] == window
        assert data["granularity"] == granularity
        assert len(data["months"]) == label_count
