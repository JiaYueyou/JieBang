"""
认证模块测试 —— 登录、注册、个人信息。
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """测试登录成功"""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser", "password": "123456",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["token"] is not None
    assert data["data"]["user"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """测试密码错误登录失败"""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser", "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    """测试注册新用户"""
    resp = await client.post("/api/v1/auth/register", json={
        "username": "newuser", "email": "new@example.com", "password": "123456",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["token"] is not None


@pytest.mark.asyncio
async def test_get_profile(auth_headers: dict, client: AsyncClient):
    """测试获取个人信息"""
    resp = await client.get("/api/v1/auth/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """测试健康检查"""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["status"] == "running"
