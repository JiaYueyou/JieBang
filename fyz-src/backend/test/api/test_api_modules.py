"""占位模块路由测试 — 验证所有模块基础可用"""

import pytest


MODULES = [
    ("/api/v1/changes/", "能力更新"),
    ("/api/v1/graph/", "技能图谱"),
    ("/api/v1/matching/", "匹配诊断"),
    ("/api/v1/analysis/", "趋势分析"),
]


class TestPlaceholderModules:
    @pytest.mark.parametrize("path,name", MODULES)
    async def test_module_returns_200(self, client, auth_headers, path, name):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert "message" in body["data"]
        assert len(body["data"]["message"]) > 0

    @pytest.mark.parametrize("path,name", MODULES)
    async def test_module_blocked_without_auth(self, client, path, name):
        resp = await client.get(path)
        assert resp.status_code == 401

    async def test_nonexistent_route(self, client):
        resp = await client.get("/api/v1/doesnotexist/")
        assert resp.status_code == 404
        assert resp.json() == {
            "code": 40400,
            "message": "请求的资源不存在",
            "data": None,
            "meta": None,
        }


class TestAdminModule:
    """系统管理 — 真实路由测试"""

    async def test_overview_returns_200(self, client, auth_headers):
        job_response = await client.post(
            "/api/v1/jobs",
            headers=auth_headers,
            json={
                "title": "监控数据测试工程师",
                "department": "数据平台",
                "level": "mid",
                "responsibilities": ["开发 Python 服务"],
                "requirements": ["熟悉 FastAPI 和 MySQL"],
                "jd_text": "使用 Python、FastAPI 和 MySQL 开发数据服务",
                "status": "open",
            },
        )
        job_id = job_response.json()["data"]["id"]
        facts_response = await client.post(
            f"/api/v1/jobs/{job_id}/extract-skills",
            headers=auth_headers,
        )
        facts = facts_response.json()["data"]["facts"]
        await client.patch(
            f"/api/v1/skills/facts/{facts[0]['id']}/review",
            headers=auth_headers,
            json={"decision": "verified", "note": "监控接口测试确认"},
        )

        resp = await client.get("/api/v1/admin/overview", headers=auth_headers)
        assert resp.status_code == 200

        resources = await client.get(
            "/api/v1/admin/resources", headers=auth_headers
        )
        assert resources.status_code == 200
        payload = resources.json()["data"]
        assert [item["label"] for item in payload["resources"]] == [
            "CPU", "内存", "磁盘"
        ]
        assert payload["sampledAt"]
        body = resp.json()
        assert body["code"] == 200
        assert "metrics" in body["data"]
        assert "crawlers" in body["data"]
        assert body["data"]["pipelineSummary"] == {
            "totalJobs": 0,
            "todayImported": 0,
            "sourceCount": 0,
            "validRecords": 0,
            "validRate": 0.0,
            "failedTasks": 0,
            "processedToday": 0,
            "duplicatesToday": 0,
            "verifiedFacts": 1,
            "unverifiedFacts": len(facts) - 1,
            "overallQuality": 0.0,
        }
        assert body["data"]["crawlers"][0]["endpoint"] == "iflytek.com"
        cards = {card["label"]: card for card in body["data"]["performanceCards"]}
        assert cards["技能事实总量"]["value"] == str(len(facts))
        assert cards["事实确认率"]["value"] != "0.0%"
        assert body["data"]["endpoints"][0] == {
            "key": "skill_facts",
            "title": "技能事实总量",
            "description": "系统已沉淀、可追溯的岗位技能事实",
            "value": f"{len(facts)} 条",
            "percent": 100,
        }
        assert body["data"]["generatedAt"]
        assert set(body["data"]["traffic"]) == {
            "inbound",
            "outbound",
            "receivedTotal",
            "sentTotal",
        }
        assert {item["label"] for item in body["data"]["resources"]} == {
            "CPU",
            "内存",
            "磁盘",
        }
        assert all(
            0 <= float(item["value"]) <= 100
            for item in body["data"]["resources"]
        )
        services = {item["name"]: item for item in body["data"]["services"]}
        assert set(services) == {"MySQL", "Neo4j", "Agent", "Crawler"}
        assert services["MySQL"]["status"] == "healthy"
        assert services["Neo4j"]["statusLabel"] == "测试环境未连接"
        assert "Redis" not in services
        assert "crawlerPolicy" not in body["data"]
        assert any(
            log["service"] == "skill.fact.review"
            and "监控接口测试确认" in log["message"]
            for log in body["data"]["logs"]
        )
        assert "users" not in body["data"]
        assert "settings" not in body["data"]
        assert "alertRules" not in body["data"]

    async def test_overview_blocked_without_auth(self, client):
        resp = await client.get("/api/v1/admin/overview")
        assert resp.status_code == 401

    async def test_list_crawlers(self, client, auth_headers):
        resp = await client.get("/api/v1/admin/data-sources/2/status", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert "name" in body["data"]

    async def test_removed_placeholder_admin_routes_return_404(
        self, client, auth_headers
    ):
        user_response = await client.put(
            "/api/v1/admin/users/1/status", headers=auth_headers
        )
        settings_response = await client.put(
            "/api/v1/admin/settings", headers=auth_headers, json={}
        )
        assert user_response.status_code == 404
        assert settings_response.status_code == 404
