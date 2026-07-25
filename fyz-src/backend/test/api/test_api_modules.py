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
        resp = await client.get("/api/v1/admin/overview", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert "metrics" in body["data"]
        assert "crawlers" in body["data"]

    async def test_overview_blocked_without_auth(self, client):
        resp = await client.get("/api/v1/admin/overview")
        assert resp.status_code == 401

    async def test_list_crawlers(self, client, auth_headers):
        resp = await client.get("/api/v1/admin/data-sources/1/status", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert "name" in body["data"]
