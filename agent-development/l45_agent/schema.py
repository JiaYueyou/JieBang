"""L4-L5 智能体：数据模型定义"""

from pydantic import BaseModel, Field


class SkillEvidence(BaseModel):
    """技能的来源证据"""
    source_doc_id: int
    source_platform: str = Field(max_length=50)
    evidence_text: str = Field(max_length=2000)


class L4TechPoint(BaseModel):
    """L4 技术点"""
    name: str = Field(description="技术点名称，如'索引设计与优化'")
    detail: str = Field(description="技术点详细说明")
    confidence: float = Field(ge=0, le=1, description="置信度")
    knowledge_points: list["L5KnowledgePoint"] = Field(default_factory=list)


class L5KnowledgePoint(BaseModel):
    """L5 知识点"""
    name: str = Field(description="知识点名称")
    description: str = Field(description="知识点说明")
    difficulty: str = Field(description="难度: easy/medium/hard")
    confidence: float = Field(ge=0, le=1, description="置信度")


class AgentInput(BaseModel):
    """智能体输入"""
    skill_name: str = Field(max_length=100)
    skill_area: str = Field(max_length=100)
    job_directions: list[str] = Field(default_factory=list, max_length=20)
    evidence: list[SkillEvidence] = Field(min_length=1, max_length=20)


class AgentOutput(BaseModel):
    """智能体输出"""
    skill_name: str
    tech_points: list[L4TechPoint] = Field(default_factory=list)


class VerifiedResult(BaseModel):
    """验证通过的结果"""
    skill_name: str
    tech_points: list[L4TechPoint]
    passed: bool
    reason: str = ""
