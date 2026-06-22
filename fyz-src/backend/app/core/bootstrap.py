"""应用启动数据初始化。"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import (
    INITIAL_ADMIN_ENABLED,
    INITIAL_ADMIN_PASSWORD,
    INITIAL_ADMIN_USERNAME,
)
from app.core.database import async_session
from app.core.security import hash_password
from app.models import User

logger = logging.getLogger(__name__)


async def bootstrap_initial_admin() -> None:
    """按配置创建初始管理员，不负责创建数据库表。"""
    if not INITIAL_ADMIN_ENABLED:
        logger.info("Initial administrator bootstrap is disabled")
        return
    if not INITIAL_ADMIN_PASSWORD:
        raise RuntimeError(
            "INITIAL_ADMIN_PASSWORD is required when INITIAL_ADMIN_ENABLED=true"
        )

    try:
        async with async_session() as db:
            result = await db.execute(
                select(User).where(User.username == INITIAL_ADMIN_USERNAME)
            )
            if result.scalar_one_or_none():
                return

            db.add(
                User(
                    username=INITIAL_ADMIN_USERNAME,
                    password_hash=hash_password(INITIAL_ADMIN_PASSWORD),
                    role="admin",
                )
            )
            await db.commit()
            logger.info("Initial administrator created: %s", INITIAL_ADMIN_USERNAME)
    except SQLAlchemyError as exc:
        logger.exception("Database bootstrap failed")
        raise RuntimeError(
            "Database schema is unavailable. Run 'alembic upgrade head' "
            "before starting the application."
        ) from exc
