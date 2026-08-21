"""知识图谱接口契约测试（Neo4j 使用服务 Mock）。"""

import pytest
from httpx import AsyncClient

from app.api.v1.graph import get_graph_service
from app.main import app


class FakeGraphService:
    async def panorama(self, **kwargs): return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}
    async def get_node(self, node_id): return {"nodes": [], "edges": []}
    async def expand(self, node_id, depth, limit): return {"nodes": [], "edges": []}
    async def search(self, q, types, limit): return {"nodes": [], "edges": []}
    async def path(self, from_id, to_id, max_depth): return {"nodes": [], "edges": []}
    async def job_tree(self, job_id, depth): return {"nodes": [], "edges": []}
    async def enrich_skill(self, node_id): return {"nodes": [], "edges": []}


@pytest.fixture(autouse=True)
def graph_override():
    app.dependency_overrides[get_graph_service] = lambda: FakeGraphService()
    yield
    app.dependency_overrides.pop(get_graph_service, None)


async def test_all_graph_queries(client: AsyncClient):
    requests = [
        ("GET", "/api/v1/graph/panorama?stack=backend"),
        ("GET", "/api/v1/graph/nodes/skill:python"),
        ("GET", "/api/v1/graph/expand?node_id=skill:python&depth=2"),
        ("GET", "/api/v1/graph/search?q=Python"),
        ("GET", "/api/v1/graph/path?from_id=a&to_id=b"),
        ("GET", "/api/v1/graph/jobs/1/tree"),
        ("POST", "/api/v1/graph/enrich/skill:python"),
    ]
    for method, url in requests:
        response = await client.request(method, url)
        assert response.status_code == 200, (url, response.text)
        assert response.json()["code"] == 200


async def test_graph_query_validation(client: AsyncClient):
    assert (await client.get("/api/v1/graph/search?q=")).status_code == 422
    assert (await client.get("/api/v1/graph/expand?node_id=x&depth=9")).status_code == 422
