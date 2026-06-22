"""岗位管理 API 集成测试。"""

import pytest


def job_payload(**overrides):
    payload = {
        "title": "高级 Java 开发工程师",
        "standardized_title": "Java 开发工程师",
        "level": "senior",
        "department": "后台开发组",
        "company": "智联职引",
        "location": "合肥",
        "salary_min": 25000,
        "salary_max": 40000,
        "salary_months": 14,
        "headcount": 2,
        "responsibilities": ["负责核心服务架构", "主导关键模块开发"],
        "requirements": ["5 年以上 Java 经验"],
        "skills": ["Java", "Spring Boot", "MySQL"],
        "bonus_skills": ["Kubernetes"],
        "jd_text": "完整 JD",
        "status": "open",
    }
    payload.update(overrides)
    return payload


async def create_job(client, auth_headers, **overrides):
    return await client.post(
        "/api/v1/jobs",
        headers=auth_headers,
        json=job_payload(**overrides),
    )


class TestJobApi:
    async def test_requires_authentication(self, client):
        response = await client.get("/api/v1/jobs")
        assert response.status_code == 401
        assert response.json()["code"] == 40100

    async def test_create_list_and_get_job(self, client, auth_headers):
        created = await create_job(client, auth_headers)
        assert created.status_code == 200
        job = created.json()["data"]
        assert job["id"] > 0
        assert job["salary_range"] == "25K-40K · 14薪"
        assert job["skills"] == ["Java", "Spring Boot", "MySQL"]
        assert job["bonus_skills"] == ["Kubernetes"]

        listed = await client.get(
            "/api/v1/jobs?page=1&page_size=10&status=open&keyword=Java",
            headers=auth_headers,
        )
        assert listed.status_code == 200
        assert listed.json()["data"][0]["id"] == job["id"]
        assert listed.json()["meta"] == {
            "page": 1,
            "page_size": 10,
            "total": 1,
            "total_pages": 1,
        }

        detail = await client.get(
            f"/api/v1/jobs/{job['id']}",
            headers=auth_headers,
        )
        assert detail.json()["data"] == job

    async def test_frontend_salary_range_is_normalized(self, client, auth_headers):
        response = await create_job(
            client,
            auth_headers,
            salary_min=None,
            salary_max=None,
            salary_months=12,
            salary_range="18K-28K·13薪",
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["salary_min"] == 18000
        assert data["salary_max"] == 28000
        assert data["salary_months"] == 13

    async def test_update_status_and_versions(self, client, auth_headers):
        job = (await create_job(client, auth_headers, status="draft")).json()["data"]
        updated = await client.put(
            f"/api/v1/jobs/{job['id']}",
            headers=auth_headers,
            json={"title": "Java 平台工程师", "skills": ["Java", "Redis"]},
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["title"] == "Java 平台工程师"
        assert updated.json()["data"]["skills"] == ["Java", "Redis"]

        status = await client.put(
            f"/api/v1/jobs/{job['id']}/status",
            headers=auth_headers,
            json={"status": "open"},
        )
        assert status.json()["data"]["status"] == "open"

        versions = await client.get(
            f"/api/v1/jobs/{job['id']}/versions",
            headers=auth_headers,
        )
        rows = versions.json()["data"]
        assert [row["version_no"] for row in rows] == [3, 2, 1]
        assert rows[0]["snapshot"]["status"] == "open"

    async def test_partial_update_rejects_invalid_salary(self, client, auth_headers):
        job = (await create_job(client, auth_headers)).json()["data"]
        response = await client.put(
            f"/api/v1/jobs/{job['id']}",
            headers=auth_headers,
            json={"salary_min": 50000},
        )
        assert response.status_code == 422
        assert response.json()["code"] == 40003

    async def test_soft_delete_hides_job(self, client, auth_headers):
        job = (await create_job(client, auth_headers)).json()["data"]
        deleted = await client.delete(
            f"/api/v1/jobs/{job['id']}",
            headers=auth_headers,
        )
        assert deleted.status_code == 200

        detail = await client.get(
            f"/api/v1/jobs/{job['id']}",
            headers=auth_headers,
        )
        assert detail.status_code == 404
        assert detail.json()["code"] == 40400

        listed = await client.get("/api/v1/jobs", headers=auth_headers)
        assert listed.json()["data"] == []

    @pytest.mark.parametrize(
        "payload",
        [
            {"title": "", "department": "研发"},
            {"title": "Java", "department": "研发", "salary_min": 40000, "salary_max": 20000},
            {"title": "Java", "department": "研发", "status": "invalid"},
        ],
    )
    async def test_validation_errors(self, client, auth_headers, payload):
        response = await client.post(
            "/api/v1/jobs",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 422
        assert response.json()["code"] == 40003

    async def test_missing_job_uses_unified_error(self, client, auth_headers):
        response = await client.get("/api/v1/jobs/9999", headers=auth_headers)
        assert response.status_code == 404
        assert response.json() == {
            "code": 40400,
            "message": "岗位不存在",
            "data": None,
            "meta": None,
        }
