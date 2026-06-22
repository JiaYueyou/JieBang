"""认证 Service 测试。"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import async_session
from app.core.exceptions import DuplicateUsernameError, InvalidCredentialsError
from app.repositories import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import AuthService


class TestAuthService:
    async def test_login_success(self):
        async with async_session() as db:
            service = AuthService(db)
            result = await service.login(
                LoginRequest(username="admin", password="admin123")
            )

        assert result.username == "admin"
        assert result.token_type == "bearer"
        assert result.access_token

    async def test_login_wrong_password(self):
        async with async_session() as db:
            service = AuthService(db)
            with pytest.raises(InvalidCredentialsError):
                await service.login(
                    LoginRequest(username="admin", password="wrong-password")
                )

    async def test_register_success(self):
        async with async_session() as db:
            service = AuthService(db)
            await service.register(
                RegisterRequest(username="service-user", password="password")
            )
            created = await UserRepository(db).get_by_username("service-user")

        assert created is not None

    async def test_register_duplicate_from_precheck(self):
        async with async_session() as db:
            service = AuthService(db)
            with pytest.raises(DuplicateUsernameError):
                await service.register(
                    RegisterRequest(username="admin", password="password")
                )

    async def test_register_duplicate_from_database_race(self):
        db = AsyncMock()
        repository = AsyncMock()
        repository.get_by_username.return_value = None
        repository.create.side_effect = IntegrityError(
            statement="INSERT",
            params={},
            orig=Exception("duplicate"),
        )
        service = AuthService(db, user_repository=repository)

        with pytest.raises(DuplicateUsernameError):
            await service.register(
                RegisterRequest(username="race-user", password="password")
            )

        db.rollback.assert_awaited_once()
