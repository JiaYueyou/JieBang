"""
学习路径 API —— 学习路径 CRUD + AI 学习助手（Agent 2: 学习助手智能体）。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.learning_service import LearningService
from app.schemas.learning import (
    LearningPathCreate, LearningPathUpdate, LearningPathResponse,
    ChatRequest, ChatResponse,
    GeneratePathRequest,
    RecommendResourcesRequest, RecommendResourcesResponse,
    QuizRequest, QuizResponse,
)
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/learning", tags=["学习"])


def get_learning_service(db: AsyncSession = Depends(get_db)) -> LearningService:
    """依赖注入：创建学习服务实例"""
    return LearningService(db)


# ===== 学习路径 CRUD =====

@router.get("/paths", response_model=ApiResponse[list[LearningPathResponse]])
async def list_paths(
    user: dict = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
):
    """获取用户的所有学习路径"""
    paths = await service.list_paths(user["user_id"])
    return ApiResponse(data=paths)


@router.get("/paths/{path_id}", response_model=ApiResponse[LearningPathResponse])
async def get_path(
    path_id: int,
    service: LearningService = Depends(get_learning_service),
):
    """获取学习路径详情"""
    path = await service.get_path(path_id)
    return ApiResponse(data=path)


@router.post("/paths", response_model=ApiResponse[LearningPathResponse])
async def create_path(
    req: LearningPathCreate,
    user: dict = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
):
    """创建学习路径"""
    path = await service.create_path(user["user_id"], req.model_dump())
    return ApiResponse(data=path)


@router.put("/paths/{path_id}", response_model=ApiResponse[LearningPathResponse])
async def update_path(
    path_id: int,
    req: LearningPathUpdate,
    service: LearningService = Depends(get_learning_service),
):
    """更新学习路径（名称、步骤、完成状态）"""
    path = await service.update_path(path_id, req.model_dump(exclude_none=True))
    return ApiResponse(data=path)


@router.delete("/paths/{path_id}", response_model=ApiResponse)
async def delete_path(
    path_id: int,
    service: LearningService = Depends(get_learning_service),
):
    """删除学习路径"""
    await service.delete_path(path_id)
    return ApiResponse(message="学习路径已删除")


# ===== AI 学习助手 =====

@router.post("/assistant/chat", response_model=ApiResponse[ChatResponse])
async def assistant_chat(
    req: ChatRequest,
    service: LearningService = Depends(get_learning_service),
):
    """
    AI 学习助手对话 —— 结合知识图谱上下文回答职业/技术问题。
    支持：概念解释、学习建议、转行咨询等。
    """
    result = await service.chat(req.message, req.context, req.history)
    return ApiResponse(data=result)


@router.post("/assistant/generate-path", response_model=ApiResponse[LearningPathResponse])
async def generate_path(
    req: GeneratePathRequest,
    user: dict = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
):
    """AI 自动生成个性化学习路径 —— 基于目标岗位和用户简历"""
    plan = await service.generate_path(req.position_id, req.resume_id)
    # 将生成的路径保存到用户的学习路径中
    path = await service.repo.create(user["user_id"], plan)
    await service.db.commit()
    return ApiResponse(data=service._path_to_dict(path))


@router.post("/assistant/recommend-resources", response_model=ApiResponse[RecommendResourcesResponse])
async def recommend_resources(
    req: RecommendResourcesRequest,
    service: LearningService = Depends(get_learning_service),
):
    """AI 推荐学习资源 —— 根据技能名称推荐视频/课程/书籍"""
    result = await service.recommend_resources(req.skill_names)
    return ApiResponse(data=result)


@router.post("/assistant/quiz", response_model=ApiResponse[QuizResponse])
async def generate_quiz(
    req: QuizRequest,
    service: LearningService = Depends(get_learning_service),
):
    """AI 生成学习测试题 —— 根据已学内容生成选择题/简答题"""
    result = await service.generate_quiz(req.path_id, req.step_ids, req.question_count)
    return ApiResponse(data=result)
