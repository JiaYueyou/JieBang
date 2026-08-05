"""
Neo4j 知识图谱连接 —— 单例驱动 + 会话管理，提供读写查询辅助。
"""
import logging
from contextlib import contextmanager

from neo4j import GraphDatabase, Session, Transaction

from app.core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, TESTING

logger = logging.getLogger(__name__)

_driver = None


def get_driver():
    """获取 Neo4j 驱动（单例），首次调用时创建连接池"""
    global _driver
    if _driver is None:
        if TESTING:
            return None
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
        )
    return _driver


def close_driver():
    """关闭 Neo4j 驱动"""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


@contextmanager
def get_session(database: str = "neo4j"):
    """获取 Neo4j 会话的上下文管理器"""
    driver = get_driver()
    session = driver.session(database=database) if driver is not None else None
    try:
        yield session
    finally:
        if session is not None:
            session.close()


def run_read(query: str, params: dict = None, database: str = "neo4j") -> list[dict]:
    """执行只读 Cypher 查询"""
    with get_session(database=database) as session:
        if session is None:
            return []
        result = session.run(query, params or {})
        return [record.data() for record in result]


def _run(tx: Transaction, query: str, params: dict) -> list:
    """事务内执行写入查询"""
    return list(tx.run(query, params))


def run_write(query: str, params: dict = None, database: str = "neo4j") -> list[dict]:
    """执行写入 Cypher 查询"""
    driver = get_driver()
    if driver is None:
        return []
    with driver.session(database=database) as session:
        result = session.execute_write(_run, query, params or {})
        return [record.data() for record in result]


def health_check() -> bool:
    """检查 Neo4j 连接是否正常"""
    try:
        driver = get_driver()
        if driver is None:
            return True
        driver.verify_connectivity()
        return True
    except Exception:
        return False


def health_detail() -> str:
    """返回 Neo4j 连接详情（用于诊断）"""
    try:
        driver = get_driver()
        if driver is None:
            return "Neo4j: testing mode (no driver)"
        driver.verify_connectivity()
        return f"Neo4j connected: {NEO4J_URI}"
    except Exception as exc:
        return f"Neo4j error: {type(exc).__name__}: {exc}"
