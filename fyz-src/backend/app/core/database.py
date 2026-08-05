"""数据库连接"""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import DATABASE_URL

TESTING = os.getenv("TESTING") == "true"

if TESTING:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
else:
    engine = create_async_engine(DATABASE_URL, echo=False, pool_recycle=3600)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
