"""健康检查接口测试"""

import pytest


class TestHealth:
    async def test_health_ok(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert body["data"]["status"] == "ok"

    async def test_health_response_structure(self, client):
        resp = await client.get("/api/v1/health")
        body = resp.json()
        assert "code" in body
        assert "message" in body
        assert "data" in body
