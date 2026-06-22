"""MySQL 图谱审计访问与参数化 Neo4j 访问。"""

from __future__ import annotations

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
        for label in GRAPH_LABELS:
            run_write(
                f"CREATE CONSTRAINT {label.lower()}_jiebang_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE (n.namespace, n.id) IS UNIQUE"
            )

    def merge_nodes(self, label: str, rows: list[dict], version: str) -> None:
        if label not in GRAPH_LABELS or not rows:
            return
        run_write(
            f"UNWIND $rows AS row "
            f"MERGE (n:{label} {{namespace:$namespace, id:row.id}}) "
            "SET n += row.properties, n.syncVersion=$version",
            {"rows": rows, "namespace": self.namespace, "version": version},
        )

    def merge_edges(self, relation: str, rows: list[dict], version: str) -> None:
        if relation not in GRAPH_RELATIONS or not rows:
            return
        run_write(
            "UNWIND $rows AS row "
            "MATCH (a {namespace:$namespace, id:row.source}) "
            "MATCH (b {namespace:$namespace, id:row.target}) "
            f"MERGE (a)-[r:{relation} {{namespace:$namespace}}]->(b) "
            "SET r += row.properties, r.syncVersion=$version",
            {"rows": rows, "namespace": self.namespace, "version": version},
        )

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
            "WHERE ($keyword IS NULL OR toLower(coalesce(n.name,'')) CONTAINS toLower($keyword)) "
            "AND ($stack IS NULL OR n.stack=$stack) "
            "AND ($level IS NULL OR n.level=$level) "
            "AND ($node_type IS NULL OR $node_type IN labels(n)) "
            "AND ($include_auxiliary OR NOT "
            "('SourceDocument' IN labels(n) OR 'GraphSnapshot' IN labels(n))) "
            "RETURN n.id AS id, labels(n)[0] AS type, properties(n) AS properties "
            "ORDER BY n.frequency DESC, n.name LIMIT $limit",
            {
                "namespace": self.namespace, "keyword": keyword, "stack": stack,
                "level": level, "node_type": node_type, "limit": limit,
                "include_auxiliary": include_auxiliary,
            },
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
