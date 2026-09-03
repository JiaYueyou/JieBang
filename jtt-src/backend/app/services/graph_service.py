"""图谱查询与按需富化服务。"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.providers.llm import DeepSeekProvider
from app.repositories.graph_repository import Neo4jGraphRepository
from app.schemas.graph import GraphEdge, GraphNode, GraphSubgraph

logger = logging.getLogger(__name__)


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

    async def enrich_skill(self, node_id: str) -> GraphSubgraph:
        """对指定 TechStack 节点调用 LLM 生成 L4(技术点)+L5(知识点) 并写入 Neo4j"""
        # 查询技能节点（同步驱动放线程池，避免阻塞事件循环）
        skill_nodes = await asyncio.to_thread(
            self.graph.query_nodes,
            node_type="TechStack", limit=1, include_auxiliary=True,
        )
        # query_nodes 不支持按 id 精确查，换用 expand
        nodes, _ = await asyncio.to_thread(self.graph.expand, node_id, 0, 1)
        if not nodes or "TechStack" not in nodes[0].get("type", ""):
            raise ResourceNotFoundError(f"技能节点不存在或类型错误: {node_id}")

        skill = nodes[0]
        skill_name = skill["properties"].get("name", "")
        skill_props = skill["properties"]

        # 检查是否已有子节点（避免重复生成）
        _, existing_edges = await asyncio.to_thread(self.graph.expand, node_id, 2, 200)
        has_children = any(
            e["relation"] in ("REFINES_TO",) and e["source"] == node_id
            for e in existing_edges
        )
        if has_children:
            # 已有数据，直接返回现有子图
            nodes2, edges2 = await asyncio.to_thread(self.graph.expand, node_id, 2, 200)
            return self._subgraph(nodes2, edges2)

        logger.info(f"enrich_skill: generating L4/L5 for {skill_name} ({node_id})")

        # 构造 LLM prompt
        category = skill_props.get("description", "").replace(" 标准技能", "")
        prompt = f"""你是一个技术技能分析专家。请将以下技能拆解为具体的技术点和知识点。

技能名称：{skill_name}
技能类别：{category}

请严格按照以下 JSON 格式输出（不要输出其他内容）：
{{
  "tech_points": [
    {{
      "name": "技术点名称",
      "detail": "1-2句话详细描述该技术点是什么、为什么重要",
      "knowledge_points": [
        {{"name": "知识点名称", "description": "该知识点的简要说明", "difficulty": "beginner|intermediate|advanced"}}
      ]
    }}
  ]
}}

要求：
- 生成 3-6 个技术点
- 每个技术点包含 2-5 个知识点
- 技术点应该覆盖该技能的核心方向
- 知识点应该是具体可学习的概念或工具"""

        # 调用 LLM
        llm = DeepSeekProvider()
        try:
            response = await llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response["content"]
            # 清理可能的 markdown 代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            data = json.loads(content)
        except Exception as e:
            logger.exception(f"enrich_skill: LLM call failed for {skill_name}")
            raise RuntimeError(f"LLM 生成失败: {str(e)}")

        tech_points = data.get("tech_points", [])
        if not tech_points:
            raise RuntimeError("LLM 未返回有效的技术点")

        # 解析 skill_id (格式: "skill:123")
        skill_id_num = node_id.split(":", 1)[1] if ":" in node_id else node_id

        # 构建节点和边
        new_nodes: list[dict] = []
        new_edges: list[dict] = []
        version = "enrich:" + str(uuid.uuid4())[:8]

        for pi, point in enumerate(tech_points):
            point_id = f"point:{skill_id_num}:{pi}"
            new_nodes.append({
                "id": point_id,
                "properties": {
                    "name": point["name"],
                    "description": point.get("detail", ""),
                    "stack": skill_props.get("stack", "backend"),
                    "level": "middle",
                    "importance": 0.85 - pi * 0.05,  # 第一个最重要
                },
            })
            new_edges.append({
                "source": node_id,
                "target": point_id,
                "properties": {"confidence": 0.9, "sourceCount": 1},
            })
            for ki, kp in enumerate(point.get("knowledge_points", [])):
                kp_id = f"knowledge:{skill_id_num}:{pi}:{ki}"
                new_nodes.append({
                    "id": kp_id,
                    "properties": {
                        "name": kp["name"],
                        "description": kp.get("description", ""),
                        "stack": skill_props.get("stack", "backend"),
                        "level": "middle",
                        "difficulty": kp.get("difficulty", "intermediate"),
                        "importance": 0.85 - pi * 0.05 - ki * 0.02,
                    },
                })
                new_edges.append({
                    "source": point_id,
                    "target": kp_id,
                    "properties": {"confidence": 0.85, "sourceCount": 1},
                })

        # 写入 Neo4j（写操作同样放线程池，避免写入期间阻塞事件循环）
        await asyncio.to_thread(self.graph.ensure_schema)
        await asyncio.to_thread(self.graph.merge_nodes, "TechPoint", new_nodes, version)
        await asyncio.to_thread(self.graph.merge_nodes, "KnowledgePoint", new_nodes, version)
        await asyncio.to_thread(self.graph.merge_edges, "REFINES_TO", new_edges, version)
        await asyncio.to_thread(self.graph.merge_edges, "HAS_KNOWLEDGE", new_edges, version)

        # 返回完整子图
        all_nodes, all_edges = await asyncio.to_thread(self.graph.expand, node_id, 2, 300)
        return self._subgraph(all_nodes, all_edges)

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
