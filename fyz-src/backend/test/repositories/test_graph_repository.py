"""Neo4j Repository 参数化查询与命名空间测试。"""

import app.repositories.graph_repository as graph_module
from app.repositories.graph_repository import Neo4jGraphRepository


def test_merge_uses_parameters_and_jiebang_namespace(monkeypatch):
    calls = []
    monkeypatch.setattr(
        graph_module, "run_write",
        lambda query, params=None: calls.append((query, params)) or [],
    )
    repository = Neo4jGraphRepository()
    repository.merge_nodes(
        "Job",
        [{"id": "job:1", "properties": {"name": "Python 工程师"}}],
        "v1",
    )
    query, params = calls[0]
    assert "$rows" in query
    assert "Python 工程师" not in query
    assert params["namespace"] == "jiebang"


def test_cleanup_never_deletes_other_namespaces(monkeypatch):
    calls = []
    monkeypatch.setattr(
        graph_module, "run_write",
        lambda query, params=None: calls.append((query, params)) or [],
    )
    Neo4jGraphRepository().cleanup_stale("v2")
    assert len(calls) == 2
    assert all(params == {"namespace": "jiebang", "version": "v2"} for _, params in calls)
    assert all("namespace:$namespace" in query for query, _ in calls)
