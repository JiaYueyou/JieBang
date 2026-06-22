"""全局异常协议测试。"""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exception_handlers import register_exception_handlers


async def test_unhandled_exception_uses_standard_response():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/explode")
    async def explode():
        raise RuntimeError("internal detail must not leak")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/explode")

    assert response.status_code == 500
    assert response.json() == {
        "code": 50000,
        "message": "服务器内部错误",
        "data": None,
        "meta": None,
    }
