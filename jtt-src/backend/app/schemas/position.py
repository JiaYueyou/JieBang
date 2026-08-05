"""
岗位相关 Schema —— 岗位（来自爬虫数据）、技能、图谱数据。
"""
from pydantic import BaseModel, Field


class SkillSchema(BaseModel):
    """技能"""
    id: str | None = None
    name: str
    level: str = "required"  # required / preferred / advanced
    category: str = ""


class SkillChangeSchema(BaseModel):
    """技能变化记录（爬虫数据暂不使用，保留兼容）"""
    id: str | None = None
    skill_name: str = ""
    change_type: str = "modified"  # added / removed / modified
    date: str = ""
    description: str = ""
    source: str = ""


class JobPositionResponse(BaseModel):
    """岗位列表项响应（来自 raw_job_record）"""
    id: str
    name: str
    category: str  # new=新兴(ai), existing=既有(backend/data/devops)
    summary: str = ""
    # 核心字段
    company: str = ""
    city: str = ""
    salary_range: str = ""
    experience: str = ""
    education: str = ""
    # 技能（从 keywords 解析）
    required_skills: list[SkillSchema] = []
    # 兼容旧接口的字段
    aliases: list[str] = []
    responsibilities: list[str] = []
    preferred_skills: list[SkillSchema] = []
    industry_scenarios: list[str] = []
    tech_stack: list[str] = []
    career_level: str = "mid"
    skill_changes: list[SkillChangeSchema] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class JobPositionDetailResponse(JobPositionResponse):
    """岗位详情响应（含 JD 全文等完整字段）"""
    # 原始标题
    original_title: str = ""
    # 完整 JD
    jd_text: str = ""
    # 职责和要求
    responsibilities_text: str = ""
    requirements_text: str = ""
    # 发布日期
    posted_at: str = ""
    # 技术栈标签
    stack: str = ""  # ai / backend / data / devops
    # 关联的标准岗位名
    std_job_name: str = ""


class JobPositionListQuery(BaseModel):
    """岗位列表查询参数"""
    category: str | None = None  # new / existing
    keyword: str | None = None
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
