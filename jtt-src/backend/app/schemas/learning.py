"""
学习路径相关 Schema —— 学习路径 CRUD、AI 助手对话。
"""
from pydantic import BaseModel, Field


class LearningResourceSchema(BaseModel):
    """学习资源"""
    id: str
    title: str
    type: str      # course / book / article / project / video
    url: str = ""
    platform: str = ""


class LearningStepSchema(BaseModel):
    """学习步骤"""
    id: str
    order: int
    title: str
    description: str = ""
    duration: str = ""
    resources: list[LearningResourceSchema] = []
    completed: bool = False


class LearningPathCreate(BaseModel):
    """创建学习路径，可选附带 AI 生成的步骤"""
    name: str = Field(..., min_length=1, max_length=100)
    position_id: int = 0  # 对应 learning_path.position_id（INT NOT NULL），空填 0
    steps: list[LearningStepSchema] = []
    position_name: str = ""


class LearningPathUpdate(BaseModel):
    """更新学习路径"""
    name: str | None = None
    steps: list[LearningStepSchema] | None = None


class LearningPathResponse(BaseModel):
    """学习路径响应"""
    id: int
    name: str
    position_id: int = 0  # 与 DB 列类型一致（INT）
    position_name: str = ""
    steps: list[LearningStepSchema] = []
    total_duration: str = ""
    created_at: str | None = None
    updated_at: str | None = None


# ===== AI 学习助手 Schema =====
class ChatRequest(BaseModel):
    """AI 助手对话请求"""
    message: str = Field(..., min_length=1, description="用户输入的问题")
    context: dict | None = None  # {"resume_id": 1, "target_position_id": 2}
    history: list[dict] = []     # [{"role": "user", "content": "..."}, ...]


class ChatResponse(BaseModel):
    """AI 助手对话响应"""
    reply: str                                          # Markdown 格式回答
    related_concepts: list[dict] = []                   # 关联的图谱概念
    suggested_resources: list[LearningResourceSchema] = []
    follow_up_questions: list[str] = []                 # 建议追问


class GeneratePathRequest(BaseModel):
    """生成学习路径请求 —— 传入缺失技能列表，由 LLM 直接规划"""
    position_name: str
    missing_skills: list[str] = []     # 缺失的技能
    matched_skills: list[str] = []     # 已匹配的技能（可选，提供已有基础上下文）
    resume_id: int | None = None       # 可选，传入则读取简历已有技能做个性化


class RecommendResourcesRequest(BaseModel):
    """推荐学习资源请求"""
    skill_names: list[str] = Field(..., min_length=1, description="需要学习的技能列表")


class RecommendResourcesResponse(BaseModel):
    """推荐资源响应"""
    skills: dict[str, list[LearningResourceSchema]]  # 技能名 → 推荐资源列表


class QuizRequest(BaseModel):
    """学习测试请求"""
    path_id: int
    step_ids: list[str] = []        # 需要测试的步骤，空则为全部已完成的步骤
    question_count: int = 5


class QuizQuestion(BaseModel):
    """测试题"""
    id: str
    type: str = "choice"    # choice / short_answer
    question: str
    options: list[str] = []  # 选择题的选项
    correct_answer: int | str = 0  # 选择题为选项索引，简答题为参考答案
    explanation: str = ""


class QuizResponse(BaseModel):
    """测试题响应"""
    questions: list[QuizQuestion] = []
