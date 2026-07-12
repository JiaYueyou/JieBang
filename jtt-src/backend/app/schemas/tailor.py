"""
简历优化相关 Schema —— AI 优化建议、短语润色。
"""
from pydantic import BaseModel, Field


class TailorSuggestionsQuery(BaseModel):
    """获取优化建议（path 参数从 URL 获取）"""
    pass


class AcceptSuggestionRequest(BaseModel):
    """接受单条建议"""
    resume_id: int
    suggestion_id: str


class ApplyAllRequest(BaseModel):
    """批量应用建议"""
    resume_id: int
    suggestion_ids: list[str] = Field(..., min_length=1)


class OptimizePhraseRequest(BaseModel):
    """短语润色请求"""
    text: str = Field(..., min_length=1, max_length=500, description="需要润色的文本")
    style: str = Field(default="professional", description="润色风格: professional/concise/match/impact")


class OptimizePhraseResponse(BaseModel):
    """短语润色响应"""
    suggestions: list[str] = []


class SaveAsNewRequest(BaseModel):
    """保存为新的简历版本"""
    resume_id: int
    suggestion_ids: list[str]


class SaveAsNewResponse(BaseModel):
    """保存结果"""
    new_resume_id: int


class SuggestionResponse(BaseModel):
    """单条优化建议响应"""
    id: str
    section: str
    field: str
    original: str
    suggested: str
    reason: str
    change_type: str = "small"
    accepted: bool = False
    verified: bool = True
    warning: str | None = None
