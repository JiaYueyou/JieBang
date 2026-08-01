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


def test_merge_serializes_nested_solution_properties(monkeypatch):
    calls = []
    monkeypatch.setattr(
        graph_module, "run_write",
        lambda query, params=None: calls.append((query, params)) or [],
    )
    Neo4jGraphRepository().merge_nodes(
        "KnowledgePoint",
        [{
            "id": "knowledge:1",
            "properties": {
                "core_stack": ["WSGI", "Jinja2"],
                "common_solutions": [
                    {"name": "Flask-SQLAlchemy", "purpose": "ORM 与数据访问"}
                ],
            },
        }],
        "v3",
    )

    properties = calls[0][1]["rows"][0]["properties"]
    assert properties["core_stack"] == ["WSGI", "Jinja2"]
    assert properties["common_solutions"] == (
        '[{"name":"Flask-SQLAlchemy","purpose":"ORM 与数据访问"}]'
    )


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


def test_query_nodes_excludes_non_graph_labels(monkeypatch):
    calls = []
    monkeypatch.setattr(
        graph_module, "run_read",
        lambda query, params=None: calls.append((query, params)) or [],
    )

    Neo4jGraphRepository().query_nodes(limit=1001)

    query, params = calls[0]
    assert "n.id IS NOT NULL" in query
    assert "label IN $allowed_labels" in query
    assert "head([label IN labels(n)" in query
    assert "EvidenceChunk" not in params["allowed_labels"]
    assert set(params["allowed_labels"]) == graph_module.GRAPH_LABELS
