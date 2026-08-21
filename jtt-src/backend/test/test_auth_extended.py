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
