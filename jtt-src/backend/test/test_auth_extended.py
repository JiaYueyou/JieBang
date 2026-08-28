<<<<<<< HEAD
"""认证资料与密码接口测试。"""

from httpx import AsyncClient


async def test_update_profile_and_password(client: AsyncClient, auth_headers: dict):
    updated = await client.put(
        "/api/v1/auth/profile",
        json={"nickname": "小智", "city": "合肥", "education": "本科"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["nickname"] == "小智"

    wrong = await client.put(
        "/api/v1/auth/password",
        json={"old_password": "wrong", "new_password": "newpass1"},
        headers=auth_headers,
    )
    assert wrong.status_code == 401
    changed = await client.put(
        "/api/v1/auth/password",
        json={"old_password": "123456", "new_password": "newpass1"},
        headers=auth_headers,
    )
    assert changed.status_code == 200
    assert (await client.post("/api/v1/auth/logout", headers=auth_headers)).status_code == 200


async def test_duplicate_registration_and_missing_token(client: AsyncClient):
    duplicate = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "email": "other@example.com", "password": "123456"},
    )
    assert duplicate.status_code == 409
    assert (await client.get("/api/v1/auth/profile")).status_code == 401
=======
import pytest


@pytest.mark.asyncio
async def test_profile_update_and_password_change(client, auth_headers):
    profile = await client.get("/api/v1/auth/profile", headers=auth_headers)
    assert profile.status_code == 200
    assert profile.json()["data"]["username"] == "testuser"

    updated = await client.put(
        "/api/v1/auth/profile",
        json={"nickname": "Updated User", "email": "updated@example.com"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["email"] == "updated@example.com"

    changed = await client.put(
        "/api/v1/auth/password",
        json={"old_password": "123456", "new_password": "newpass123"},
        headers=auth_headers,
    )
    assert changed.status_code == 200

    old_login = await client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "123456"}
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "newpass123"}
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_registration_duplicate_and_logout(client):
    payload = {"username": "newuser", "email": "new@example.com", "password": "password123"}
    registered = await client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 200
    duplicate = await client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409
    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 200


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_old_password(client, auth_headers):
    response = await client.put(
        "/api/v1/auth/password",
        json={"old_password": "wrong-password", "new_password": "newpass123"},
        headers=auth_headers,
    )
    assert response.status_code == 401
>>>>>>> b568d5178201726754523d39b83e833d55cbaa23
