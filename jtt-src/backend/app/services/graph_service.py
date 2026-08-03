"""图谱查询服务 —— Neo4j 只读，不处理同步/写入。"""
from __future__ import annotations

import asyncio
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.repositories.graph_repository import Neo4jGraphRepository
from app.schemas.graph import GraphEdge, GraphNode, GraphSubgraph


class GraphService:
    """图谱查询服务（从 Neo4j 只读）"""

    def __init__(self, db: AsyncSession) -> None:
        self.graph = Neo4jGraphRepository()
        self.db = db

    async def panorama(self, **filters) -> GraphSubgraph:
        limit = min(int(filters.pop("limit", 1000)), 1000)
        filters["include_auxiliary"] = filters.get("node_type") in {
            "SourceDocument", "GraphSnapshot"
        }
        rows = await asyncio.to_thread(
            self.graph.query_nodes, limit=limit + 1, **filters
        )
        truncated = len(rows) > limit
        rows = rows[:limit]
        edges = await asyncio.to_thread(
            self.graph.query_edges, [row["id"] for row in rows]
        )
        return self._subgraph(rows, edges, truncated=truncated)

    async def get_node(self, node_id: str) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(
            self.graph.expand, node_id, 1, 100
        )
        if not nodes:
            raise ResourceNotFoundError("图谱节点不存在")
        return self._subgraph(nodes, edges)

    async def expand(self, node_id: str, depth: int, limit: int) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(
            self.graph.expand, node_id, depth, limit + 1
        )
        truncated = len(nodes) > limit
        return self._subgraph(nodes[:limit], edges, truncated=truncated)

    async def search(self, query: str, node_type: str | None, limit: int) -> GraphSubgraph:
        rows = await asyncio.to_thread(
            self.graph.query_nodes, keyword=query, node_type=node_type,
            limit=limit, include_auxiliary=True,
        )
        edges = await asyncio.to_thread(
            self.graph.query_edges, [row["id"] for row in rows]
        )
        return self._subgraph(rows, edges)

    async def path(self, from_id: str, to_id: str, max_depth: int) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(
            self.graph.path, from_id, to_id, max_depth
        )
        return self._subgraph(nodes, edges)

    async def job_tree(self, job_id: int, depth: int) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(
            self.graph.job_tree, f"job:{job_id}", depth
        )
        if not nodes:
            raise ResourceNotFoundError("标准岗位图谱不存在")
        return self._subgraph(nodes, edges)

    def _subgraph(self, rows, edge_rows, *, truncated=False) -> GraphSubgraph:
        nodes = []
        for row in rows:
            props = dict(row["properties"])
            props.pop("namespace", None)
            props.pop("syncVersion", None)
            nodes.append(GraphNode(
                id=row["id"], type=row["type"],
                name=props.pop("name", row["id"]),
                stack=props.pop("stack", None),
                level=props.pop("level", None),
                description=props.pop("description", ""),
                importance=props.pop("importance", None),
                frequency=props.pop("frequency", None),
                properties=props,
            ))
        node_ids = {node.id for node in nodes}
        edges = [
            GraphEdge(
                id=f"{row['relation']}:{row['source']}:{row['target']}",
                source=row["source"], target=row["target"],
                relation=row["relation"],
                properties={
                    key: value for key, value in row.get("properties", {}).items()
                    if key not in {"namespace", "syncVersion"}
                },
            )
            for row in edge_rows
            if row["source"] in node_ids and row["target"] in node_ids
        ]
        return GraphSubgraph(
            nodes=nodes, edges=edges, node_count=len(nodes),
            edge_count=len(edges), truncated=truncated,
        )
