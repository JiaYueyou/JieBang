async def test_analysis_requires_authentication(client):
    overview = await client.get("/api/v1/analysis/overview")
    insights = await client.get("/api/v1/analysis/job-insights")
    assert overview.status_code == 401
    assert insights.status_code == 401


async def test_empty_analysis_response_is_explicit_about_data_quality(
    client, auth_headers
):
    response = await client.get(
        "/api/v1/analysis/overview?months=6&keyword=Java&city=杭州",
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
