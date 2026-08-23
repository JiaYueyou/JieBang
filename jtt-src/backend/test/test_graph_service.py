from unittest.mock import Mock

import pytest

from app.core.exceptions import ResourceNotFoundError
from app.services.graph_service import GraphService


def node(node_id="skill:1", name="Python"):
    return {
        "id": node_id, "type": "TechStack",
        "properties": {"name": name, "stack": "backend", "namespace": "jiebang"},
    }


def edge(source="skill:1", target="point:1"):
    return {
        "source": source, "target": target, "relation": "REFINES_TO",
        "properties": {"confidence": 0.9, "syncVersion": "ignored"},
    }


@pytest.mark.asyncio
async def test_graph_query_operations(monkeypatch, db_session):
    service = GraphService(db_session)
    service.graph = Mock()
    rows = [node(), node("point:1", "FastAPI")]
    edges = [edge()]
    service.graph.query_nodes.return_value = rows
    service.graph.query_edges.return_value = edges
    service.graph.expand.return_value = (rows, edges)
    service.graph.path.return_value = (rows, edges)
    service.graph.job_tree.return_value = (rows, edges)

    panorama = await service.panorama(keyword="Python", limit=1)
    assert panorama.node_count == 1
    assert panorama.truncated is True

    detail = await service.get_node("skill:1")
    assert detail.edge_count == 1
    expanded = await service.expand("skill:1", 2, 1)
    assert expanded.truncated is True
    searched = await service.search("Python", None, 10)
    assert searched.node_count == 2
    path = await service.path("skill:1", "point:1", 3)
    assert path.edge_count == 1
    tree = await service.job_tree(1, 3)
    assert tree.node_count == 2


@pytest.mark.asyncio
async def test_graph_missing_node_and_tree(db_session):
    service = GraphService(db_session)
    service.graph = Mock()
    service.graph.expand.return_value = ([], [])
    service.graph.job_tree.return_value = ([], [])

    with pytest.raises(ResourceNotFoundError):
        await service.get_node("missing")
    with pytest.raises(ResourceNotFoundError):
        await service.job_tree(999, 2)


def test_subgraph_filters_external_edges_and_internal_properties(db_session):
    service = GraphService(db_session)
    result = service._subgraph(
        [node()], [edge(), edge("skill:1", "outside")], truncated=True
    )
    assert result.node_count == 1
    assert result.edge_count == 0
    assert result.nodes[0].properties == {}
    assert result.truncated is True

