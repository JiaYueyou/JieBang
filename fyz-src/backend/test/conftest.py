"""pytest fixtures — SQLite 内存模式 + 自动种子数据"""

import asyncio
import os
import tempfile

os.environ["TESTING"] = "true"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("INITIAL_ADMIN_ENABLED", "true")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "test-only-admin-password")
# 测试必须不调用外部模型服务，也不能消耗开发者本地 .env 中的真实额度。
os.environ["DEEPSEEK_API_KEY"] = ""
# Keep tests isolated from the repository's private runtime storage and its
# machine-specific ACLs. Resume API tests write only to this disposable root.
_TEST_STORAGE = tempfile.TemporaryDirectory(prefix="jiebang-test-storage-")
os.environ["LOCAL_STORAGE_PATH"] = _TEST_STORAGE.name

import pytest
from httpx import ASGITransport, AsyncClient

pytest_plugins = ("pytest_asyncio",)


def _run_async(coro):
    loop = asyncio.get_event_loop_policy().get_event_loop()
    if loop.is_running():
        # nested — use existing loop via asyncio.ensure_future trick
        import concurrent.futures
        future = concurrent.futures.Future()
        async def _wrap():
            try:
                future.set_result(await coro)
            except Exception as e:
                future.set_exception(e)
        loop.create_task(_wrap())
        return concurrent.futures.wait([future], timeout=30)
    return loop.run_until_complete(coro)


@pytest.fixture(autouse=True)
def _setup_db():
    """每条测试前重建干净数据库（同步 fixture，用 asyncio.run 创建独立事件循环）"""
    from app.core.database import engine, async_session, Base
    from app.core.security import hash_password
    from app.models.user import User

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with async_session() as db:
            db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin"))
            db.add(User(username="normal", password_hash=hash_password("user123"), role="user"))
            await db.commit()

    asyncio.run(_init())
    yield


@pytest.fixture
async def client():
    """异步 HTTP 客户端"""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers(client):
    """登录获取 Authorization 头"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    data = resp.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}
