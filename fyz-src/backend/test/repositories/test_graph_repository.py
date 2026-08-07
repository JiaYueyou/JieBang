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


def test_query_nodes_keyword_only_matches_existing_properties(monkeypatch):
    """keyword 分支不得引用库中不存在的 parent_* 属性（避免 Neo4j 属性警告）。"""
    calls = []
    monkeypatch.setattr(
        graph_module, "run_read",
        lambda query, params=None: calls.append((query, params)) or [],
    )

    Neo4jGraphRepository().query_nodes(keyword="spring", limit=10)

    query, _ = calls[0]
    assert "n.name" in query and "n.description" in query
    assert "parent_skill" not in query
    assert "parent_tech_point" not in query


def test_search_nodes_uses_quoted_fulltext_query(monkeypatch):
    calls = []
    monkeypatch.setattr(
        graph_module, "run_read",
        lambda query, params=None: calls.append((query, params)) or [],
    )

    Neo4jGraphRepository().search_nodes(query="Spring Boot", limit=20)

    query, params = calls[0]
    assert "db.index.fulltext.queryNodes" in query
    assert params["query"] == '"Spring Boot"'
    assert set(params["allowed_labels"]) == graph_module.GRAPH_LABELS


def test_search_nodes_special_characters_use_compatible_query(monkeypatch):
    calls = []
    monkeypatch.setattr(
        graph_module, "run_read",
        lambda query, params=None: calls.append((query, params)) or [],
    )

    Neo4jGraphRepository().search_nodes(query="C++", node_type="TechStack")

    query, params = calls[0]
    assert "db.index.fulltext.queryNodes" not in query
    assert params["keyword"] == "C++"
    assert params["node_type"] == "TechStack"


def test_search_nodes_falls_back_when_fulltext_index_is_unavailable(monkeypatch):
    calls = []

    def fake_run_read(query, params=None):
        calls.append((query, params))
        if "db.index.fulltext.queryNodes" in query:
            raise RuntimeError("index is still populating")
        return []

    monkeypatch.setattr(graph_module, "run_read", fake_run_read)

    assert Neo4jGraphRepository().search_nodes(query="Python") == []
    assert len(calls) == 2
    assert "db.index.fulltext.queryNodes" in calls[0][0]
    assert "MATCH (n {namespace:$namespace})" in calls[1][0]


def test_expand_and_path_only_use_written_relationship_types(monkeypatch):
    """expand/path 查询白名单不得引用未写入的关系类型（避免 Neo4j 关系类型警告）。"""
    calls = []
    monkeypatch.setattr(
        graph_module, "run_read",
        lambda query, params=None: calls.append((query, params)) or [{"nodes": [], "edges": []}],
    )

    Neo4jGraphRepository().expand("job:1", depth=2, limit=50)
    Neo4jGraphRepository().path("job:1", "point:x", max_depth=3)

    assert len(calls) == 2
    for query, _ in calls:
        assert "RELATED_TO" not in query
        assert "PREREQUISITE" not in query
        assert "REQUIRES_AREA" in query and "REFINES_TO" in query


def test_graph_relations_match_written_relationship_types():
    """GRAPH_RELATIONS 白名单与写入实现一致，不含未实现类型。"""
    assert "RELATED_TO" not in graph_module.GRAPH_RELATIONS
    assert "PREREQUISITE" not in graph_module.GRAPH_RELATIONS
    assert {"REQUIRES_AREA", "CONTAINS", "REFINES_TO", "HAS_KNOWLEDGE"} <= graph_module.GRAPH_RELATIONS
