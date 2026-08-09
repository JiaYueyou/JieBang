"""应用入口"""

from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import bootstrap_initial_admin
from app.core.exception_handlers import register_exception_handlers
from app.core.neo4j import close_driver as close_neo4j
from app.core.config import AUTO_PIPELINE_ENABLED, AUTO_PIPELINE_STARTUP_DELAY_SECONDS
from app.schemas.common import ApiResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.skills import router as skills_router
from app.api.v1.data_imports import router as data_imports_router
from app.api.v1.graph import router as graph_router
from app.api.v1.agents import router as agents_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.career import router as career_router
from app.api.v1.matching import router as matching_router
from app.api.v1.internal_transfer import router as internal_transfer_router
from app.api.v1.admin import router as admin_router
from app.api.v1.user_activity import router as user_activity_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.placeholder import make_placeholder_router


# --- 占位路由 ---
changes_router = make_placeholder_router("changes", "能力更新", "既有岗位能力动态更新")
logger = logging.getLogger("app.business")
# Uvicorn 默认只配置自身 logger；显式开启 app.* 业务日志并复用其输出 handler。
logging.getLogger("app").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 数据库 Schema 由 Alembic 管理；启动阶段只执行显式数据 bootstrap。
    await bootstrap_initial_admin()
    # Agent 使用进程内异步任务，不依赖 Redis/Celery；重启后恢复未完成任务。
    from app.core.agent_task_runner import (
        recover_pending_agent_tasks,
        shutdown_agent_tasks,
    )

    await recover_pending_agent_tasks()
    from app.services.pipeline_service import (
        recover_pipeline_runs,
        shutdown_pipeline_scheduler,
        start_pipeline_scheduler,
    )

    await recover_pipeline_runs()
    if AUTO_PIPELINE_ENABLED:
        await start_pipeline_scheduler(AUTO_PIPELINE_STARTUP_DELAY_SECONDS)
    # 初始化 Neo4j 驱动
    from app.core.neo4j import get_driver

    get_driver()
    yield
    await shutdown_pipeline_scheduler()
    await shutdown_agent_tasks()
    close_neo4j()


app = FastAPI(
    title="智联职引——面向数字产业的人才岗位智能适配体系",
    version="0.1.0",
    lifespan=lifespan,
)
register_exception_handlers(app)


@app.middleware("http")
async def request_business_log(request: Request, call_next):
    """输出可关联的请求生命周期日志；不记录请求体、令牌等敏感数据。"""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    logger.info(
        "request_started request_id=%s method=%s path=%s client=%s",
        request_id, request.method, request.url.path,
        request.client.host if request.client else "unknown",
    )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%d",
            request_id, request.method, request.url.path,
            int((time.perf_counter() - started) * 1000),
        )
        raise
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed request_id=%s method=%s path=%s status=%d duration_ms=%d",
        request_id, request.method, request.url.path, response.status_code,
        int((time.perf_counter() - started) * 1000),
    )
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(skills_router, prefix="/api/v1")
app.include_router(data_imports_router, prefix="/api/v1")
app.include_router(changes_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(matching_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(career_router, prefix="/api/v1")
app.include_router(internal_transfer_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(user_activity_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(retrieval_router, prefix="/api/v1")


@app.get("/api/v1/health", response_model=ApiResponse)
async def health():
    return ApiResponse(data={"status": "ok", "version": "0.1.0"})
