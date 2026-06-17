"""数据库连接"""

import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import DATABASE_URL

TESTING = os.getenv("TESTING") == "true"

if TESTING:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
else:
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
