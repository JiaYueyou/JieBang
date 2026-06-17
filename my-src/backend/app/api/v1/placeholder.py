"""占位路由工厂 — 所有路由需登录"""

from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.schemas.common import ApiResponse


def make_placeholder_router(prefix: str, tag: str, module_name: str) -> APIRouter:
    router = APIRouter(
        prefix=f"/{prefix}",
        tags=[tag],
        dependencies=[Depends(get_current_user)],
    )

    @router.get("/", response_model=ApiResponse)
    async def module_home():
        return ApiResponse(data={"message": f"{module_name} — 开发中"})

    @router.get("/health", response_model=ApiResponse)
    async def module_health():
        return ApiResponse(data={"status": "ok", "module": module_name})

    return router
