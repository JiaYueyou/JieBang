"""应用 bootstrap 测试。"""

import pytest
from sqlalchemy import select

from app.core import bootstrap
from app.core.database import Base, async_session, engine
from app.models import User


class TestInitialAdminBootstrap:
    async def test_existing_admin_is_unchanged(self):
        await bootstrap.bootstrap_initial_admin()

        async with async_session() as db:
            result = await db.execute(select(User).where(User.username == "admin"))
            users = result.scalars().all()

        assert len(users) == 1

    async def test_creates_configured_admin(self, monkeypatch):
        monkeypatch.setattr(bootstrap, "INITIAL_ADMIN_USERNAME", "bootstrap-admin")
        monkeypatch.setattr(bootstrap, "INITIAL_ADMIN_PASSWORD", "secure-password")

        await bootstrap.bootstrap_initial_admin()

        async with async_session() as db:
            result = await db.execute(
                select(User).where(User.username == "bootstrap-admin")
            )
            user = result.scalar_one()

        assert user.role == "admin"

    async def test_missing_schema_has_clear_error(self):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

        with pytest.raises(RuntimeError, match="alembic upgrade head"):
            await bootstrap.bootstrap_initial_admin()
