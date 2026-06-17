"""认证接口测试"""

import pytest


class TestLogin:
    async def test_login_ok(self, client):
        resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert "access_token" in body["data"]
        assert body["data"]["token_type"] == "bearer"
        assert body["data"]["username"] == "admin"

    async def test_login_wrong_password(self, client):
        resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 40001
        assert body["data"] is None

    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/api/v1/auth/login", json={"username": "nobody", "password": "x"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 40001

    async def test_login_missing_fields(self, client):
        resp = await client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422  # Pydantic validation error

    async def test_login_missing_password(self, client):
        resp = await client.post("/api/v1/auth/login", json={"username": "admin"})
        assert resp.status_code == 422


class TestRegister:
    async def test_register_ok(self, client):
        resp = await client.post("/api/v1/auth/register", json={"username": "newuser", "password": "pass123"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        # 验证可以登录
        resp2 = await client.post("/api/v1/auth/login", json={"username": "newuser", "password": "pass123"})
        assert resp2.json()["code"] == 200

    async def test_register_duplicate(self, client):
        resp = await client.post("/api/v1/auth/register", json={"username": "admin", "password": "x"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 40002


class TestAuthRequired:
    async def test_no_token_returns_401(self, client):
        resp = await client.get("/api/v1/jobs/")
        assert resp.status_code == 401

    async def test_bad_token_returns_401(self, client):
        resp = await client.get("/api/v1/jobs/", headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 401

    async def test_authenticated_access_ok(self, client, auth_headers):
        resp = await client.get("/api/v1/jobs/", headers=auth_headers)
        assert resp.status_code == 200
