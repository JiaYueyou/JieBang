"""用户 Repository 测试。"""

from app.core.database import async_session
from app.repositories import UserRepository


class TestUserRepository:
    async def test_get_existing_user(self):
        async with async_session() as db:
            repository = UserRepository(db)
            user = await repository.get_by_username("admin")

        assert user is not None
        assert user.username == "admin"

    async def test_get_missing_user(self):
        async with async_session() as db:
            repository = UserRepository(db)
            user = await repository.get_by_username("missing")

        assert user is None

    async def test_create_user(self):
        async with async_session() as db:
            repository = UserRepository(db)
            created = await repository.create(
                username="repository-user",
                password_hash="hashed-value",
            )
            await db.commit()

        assert created.id is not None
        assert created.username == "repository-user"
