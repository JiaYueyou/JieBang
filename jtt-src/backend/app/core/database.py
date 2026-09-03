"""
数据库连接 —— SQLAlchemy 异步引擎 + session 工厂。
测试模式使用 SQLite 内存数据库，生产模式使用 MySQL。
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import DATABASE_URL, TESTING

if TESTING:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
else:
    # 连接池保活配置：
    # - pool_recycle: 连接最长复用 1 小时，主动回收防止 MySQL wait_timeout 掐断后的陈旧连接
    #   （注意：不能加 pool_pre_ping，aiomysql 驱动的 ping() 不兼容会报 missing 'reconnect'）
    # - pool_size/max_overflow: 并发匹配等场景默认 5 连接不够用，提高上限避免排队
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


async def get_db():
    """FastAPI 依赖注入：每次请求创建一个数据库 session，结束后自动关闭"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


