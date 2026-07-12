"""
岗位相关 Schema —— 岗位、技能、技能变化。
"""
from pydantic import BaseModel, Field


class SkillSchema(BaseModel):
    """技能"""
    id: str | None = None
    name: str
    level: str = "required"  # required / preferred / advanced
    category: str = ""


class SkillChangeSchema(BaseModel):
    """技能变化记录"""
    id: str | None = None
    skill_name: str
    change_type: str  # added / removed / modified
    date: str = ""
    description: str = ""
    source: str = ""


class JobPositionResponse(BaseModel):
    """岗位详情响应"""
    id: int
    name: str
    category: str  # new / existing
    aliases: list[str] = []
    summary: str = ""
    responsibilities: list[str] = []
    required_skills: list[SkillSchema] = []
    preferred_skills: list[SkillSchema] = []
    industry_scenarios: list[str] = []
    tech_stack: list[str] = []
    career_level: str = "mid"
    salary_range: str | None = None
    skill_changes: list[SkillChangeSchema] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class JobPositionListQuery(BaseModel):
    """岗位列表查询参数"""
    category: str | None = None  # new / existing
    keyword: str | None = None
    tech_stack: str | None = None
    page: int = 1
    page_size: int = 20


# ===== 图谱数据 Schema =====
class GraphNodeSchema(BaseModel):
    """知识图谱节点"""
    id: str
    label: str
    type: str  # root / position / domain_branch / skillset_branch / module / knowledge
    layer: int  # 1-5
    root_id: str | None = None


class GraphEdgeSchema(BaseModel):
    """知识图谱边"""
    source: str
    target: str
    relation: str  # derives / applies_to / composes / contains / includes / cross_ref
    weight: int = 5


class GraphResponse(BaseModel):
    """图谱数据响应"""
    nodes: list[GraphNodeSchema] = []
    edges: list[GraphEdgeSchema] = []
