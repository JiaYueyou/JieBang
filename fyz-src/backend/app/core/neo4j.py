"""Neo4j 图数据库连接"""

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

from neo4j import GraphDatabase, Driver, Session, Transaction
from app.core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

_driver: Optional[Driver] = None


def get_driver() -> Driver:
    """获取 Neo4j 驱动（单例）"""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
        )
        logger.info("Neo4j driver initialized: %s", NEO4J_URI)
    return _driver


def close_driver():
    """关闭 Neo4j 驱动"""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


@contextmanager
def get_session(database: str = "neo4j") -> Iterator[Session]:
    """获取 Neo4j session（上下文管理器）"""
    driver = get_driver()
    session = driver.session(database=database)
    try:
        yield session
    finally:
        session.close()


def run_read(query: str, params: dict = None, database: str = "neo4j") -> list:
    """执行只读 Cypher 查询，返回记录列表"""
    with get_session(database=database) as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def run_write(query: str, params: dict = None, database: str = "neo4j") -> list:
    """执行写入 Cypher 查询，返回记录列表"""
    with get_session(database=database) as session:
        result = session.execute_write(_run, query, params or {})
        return [record.data() for record in result]


def _run(tx: Transaction, query: str, params: dict) -> list:
    return list(tx.run(query, params))


def health_check() -> bool:
    """测试 Neo4j 连接，返回 True/False"""
    try:
        result = run_read("RETURN 1 AS ok")
        return result[0]["ok"] == 1
    except Exception:
        return False


def health_detail() -> str:
    """测试 Neo4j 连接，返回详细信息（含错误原因）"""
    try:
        result = run_read("RETURN 1 AS ok")
        if result[0]["ok"] == 1:
            return f"OK — connected to {NEO4J_URI}"
        return f"Unexpected result: {result}"
    except Exception as e:
        return f"FAILED: {type(e).__name__}: {e}"
