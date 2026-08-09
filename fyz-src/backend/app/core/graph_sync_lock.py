"""Cross-process serialization for MySQL-to-Neo4j graph rebuilds."""

from contextlib import asynccontextmanager

from sqlalchemy import text

from app.core.database import engine


_GRAPH_SYNC_LOCK_NAME = "jiebang:graph_sync"
_GRAPH_SYNC_LOCK_TIMEOUT_SECONDS = 900


@asynccontextmanager
async def serialized_graph_sync():
    """Hold one MySQL advisory lock for the complete graph synchronization."""
    if engine.dialect.name not in {"mysql", "mariadb"}:
        yield
        return

    async with engine.connect() as lock_connection:
        acquired = await lock_connection.scalar(
            text("SELECT GET_LOCK(:lock_name, :timeout_seconds)"),
            {
                "lock_name": _GRAPH_SYNC_LOCK_NAME,
                "timeout_seconds": _GRAPH_SYNC_LOCK_TIMEOUT_SECONDS,
            },
        )
        if acquired != 1:
            raise RuntimeError("等待其他图谱同步任务完成超时，请稍后重试")
        try:
            yield
        finally:
            await lock_connection.execute(
                text("SELECT RELEASE_LOCK(:lock_name)"),
                {"lock_name": _GRAPH_SYNC_LOCK_NAME},
            )
