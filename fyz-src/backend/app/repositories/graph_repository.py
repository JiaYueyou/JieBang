"""MySQL 图谱审计访问与参数化 Neo4j 访问。"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.neo4j import run_read, run_write
from app.models import (
    GraphEnrichmentCandidate,
    GraphSnapshot,
    GraphSyncBatch,
    StandardJob,
    StandardJobSource,
)

GRAPH_LABELS = {
    "Job", "SkillArea", "TechStack", "TechPoint",
    "KnowledgePoint", "SourceDocument", "GraphSnapshot",
}
GRAPH_RELATIONS = {
    "REQUIRES_AREA", "CONTAINS", "REFINES_TO", "HAS_KNOWLEDGE",
    "RELATED_TO", "PREREQUISITE", "SUPPORTS", "HAS_SNAPSHOT",
}

logger = logging.getLogger(__name__)
_LUCENE_SPECIAL = re.compile(r'[+\-!(){}\[\]^"~*?:\\/]|&&|\|\|')


class GraphAuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_standard_job(self, canonical_key: str) -> StandardJob | None:
        return (await self.db.execute(
            select(StandardJob).where(StandardJob.canonical_key == canonical_key)
        )).scalar_one_or_none()

    async def get_source(self, source_type: str, source_id: int) -> StandardJobSource | None:
        return (await self.db.execute(select(StandardJobSource).where(
            StandardJobSource.source_type == source_type,
            StandardJobSource.source_id == source_id,
        ))).scalar_one_or_none()

    async def list_snapshots(self) -> list[GraphSnapshot]:
        rows = await self.db.execute(
            select(GraphSnapshot).order_by(GraphSnapshot.created_at.desc())
        )
        return list(rows.scalars())

    async def get_snapshot(self, snapshot_id: str) -> GraphSnapshot | None:
        return await self.db.get(GraphSnapshot, snapshot_id)

    async def count_standard_jobs(self) -> int:
        return int(await self.db.scalar(select(func.count(StandardJob.id))) or 0)

    async def add_candidate(self, candidate: GraphEnrichmentCandidate) -> None:
        self.db.add(candidate)
        await self.db.flush()


class Neo4jGraphRepository:
    namespace = "jiebang"

    def ensure_schema(self) -> None:
        # ── 唯一约束 ──
        for label in GRAPH_LABELS:
            run_write(
                f"CREATE CONSTRAINT {label.lower()}_jiebang_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE (n.namespace, n.id) IS UNIQUE"
            )
            run_write(
                f"CREATE INDEX {label.lower()}_jiebang_name IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.namespace, n.name)"
            )
        run_write(
            "CREATE INDEX job_jiebang_filter IF NOT EXISTS "
            "FOR (n:Job) ON (n.namespace, n.stack, n.level)"
        )

        # ── 全文搜索索引（加速 CONTAINS 搜索）──
        run_write(
            "CREATE FULLTEXT INDEX graph_name_search IF NOT EXISTS "
            "FOR (n:Job|SkillArea|TechStack|TechPoint|KnowledgePoint) "
            "ON EACH [n.name, n.description]"
        )

        # ── 属性过滤索引（加速过滤与排序）──
        # Job: stack/level 用于岗位筛选
        run_write("CREATE RANGE INDEX idx_job_stack IF NOT EXISTS FOR (n:Job) ON (n.stack)")
        run_write("CREATE RANGE INDEX idx_job_level IF NOT EXISTS FOR (n:Job) ON (n.level)")
        # TechStack: frequency 用于技能排序
        run_write("CREATE RANGE INDEX idx_techstack_freq IF NOT EXISTS FOR (n:TechStack) ON (n.frequency)")
        # TechPoint/KnowledgePoint: importance 用于节点排序
        run_write("CREATE RANGE INDEX idx_techpoint_imp IF NOT EXISTS FOR (n:TechPoint) ON (n.importance)")
        run_write("CREATE RANGE INDEX idx_knowledgepoint_imp IF NOT EXISTS FOR (n:KnowledgePoint) ON (n.importance)")

    def merge_nodes(self, label: str, rows: list[dict], version: str) -> None:
        if label not in GRAPH_LABELS or not rows:
            return
        rows = self._serialize_property_rows(rows)
        run_write(
            f"UNWIND $rows AS row "
            f"MERGE (n:{label} {{namespace:$namespace, id:row.id}}) "
            "SET n += row.properties, n.syncVersion=$version",
            {"rows": rows, "namespace": self.namespace, "version": version},
        )

    def merge_edges(self, relation: str, rows: list[dict], version: str) -> None:
        if relation not in GRAPH_RELATIONS or not rows:
            return
        rows = self._serialize_property_rows(rows)
        run_write(
            "UNWIND $rows AS row "
            "MATCH (a {namespace:$namespace, id:row.source}) "
            "MATCH (b {namespace:$namespace, id:row.target}) "
            f"MERGE (a)-[r:{relation} {{namespace:$namespace}}]->(b) "
            "SET r += row.properties, r.syncVersion=$version",
            {"rows": rows, "namespace": self.namespace, "version": version},
        )

    @staticmethod
    def _serialize_property_rows(rows: list[dict]) -> list[dict]:
        """将 Neo4j 不支持的嵌套属性编码为 JSON，同时保留普通标量数组。"""
        serialized = []
        for row in rows:
            output = dict(row)
            properties = {}
            for key, value in (row.get("properties") or {}).items():
                if isinstance(value, dict) or (
                    isinstance(value, (list, tuple))
                    and any(isinstance(item, (dict, list, tuple)) for item in value)
                ):
                    properties[key] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                elif isinstance(value, tuple):
                    properties[key] = list(value)
                else:
                    properties[key] = value
            output["properties"] = properties
            serialized.append(output)
        return serialized

    def cleanup_stale(self, version: str) -> None:
        run_write(
            "MATCH ()-[r {namespace:$namespace}]->() "
            "WHERE r.syncVersion <> $version DELETE r",
            {"namespace": self.namespace, "version": version},
        )
        run_write(
            "MATCH (n {namespace:$namespace}) WHERE n.syncVersion <> $version "
            "DETACH DELETE n",
            {"namespace": self.namespace, "version": version},
        )

    def counts(self) -> dict:
        nodes = run_read(
            "MATCH (n {namespace:$namespace}) RETURN count(n) AS count",
            {"namespace": self.namespace},
        )[0]["count"]
        edges = run_read(
            "MATCH ()-[r {namespace:$namespace}]->() RETURN count(r) AS count",
            {"namespace": self.namespace},
        )[0]["count"]
        return {"nodes": nodes, "edges": edges}

    def query_nodes(
        self, *, keyword: str | None = None, stack: str | None = None,
        level: str | None = None, node_type: str | None = None, limit: int = 1000,
        include_auxiliary: bool = False,
    ) -> list[dict]:
        return run_read(
            "MATCH (n {namespace:$namespace}) "
            "WHERE ($keyword IS NULL OR toLower(coalesce(n.name,'')) CONTAINS toLower($keyword) "
            "OR toLower(coalesce(n.description,'')) CONTAINS toLower($keyword) "
            "OR toLower(coalesce(n.parent_skill,'')) CONTAINS toLower($keyword) "
            "OR toLower(coalesce(n.parent_tech_point,'')) CONTAINS toLower($keyword)) "
            "AND ($stack IS NULL OR n.stack=$stack) "
            "AND ($level IS NULL OR n.level=$level) "
            "AND ($node_type IS NULL OR $node_type IN labels(n)) "
            "AND n.id IS NOT NULL "
            "AND any(label IN labels(n) WHERE label IN $allowed_labels) "
            "AND ($include_auxiliary OR NOT "
            "('SourceDocument' IN labels(n) OR 'GraphSnapshot' IN labels(n))) "
            "RETURN n.id AS id, "
            "head([label IN labels(n) WHERE label IN $allowed_labels]) AS type, "
            "properties(n) AS properties "
            "ORDER BY n.frequency DESC, n.name LIMIT $limit",
            {
                "namespace": self.namespace, "keyword": keyword, "stack": stack,
                "level": level, "node_type": node_type, "limit": limit,
                "include_auxiliary": include_auxiliary,
                "allowed_labels": sorted(GRAPH_LABELS),
            },
        )

    def search_nodes(
        self, *, query: str, node_type: str | None = None,
        stack: str | None = None, level: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Search indexed graph nodes and retain a safe compatibility fallback."""
        normalized_query = query.strip()
        if not normalized_query or _LUCENE_SPECIAL.search(normalized_query):
            return self.query_nodes(
                keyword=normalized_query, stack=stack, level=level,
                node_type=node_type, limit=limit, include_auxiliary=True,
            )

        # Quoting preserves the former CONTAINS semantics for multi-word names.
        fulltext_query = f'"{normalized_query}"'
        try:
            return run_read(
                "CALL db.index.fulltext.queryNodes('graph_name_search', $query) "
                "YIELD node, score "
                "WHERE node.namespace = $namespace "
                "AND ($stack IS NULL OR node.stack=$stack) "
                "AND ($level IS NULL OR node.level=$level) "
                "AND ($node_type IS NULL OR $node_type IN labels(node)) "
                "AND node.id IS NOT NULL "
                "AND any(label IN labels(node) WHERE label IN $allowed_labels) "
                "RETURN node.id AS id, "
                "head([label IN labels(node) WHERE label IN $allowed_labels]) AS type, "
                "properties(node) AS properties, score "
                "ORDER BY score DESC, coalesce(node.frequency, 0) DESC, node.name "
                "LIMIT $limit",
                {
                    "namespace": self.namespace, "query": fulltext_query,
                    "stack": stack, "level": level,
                    "node_type": node_type, "limit": limit,
                    "allowed_labels": sorted(GRAPH_LABELS),
                },
            )
        except Exception as exc:  # Neo4j index may not exist/be online during startup.
            logger.warning(
                "graph fulltext search unavailable; falling back to property search: %s",
                exc,
            )
            return self.query_nodes(
                keyword=normalized_query, stack=stack, level=level,
                node_type=node_type, limit=limit, include_auxiliary=True,
            )

    def query_edges(self, node_ids: list[str]) -> list[dict]:
        if not node_ids:
            return []
        return run_read(
            "MATCH (a {namespace:$namespace})-[r {namespace:$namespace}]->"
            "(b {namespace:$namespace}) "
            "WHERE a.id IN $ids AND b.id IN $ids "
            "RETURN a.id AS source, b.id AS target, type(r) AS relation, "
            "properties(r) AS properties",
            {"namespace": self.namespace, "ids": node_ids},
        )

    def query_overview_jobs(
        self, *, offset: int, page_size: int, keyword: str | None = None,
        stack: str | None = None, level: str | None = None,
    ) -> list[dict]:
        """Page deterministic L1 seeds; L2/L3 context is fetched in one follow-up query."""
        return run_read(
            "MATCH (job:Job {namespace:$namespace}) "
            "OPTIONAL MATCH (job)-[:REQUIRES_AREA {namespace:$namespace}]->(area:SkillArea) "
            "OPTIONAL MATCH (area)-[:CONTAINS {namespace:$namespace}]->(skill:TechStack) "
            "WITH job, collect(DISTINCT area.name) AS area_names, "
            "collect(DISTINCT skill.name) AS skill_names "
            "WHERE ($keyword IS NULL OR toLower(coalesce(job.name,'')) CONTAINS toLower($keyword) "
            "OR any(name IN area_names WHERE toLower(coalesce(name,'')) CONTAINS toLower($keyword)) "
            "OR any(name IN skill_names WHERE toLower(coalesce(name,'')) CONTAINS toLower($keyword))) "
            "AND ($stack IS NULL OR job.stack=$stack) "
            "AND ($level IS NULL OR job.level=$level) "
            "RETURN job.id AS id, 'Job' AS type, properties(job) AS properties, "
            "size(area_names) AS relation_count "
            "ORDER BY relation_count DESC, coalesce(job.frequency,0) DESC, job.name, job.id "
            "SKIP $offset LIMIT $limit",
            {
                "namespace": self.namespace, "offset": offset,
                "limit": page_size + 1, "keyword": keyword,
                "stack": stack, "level": level,
            },
        )

    def query_overview_context(
        self, job_ids: list[str], max_layer: int,
    ) -> tuple[list[dict], list[dict]]:
        if not job_ids:
            return [], []
        rows = run_read(
            "MATCH (job:Job {namespace:$namespace}) WHERE job.id IN $job_ids "
            "OPTIONAL MATCH (job)-[r1:REQUIRES_AREA {namespace:$namespace}]->(area:SkillArea) "
            "OPTIONAL MATCH (area)-[r2:CONTAINS {namespace:$namespace}]->(skill:TechStack) "
            "WHERE $max_layer < 3 OR skill IS NULL OR job.id IN coalesce(r2.jobIds, []) "
            "RETURN job.id AS job_id, properties(job) AS job_properties, "
            "area.id AS area_id, properties(area) AS area_properties, "
            "skill.id AS skill_id, properties(skill) AS skill_properties, "
            "CASE WHEN r1 IS NULL THEN NULL ELSE properties(r1) END AS r1_properties, "
            "CASE WHEN r2 IS NULL THEN NULL ELSE properties(r2) END AS r2_properties",
            {"namespace": self.namespace, "job_ids": job_ids, "max_layer": max_layer},
        )
        nodes: dict[str, dict] = {}
        edges: dict[tuple[str, str, str], dict] = {}
        for row in rows:
            nodes[row["job_id"]] = {
                "id": row["job_id"], "type": "Job", "properties": row["job_properties"]
            }
            if max_layer >= 2 and row.get("area_id"):
                nodes[row["area_id"]] = {
                    "id": row["area_id"], "type": "SkillArea", "properties": row["area_properties"]
                }
                edges[(row["job_id"], row["area_id"], "REQUIRES_AREA")] = {
                    "source": row["job_id"], "target": row["area_id"],
                    "relation": "REQUIRES_AREA", "properties": row.get("r1_properties") or {},
                }
            if max_layer >= 3 and row.get("skill_id") and row.get("area_id"):
                props = dict(row["skill_properties"] or {})
                props["has_deep_nodes"] = True
                nodes[row["skill_id"]] = {
                    "id": row["skill_id"], "type": "TechStack", "properties": props
                }
                edges[(row["area_id"], row["skill_id"], "CONTAINS")] = {
                    "source": row["area_id"], "target": row["skill_id"],
                    "relation": "CONTAINS", "properties": row.get("r2_properties") or {},
                }
        return list(nodes.values()), list(edges.values())

    def query_neighbors(
        self, *, node_id: str, offset: int, page_size: int, max_layer: int,
    ) -> tuple[list[dict], list[dict]]:
        allowed = ["Job", "SkillArea", "TechStack"]
        if max_layer >= 4:
            allowed.append("TechPoint")
        if max_layer >= 5:
            allowed.append("KnowledgePoint")
        rows = run_read(
            "MATCH (root {namespace:$namespace,id:$node_id}) "
            "MATCH (root)-[r]-(neighbor {namespace:$namespace}) "
            "WHERE any(label IN labels(neighbor) WHERE label IN $allowed_labels) "
            "WITH root, neighbor, r ORDER BY coalesce(neighbor.frequency,0) DESC, neighbor.name, neighbor.id "
            "SKIP $offset LIMIT $limit "
            "RETURN root.id AS root_id, "
            "head([label IN labels(root) WHERE label IN $allowed_labels]) AS root_type, "
            "properties(root) AS root_properties, neighbor.id AS neighbor_id, "
            "head([label IN labels(neighbor) WHERE label IN $allowed_labels]) AS neighbor_type, "
            "properties(neighbor) AS neighbor_properties, startNode(r).id AS source, "
            "endNode(r).id AS target, type(r) AS relation, properties(r) AS edge_properties",
            {
                "namespace": self.namespace, "node_id": node_id,
                "allowed_labels": allowed, "offset": offset, "limit": page_size + 1,
            },
        )
        if not rows:
            return [], []
        nodes = [{
            "id": rows[0]["root_id"], "type": rows[0]["root_type"],
            "properties": rows[0]["root_properties"],
        }]
        edges = []
        for row in rows:
            nodes.append({
                "id": row["neighbor_id"], "type": row["neighbor_type"],
                "properties": row["neighbor_properties"],
            })
            edges.append({
                "source": row["source"], "target": row["target"],
                "relation": row["relation"], "properties": row["edge_properties"],
            })
        return nodes, edges

    def expand(self, node_id: str, depth: int, limit: int) -> tuple[list[dict], list[dict]]:
        rows = run_read(
            f"MATCH p=(root {{namespace:$namespace, id:$node_id}})"
            f"-[:REQUIRES_AREA|CONTAINS|REFINES_TO|HAS_KNOWLEDGE|RELATED_TO|PREREQUISITE*0..{depth}]-(n) "
            "WHERE all(x IN nodes(p) WHERE x.namespace=$namespace) "
            "WITH p LIMIT $limit "
            "UNWIND nodes(p) AS node "
            "WITH collect(DISTINCT node) AS nodes, collect(DISTINCT p) AS paths "
            "UNWIND paths AS path UNWIND relationships(path) AS rel "
            "RETURN [n IN nodes | {id:n.id,type:labels(n)[0],properties:properties(n)}] AS nodes, "
            "collect(DISTINCT {source:startNode(rel).id,target:endNode(rel).id,"
            "relation:type(rel),properties:properties(rel)}) AS edges",
            {"namespace": self.namespace, "node_id": node_id, "limit": limit},
        )
        if not rows:
            return [], []
        return rows[0]["nodes"], rows[0]["edges"]

    def path(self, from_id: str, to_id: str, max_depth: int) -> tuple[list[dict], list[dict]]:
        rows = run_read(
            f"MATCH p=shortestPath((a {{namespace:$namespace,id:$from_id}})"
            f"-[:REQUIRES_AREA|CONTAINS|REFINES_TO|HAS_KNOWLEDGE|RELATED_TO|PREREQUISITE*..{max_depth}]-(b "
            "{namespace:$namespace,id:$to_id})) "
            "RETURN [n IN nodes(p) | {id:n.id,type:labels(n)[0],properties:properties(n)}] AS nodes, "
            "[r IN relationships(p) | {source:startNode(r).id,target:endNode(r).id,"
            "relation:type(r),properties:properties(r)}] AS edges",
            {"namespace": self.namespace, "from_id": from_id, "to_id": to_id},
        )
        if not rows:
            return [], []
        return rows[0]["nodes"], rows[0]["edges"]

    def job_tree(self, job_id: str, depth: int) -> tuple[list[dict], list[dict]]:
        root = run_read(
            "MATCH (job:Job {namespace:$namespace,id:$job_id}) "
            "RETURN job.id AS id, labels(job)[0] AS type, properties(job) AS properties",
            {"namespace": self.namespace, "job_id": job_id},
        )
        if not root:
            return [], []
        nodes = root
        edges: list[dict] = []
        area_rows = run_read(
            "MATCH (job:Job {namespace:$namespace,id:$job_id})"
            "-[r:REQUIRES_AREA {namespace:$namespace}]->(area:SkillArea) "
            "RETURN area.id AS id, labels(area)[0] AS type, properties(area) AS properties, "
            "job.id AS source, area.id AS target, type(r) AS relation, properties(r) AS edge_properties",
            {"namespace": self.namespace, "job_id": job_id},
        )
        nodes.extend({
            "id": row["id"], "type": row["type"], "properties": row["properties"]
        } for row in area_rows)
        edges.extend({
            "source": row["source"], "target": row["target"],
            "relation": row["relation"], "properties": row["edge_properties"],
        } for row in area_rows)
        if depth >= 2:
            skill_rows = run_read(
                "MATCH (job:Job {namespace:$namespace,id:$job_id})"
                "-[:REQUIRES_AREA {namespace:$namespace}]->(area:SkillArea)"
                "-[r:CONTAINS {namespace:$namespace}]->(skill:TechStack) "
                "WHERE job.id IN r.jobIds "
                "RETURN skill.id AS id, labels(skill)[0] AS type, properties(skill) AS properties, "
                "area.id AS source, skill.id AS target, type(r) AS relation, properties(r) AS edge_properties",
                {"namespace": self.namespace, "job_id": job_id},
            )
            nodes.extend({
                "id": row["id"], "type": row["type"], "properties": row["properties"]
            } for row in skill_rows)
            edges.extend({
                "source": row["source"], "target": row["target"],
                "relation": row["relation"], "properties": row["edge_properties"],
            } for row in skill_rows)
            if depth >= 3:
                skill_ids = list({row["id"] for row in skill_rows})
                if skill_ids:
                    deep_nodes, deep_edges = self._deep_tree(skill_ids, depth - 2)
                    nodes.extend(deep_nodes)
                    edges.extend(deep_edges)
        nodes = list({row["id"]: row for row in nodes}.values())
        edges = list({
            (row["source"], row["target"], row["relation"]): row for row in edges
        }.values())
        return nodes, edges

    def _deep_tree(self, skill_ids: list[str], depth: int) -> tuple[list[dict], list[dict]]:
        rows = run_read(
            f"MATCH p=(skill:TechStack)-[*1..{depth}]->(leaf) "
            "WHERE skill.namespace=$namespace AND skill.id IN $skill_ids "
            "AND all(r IN relationships(p) WHERE type(r) IN $relation_types) "
            "RETURN [n IN nodes(p)[1..] | {id:n.id,type:labels(n)[0],properties:properties(n)}] AS nodes, "
            "[r IN relationships(p) | {source:startNode(r).id,target:endNode(r).id,"
            "relation:type(r),properties:properties(r)}] AS edges",
            {
                "namespace": self.namespace,
                "skill_ids": skill_ids,
                "relation_types": ["REFINES_TO", "HAS_KNOWLEDGE", "PREREQUISITE"],
            },
        )
        nodes, edges = [], []
        for row in rows:
            nodes.extend(row["nodes"])
            edges.extend(row["edges"])
        return nodes, edges
