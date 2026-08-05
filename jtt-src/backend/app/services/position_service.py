"""
岗位服务 —— 岗位列表查询、详情、知识图谱数据构建。
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundError
from app.repositories.position_repository import PositionRepository
from app.core.neo4j import run_read


class PositionService:
    """岗位业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.repo = PositionRepository(db)
        self.db = db

    async def list_positions(self, params: dict) -> dict:
        """分页查询岗位列表"""
        positions, total = await self.repo.list_positions(
            category=params.get("category"),
            keyword=params.get("keyword"),
            tech_stack=params.get("tech_stack"),
            page=params.get("page", 1),
            page_size=params.get("page_size", 20),
        )
        # 批量加载所有岗位的关联数据
        pos_ids = [p.id for p in positions]
        skills_map = await self.repo.get_skills_for_positions(pos_ids)
        changes_map = await self.repo.get_skill_changes_for_positions(pos_ids)

        return {
            "list": [self._position_to_dict(p, skills_map.get(p.id, []), changes_map.get(p.id, []))
                     for p in positions],
            "total": total,
            "page": params.get("page", 1),
            "page_size": params.get("page_size", 20),
        }

    async def get_detail(self, position_id: int) -> dict:
        """获取岗位详情"""
        position = await self.repo.get_by_id(position_id)
        if not position:
            raise ResourceNotFoundError("岗位不存在")
        skills_map = await self.repo.get_skills_for_positions([position_id])
        changes_map = await self.repo.get_skill_changes_for_positions([position_id])
        return self._position_to_dict(position, skills_map.get(position_id, []), changes_map.get(position_id, []))

    async def get_graph_data(self, root_tech: str | None = None) -> dict:
        """知识图谱数据，优先从 Neo4j 查询，否则返回示例数据"""
        try:
            nodes = run_read(
                "MATCH (n) WHERE ($root IS NULL OR n.rootId = $root) "
                "RETURN n.id AS id, n.label AS label, n.type AS type, n.layer AS layer, n.rootId AS root_id",
                {"root": root_tech},
            )
            edges = run_read(
                "MATCH (a)-[r]->(b) WHERE ($root IS NULL OR a.rootId = $root) "
                "RETURN a.id AS source, b.id AS target, type(r) AS relation, r.weight AS weight",
                {"root": root_tech},
            )
            if nodes:
                return {"nodes": nodes, "edges": edges}
        except Exception:
            pass
        return {"nodes": self._sample_nodes(root_tech), "edges": self._sample_edges(root_tech)}

    def _position_to_dict(self, p, skills: list | None = None, changes: list | None = None) -> dict:
        """将 JobPosition 模型转为 API 返回格式"""
        if skills is None:
            skills = []
        required = [sk for sk in skills if sk.get("kind") == "required"]
        preferred = [sk for sk in skills if sk.get("kind") == "preferred"]
        if changes is None:
            changes = []

        return {
            "id": p.id, "name": p.name, "category": p.category,
            "aliases": p.aliases or [], "summary": p.summary or "",
            "responsibilities": p.responsibilities or [],
            "required_skills": [{"id": str(s["id"]), "name": s["name"], "level": s["level"], "category": s["category"]}
                                for s in required],
            "preferred_skills": [{"id": str(s["id"]), "name": s["name"], "level": s["level"], "category": s["category"]}
                                 for s in preferred],
            "industry_scenarios": p.industry_scenarios or [],
            "tech_stack": p.tech_stack or [],
            "career_level": p.career_level or "mid",
            "salary_range": p.salary_range,
            "skill_changes": [{"id": str(sc["id"]), "skill_name": sc["skill_name"],
                               "change_type": sc["change_type"], "date": sc["change_date"],
                               "description": sc["description"], "source": sc["source"]}
                              for sc in changes],
            "created_at": str(p.created_at) if p.created_at else None,
            "updated_at": str(p.updated_at) if p.updated_at else None,
        }

    def _sample_nodes(self, root_tech: str | None = None) -> list[dict]:
        """示例图谱节点数据（五级结构，Java 子树）"""
        all_nodes = [
            # Level 1: 根技术
            {"id": "root-java", "label": "Java", "type": "root", "layer": 1, "root_id": None},
            # Level 2: 岗位
            {"id": "pos-java-dev", "label": "Java开发工程师", "type": "position", "layer": 2, "root_id": "root-java"},
            {"id": "pos-java-arch", "label": "Java架构师", "type": "position", "layer": 2, "root_id": "root-java"},
            # Level 3: 应用领域 + 技能集合
            {"id": "domain-ecom", "label": "电商", "type": "domain_branch", "layer": 3, "root_id": "root-java"},
            {"id": "domain-fin", "label": "金融", "type": "domain_branch", "layer": 3, "root_id": "root-java"},
            {"id": "skillset-backend", "label": "后端开发技能", "type": "skillset_branch", "layer": 3, "root_id": "root-java"},
            {"id": "skillset-arch", "label": "系统架构技能", "type": "skillset_branch", "layer": 3, "root_id": "root-java"},
            # Level 4: 能力模块
            {"id": "mod-micro", "label": "微服务架构", "type": "module", "layer": 4, "root_id": "root-java"},
            {"id": "mod-db", "label": "数据库设计", "type": "module", "layer": 4, "root_id": "root-java"},
            {"id": "mod-dist", "label": "分布式系统", "type": "module", "layer": 4, "root_id": "root-java"},
            # Level 5: 知识点
            {"id": "kp-springboot", "label": "Spring Boot", "type": "knowledge", "layer": 5, "root_id": "root-java"},
            {"id": "kp-mysql", "label": "MySQL优化", "type": "knowledge", "layer": 5, "root_id": "root-java"},
            {"id": "kp-redis", "label": "Redis", "type": "knowledge", "layer": 5, "root_id": "root-java"},
            {"id": "kp-kafka", "label": "Kafka", "type": "knowledge", "layer": 5, "root_id": "root-java"},
        ]
        if root_tech:
            return [n for n in all_nodes if n["root_id"] == root_tech or n["id"] == root_tech]
        return all_nodes

    def _sample_edges(self, root_tech: str | None = None) -> list[dict]:
        """示例图谱边数据"""
        return [
            # 层级边
            {"source": "root-java", "target": "pos-java-dev", "relation": "derives", "weight": 5},
            {"source": "root-java", "target": "pos-java-arch", "relation": "derives", "weight": 4},
            {"source": "pos-java-dev", "target": "domain-ecom", "relation": "applies_to", "weight": 4},
            {"source": "pos-java-dev", "target": "domain-fin", "relation": "applies_to", "weight": 3},
            {"source": "pos-java-dev", "target": "skillset-backend", "relation": "composes", "weight": 5},
            {"source": "pos-java-arch", "target": "skillset-arch", "relation": "composes", "weight": 5},
            {"source": "skillset-backend", "target": "mod-micro", "relation": "contains", "weight": 5},
            {"source": "skillset-backend", "target": "mod-db", "relation": "contains", "weight": 5},
            {"source": "skillset-arch", "target": "mod-dist", "relation": "contains", "weight": 4},
            {"source": "mod-micro", "target": "kp-springboot", "relation": "includes", "weight": 5},
            {"source": "mod-db", "target": "kp-mysql", "relation": "includes", "weight": 5},
            {"source": "mod-dist", "target": "kp-kafka", "relation": "includes", "weight": 4},
            # 交叉边（多对多关系）
            {"source": "kp-redis", "target": "mod-dist", "relation": "cross_ref", "weight": 3},
            {"source": "kp-kafka", "target": "mod-micro", "relation": "cross_ref", "weight": 3},
        ]
