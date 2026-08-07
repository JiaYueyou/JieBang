"""
匹配相关 Schema —— 人岗匹配、差距分析、优化建议。
"""
from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    """单次匹配请求"""
    resume_id: int
    position_id: int


class BatchMatchRequest(BaseModel):
    """批量匹配请求（一份简历 vs 多个岗位）"""
    resume_id: int
    position_ids: list[int] = Field(..., min_length=1)


class MatchDimensionSchema(BaseModel):
    """匹配维度"""
    name: str       # 技能匹配 / 经验匹配 / 学历匹配 / 综合素质
    score: int      # 0-100
    weight: float   # 权重
    details: str = ""


class GapAnalysisSchema(BaseModel):
    """差距分析"""
    missing_skills: list[dict] = []   # 完全缺失的技能
    weak_skills: list[dict] = []      # 薄弱的技能
    match_skills: list[dict] = []     # 已匹配的技能


class SuggestionSchema(BaseModel):
    """优化建议"""
    id: str
    section: str          # skills / workExperience / education / selfEvaluation
    field: str
    original: str
    suggested: str
    reason: str
    change_type: str = "small"  # small / large
    accepted: bool = False
    verified: bool = True       # 是否通过图谱校验
    warning: str | None = None  # 校验警告


class MatchResultResponse(BaseModel):
    """匹配结果响应"""
    id: int
    resume_id: int
    position_id: str  # Neo4j 如 "job:113"，MySQL 如 "position:5"
    position_name: str = ""
    resume_name: str = ""
    total_score: int = 0
    dimensions: list[MatchDimensionSchema] = []
    gap_analysis: GapAnalysisSchema = GapAnalysisSchema()
    suggestions: list[SuggestionSchema] = []
    match_date: str | None = None


class AutoMatchResponse(BaseModel):
    """自动匹配响应（Agent 3）"""
    results: list[MatchResultResponse] = []
    total_matched: int = 0
    education_filtered: int = 0
    score_filtered: int = 0
    data_source: str = ""
