"""
数据库连接 —— SQLAlchemy 异步引擎 + session 工厂。
测试模式使用 SQLite 内存数据库，生产模式使用 MySQL。
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import DATABASE_URL, RAW_DB_URL, TESTING

if TESTING:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    raw_engine = engine  # 测试模式共用
else:
    engine = create_async_engine(DATABASE_URL, echo=False)
    raw_engine = create_async_engine(RAW_DB_URL, echo=False)  # 爬虫库只读

# 异步 session 工厂
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
raw_async_session = async_sessionmaker(raw_engine, class_=AsyncSession, expire_on_commit=False)


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


async def get_raw_db():
    """返回爬虫数据库 session（只读）"""
    async with raw_async_session() as session:
        try:
            yield session
        finally:
            await session.close()
