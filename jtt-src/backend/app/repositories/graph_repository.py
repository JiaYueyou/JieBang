"""Neo4j 图谱查询与写入 —— 参数化 Cypher 访问。"""
from app.core.neo4j import run_read, run_write

GRAPH_LABELS = {
    "Job", "SkillArea", "TechStack", "TechPoint",
    "KnowledgePoint", "SourceDocument", "GraphSnapshot",
}
GRAPH_RELATIONS = {
    "REQUIRES_AREA", "CONTAINS", "REFINES_TO", "HAS_KNOWLEDGE",
    "RELATED_TO", "PREREQUISITE", "SUPPORTS", "HAS_SNAPSHOT",
}


class Neo4jGraphRepository:
    """Neo4j 图谱查询与写入（namespace="jiebang"，与 fyz 共享数据）"""
    namespace = "jiebang"

    # ===== 写入方法 =====

    def ensure_schema(self) -> None:
        """创建 namespace+id 唯一约束（如果不存在）"""
        for label in GRAPH_LABELS:
            run_write(
                f"CREATE CONSTRAINT {label.lower()}_jiebang_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE (n.namespace, n.id) IS UNIQUE"
            )

    def merge_nodes(self, label: str, rows: list[dict], version: str = "") -> None:
        """批量 UPSERT 节点"""
        if label not in GRAPH_LABELS or not rows:
            return
        run_write(
            f"UNWIND $rows AS row "
            f"MERGE (n:{label} {{namespace:$namespace, id:row.id}}) "
            "SET n += row.properties, n.syncVersion=$version",
            {"rows": rows, "namespace": self.namespace, "version": version},
        )

    def merge_edges(self, relation: str, rows: list[dict], version: str = "") -> None:
        """批量 UPSERT 边"""
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

    # ===== 查询方法 =====

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

    # ===== 匹配诊断用：Job + 技能树查询 =====

    def query_jobs_for_matching(self) -> list[dict]:
        """查询所有 Job 节点及其关联技能名称列表，供匹配引擎使用"""
        rows = run_read(
            "MATCH (job:Job {namespace:$namespace}) "
            "OPTIONAL MATCH (job)-[:REQUIRES_AREA {namespace:$namespace}]->(area:SkillArea) "
            "OPTIONAL MATCH (area)-[:CONTAINS {namespace:$namespace}]->(skill:TechStack) "
            "OPTIONAL MATCH (skill)-[:REFINES_TO {namespace:$namespace}]->(tp:TechPoint) "
            "OPTIONAL MATCH (tp)-[:HAS_KNOWLEDGE {namespace:$namespace}]->(kp:KnowledgePoint) "
            "RETURN "
            "job.id AS id, job.name AS name, job.description AS description, "
            "job.stack AS stack, job.level AS level, "
            "collect(DISTINCT area.name) AS areas, "
            "collect(DISTINCT skill.name) AS skills, "
            "collect(DISTINCT tp.name) AS tech_points, "
            "collect(DISTINCT kp.name) AS knowledge_points "
            "ORDER BY job.name",
            {"namespace": self.namespace},
        )
        return [
            {
                "id": row["id"], "name": row["name"] or "",
                "description": row.get("description") or "",
                "stack": row.get("stack") or "",
                "level": row.get("level") or "",
                "areas": [s for s in (row.get("areas") or []) if s],
                "skills": [s for s in (row.get("skills") or []) if s],
                "tech_points": [s for s in (row.get("tech_points") or []) if s],
                "knowledge_points": [s for s in (row.get("knowledge_points") or []) if s],
            }
            for row in rows
        ]

    def query_job_skills(self, job_id: str) -> dict | None:
        """查询单个 Job 节点的完整技能树"""
        rows = run_read(
            "MATCH (job:Job {namespace:$namespace, id:$job_id}) "
            "OPTIONAL MATCH (job)-[:REQUIRES_AREA {namespace:$namespace}]->(area:SkillArea) "
            "OPTIONAL MATCH (area)-[:CONTAINS {namespace:$namespace}]->(skill:TechStack) "
            "OPTIONAL MATCH (skill)-[:REFINES_TO {namespace:$namespace}]->(tp:TechPoint) "
            "OPTIONAL MATCH (tp)-[:HAS_KNOWLEDGE {namespace:$namespace}]->(kp:KnowledgePoint) "
            "RETURN "
            "job.name AS name, job.description AS description, "
            "job.stack AS stack, job.level AS level, "
            "collect(DISTINCT area.name) AS areas, "
            "collect(DISTINCT skill.name) AS skills, "
            "collect(DISTINCT tp.name) AS tech_points, "
            "collect(DISTINCT kp.name) AS knowledge_points",
            {"namespace": self.namespace, "job_id": job_id},
        )
        if not rows or not rows[0].get("name"):
            return None
        row = rows[0]
        return {
            "id": job_id, "name": row["name"] or "",
            "description": row.get("description") or "",
            "stack": row.get("stack") or "",
            "level": row.get("level") or "",
            "areas": [s for s in (row.get("areas") or []) if s],
            "skills": [s for s in (row.get("skills") or []) if s],
            "tech_points": [s for s in (row.get("tech_points") or []) if s],
            "knowledge_points": [s for s in (row.get("knowledge_points") or []) if s],
        }

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
