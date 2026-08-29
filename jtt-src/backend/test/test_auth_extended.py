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
