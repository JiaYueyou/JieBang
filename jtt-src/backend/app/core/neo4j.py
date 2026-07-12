"""
Neo4j 知识图谱连接 —— 单例驱动，提供读/写查询辅助函数。
"""
from neo4j import GraphDatabase
from app.core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, TESTING

_driver = None


def get_driver():
    """获取 Neo4j 驱动（单例模式），首次调用时创建连接"""
    global _driver
    if _driver is None:
        if TESTING:
            # 测试模式返回 None，调用方需处理
            return None
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def close_driver():
    """关闭 Neo4j 驱动连接"""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def run_read(query: str, params: dict = None, database: str = "neo4j") -> list[dict]:
    """执行只读 Cypher 查询，返回结果列表"""
    driver = get_driver()
    if driver is None:
        return []
    with driver.session(database=database) as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def run_write(query: str, params: dict = None, database: str = "neo4j") -> list[dict]:
    """执行写入 Cypher 查询，返回结果列表"""
    driver = get_driver()
    if driver is None:
        return []

    def _run(tx, q, p):
        return list(tx.run(q, p))

    with driver.session(database=database) as session:
        result = session.execute_write(_run, query, params or {})
        return [record.data() for record in result]


def health_check() -> bool:
    """检查 Neo4j 连接是否正常"""
    try:
        driver = get_driver()
        if driver is None:
            return True  # 测试模式下跳过
        driver.verify_connectivity()
        return True
    except Exception:
        return False
