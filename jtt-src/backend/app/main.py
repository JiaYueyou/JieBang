"""
FastAPI 应用入口 —— 注册路由、中间件、异常处理，启动/关闭时管理 Neo4j 连接。
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import TESTING, INITIAL_ADMIN_ENABLED, INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_PASSWORD
from app.core.database import engine, Base, async_session
from app.core.neo4j import get_driver, close_driver
from app.core.exceptions import register_exception_handlers
from app.api.v1 import auth, graph, positions, resume, match, tailor, learning, favorites

logger = logging.getLogger(__name__)


async def init_db():
    """创建所有数据库表（开发/测试模式自动建表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_initial_admin():
    """创建初始管理员账号（如已存在则跳过）"""
    from app.repositories.user_repository import UserRepository
    import bcrypt

    async with async_session() as db:
        repo = UserRepository(db)
        existing = await repo.get_by_username(INITIAL_ADMIN_USERNAME)
        if existing:
            return
        password_hash = bcrypt.hashpw(INITIAL_ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        await repo.create(INITIAL_ADMIN_USERNAME, "admin@jiebang.local", password_hash)
        await db.commit()
        logger.info(f"初始管理员账号已创建: {INITIAL_ADMIN_USERNAME}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时建表+初始化 Neo4j + 创建管理员，关闭时断开连接"""
    # 启动时（init_db 失败不阻止服务启动，健康检查会反映数据库状态）
    try:
        await init_db()
    except Exception as e:
        logger.error(f"数据库初始化失败，服务降级启动: {e}")
    if INITIAL_ADMIN_ENABLED:
        try:
            await create_initial_admin()
        except Exception as e:
            logger.warning(f"创建初始管理员失败（可能数据库未就绪）: {e}")
    # 种子数据（岗位、简历、学习路径、收藏），仅在表为空时填充
    try:
        from app.seed import seed_all
        await seed_all()
        logger.info("种子数据检查完成")
    except Exception as e:
        logger.warning(f"种子数据填充失败（可能数据库未就绪）: {e}")
    try:
        get_driver()  # 初始化 Neo4j 连接
    except Exception as e:
        logger.warning(f"Neo4j 连接失败，图谱功能暂不可用: {e}")
    yield
    # 关闭时
    close_driver()


# 创建 FastAPI 应用
app = FastAPI(
    title="智联职引 - 用户端 API",
    description="人才分析与决策系统 —— 岗位探索、简历管理、人岗匹配、学习路径推荐",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 跨域配置（允许前端开发服务器访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全局异常处理器（统一 API 返回格式）
register_exception_handlers(app)

# 注册所有 API 路由（统一前缀 /api/v1）
app.include_router(auth.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(positions.router, prefix="/api/v1")
app.include_router(resume.router, prefix="/api/v1")
app.include_router(match.router, prefix="/api/v1")
app.include_router(tailor.router, prefix="/api/v1")
app.include_router(learning.router, prefix="/api/v1")
app.include_router(favorites.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check():
    """健康检查端点"""
    import asyncio
    neo4j_ok = True
    try:
        driver = get_driver()
        if driver is not None:
            # 同步连通性检查放线程池执行，Neo4j 卡顿时也不阻塞事件循环
            await asyncio.to_thread(driver.verify_connectivity)
    except Exception:
        neo4j_ok = False
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "status": "running",
            "database": "connected",
            "neo4j": "connected" if neo4j_ok else "unavailable",
        },
    }


# 启动命令: uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8002, reload=True)
