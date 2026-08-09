"""Cross-process serialization for end-to-end data refreshes."""

from contextlib import asynccontextmanager

from sqlalchemy import text

from app.core.database import engine


_LOCK_NAME = "jiebang:automatic_pipeline"
_LOCK_TIMEOUT_SECONDS = 3600


@asynccontextmanager
async def serialized_pipeline_run():
    if engine.dialect.name not in {"mysql", "mariadb"}:
        yield
        return
    async with engine.connect() as connection:
        acquired = await connection.scalar(
            text("SELECT GET_LOCK(:name, :timeout)"),
            {"name": _LOCK_NAME, "timeout": _LOCK_TIMEOUT_SECONDS},
        )
        if acquired != 1:
            raise RuntimeError("等待其他自动更新流水线完成超时")
        try:
            yield
        finally:
            await connection.execute(
                text("SELECT RELEASE_LOCK(:name)"), {"name": _LOCK_NAME}
            )
