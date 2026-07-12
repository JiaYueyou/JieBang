"""
测试配置 —— 测试模式使用 SQLite 内存数据库，创建测试客户端。
"""
import os
os.environ["TESTING"] = "true"
os.environ["LLM_API_KEY"] = ""  # 测试时禁用 LLM 调用
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import Base, engine, async_session
from app.models.user import User
import bcrypt


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """每个测试前重建数据库表，并创建测试用户"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 创建测试用户
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode(),
        )
        session.add(user)
        await session.commit()

    yield


@pytest_asyncio.fixture
async def client():
    """异步 HTTP 测试客户端"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    """获取测试用户的 Bearer token 请求头"""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "testuser", "password": "123456",
    })
    data = resp.json()
    token = data["data"]["token"]
    return {"Authorization": f"Bearer {token}"}
