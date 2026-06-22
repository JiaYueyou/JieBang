"""Neo4j 图数据库连接测试"""

import pytest
from app.core.neo4j import (
    get_driver,
    close_driver,
    get_session,
    run_read,
    run_write,
    health_check,
)


@pytest.fixture
def _reset_driver():
    """每个测试前重置驱动（确保用测试配置）"""
    close_driver()
    yield
    close_driver()


@pytest.mark.parametrize(
    "cypher,expected_key",
    [
        ("RETURN 1 AS n", "n"),
        ("RETURN 'hello' AS msg", "msg"),
        ("RETURN {name: 'test'} AS obj", "obj"),
    ],
)
def test_run_read_simple(_reset_driver, cypher, expected_key):
    if not health_check():
        pytest.skip("Neo4j is not running")
    result = run_read(cypher)
    assert len(result) == 1
    assert expected_key in result[0]


def test_health_check_returns_bool(_reset_driver):
    result = health_check()
    assert isinstance(result, bool)
    if not result:
        pytest.skip("Neo4j not running — skipping further connection tests")


def test_driver_is_singleton(_reset_driver):
    if not health_check():
        pytest.skip("Neo4j is not running")
    d1 = get_driver()
    d2 = get_driver()
    assert d1 is d2


def test_get_session(_reset_driver):
    if not health_check():
        pytest.skip("Neo4j is not running")
    with get_session() as session:
        result = session.run("RETURN 1 AS ok")
        assert result.single()["ok"] == 1


def test_write_and_read_node(_reset_driver):
    """创建节点并查询验证"""
    if not health_check():
        pytest.skip("Neo4j is not running")
    # 清理测试数据
    run_write("MATCH (n:TestNode) DELETE n")

    # 创建
    run_write(
        "CREATE (n:TestNode {name: $name, value: $value})",
        {"name": "test", "value": 42},
    )

    # 查询
    result = run_read("MATCH (n:TestNode {name: $name}) RETURN n.name AS name, n.value AS value", {"name": "test"})
    assert len(result) == 1
    assert result[0]["name"] == "test"
    assert result[0]["value"] == 42

    # 清理
    run_write("MATCH (n:TestNode) DELETE n")
