"""应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import bootstrap_initial_admin
from app.core.exception_handlers import register_exception_handlers
from app.core.neo4j import close_driver as close_neo4j
from app.schemas.common import ApiResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.skills import router as skills_router
from app.api.v1.data_imports import router as data_imports_router
from app.api.v1.graph import router as graph_router
from app.api.v1.placeholder import make_placeholder_router


# --- 占位路由 ---
changes_router = make_placeholder_router("changes", "能力更新", "既有岗位能力动态更新")
matching_router = make_placeholder_router("matching", "匹配诊断", "人岗匹配度诊断")
analysis_router = make_placeholder_router("analysis", "趋势分析", "动态演化趋势分析")
admin_router = make_placeholder_router("admin", "系统管理", "系统管理")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 数据库 Schema 由 Alembic 管理；启动阶段只执行显式数据 bootstrap。
    await bootstrap_initial_admin()
    # 初始化 Neo4j 驱动
    from app.core.neo4j import get_driver

    get_driver()
    yield
    close_neo4j()


app = FastAPI(
    title="智联职引——面向数字产业的人才岗位智能适配体系",
    version="0.1.0",
    lifespan=lifespan,
)
register_exception_handlers(app)

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
app.include_router(matching_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/api/v1/health", response_model=ApiResponse)
async def health():
    return ApiResponse(data={"status": "ok", "version": "0.1.0"})
