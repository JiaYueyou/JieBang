"""
收藏 API —— 用户多类型收藏的增删查（岗位/学习资料/错题/AI知识点）。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.favorite_repository import FavoriteRepository
from app.schemas.favorite import FavoriteCreate, FavoriteResponse
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/favorites", tags=["收藏"])


def _to_response(fav) -> dict:
    """将 Favorite 模型转为响应字典"""
    return {
        "id": fav.id,
        "item_type": fav.item_type,
        "item_id": fav.item_id,
        "title": fav.title,
        "summary": fav.summary,
        "metadata": fav.item_data,
        "tags": fav.tags,
        "created_at": str(fav.created_at) if fav.created_at else None,
    }


@router.get("", response_model=ApiResponse[list[FavoriteResponse]])
async def list_favorites(
    type: str | None = Query(None, description="按类型筛选: position/learning_resource/quiz_error/knowledge_point"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户收藏列表，可按类型筛选"""
    repo = FavoriteRepository(db)
    favs = await repo.list_by_user(user["user_id"], type)
    return ApiResponse(data=[_to_response(f) for f in favs])


@router.post("", response_model=ApiResponse[FavoriteResponse])
async def add_favorite(
    req: FavoriteCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加收藏"""
    repo = FavoriteRepository(db)
    existing = await repo.get_by_item(user["user_id"], req.item_type, req.item_id)
    if existing:
        return ApiResponse(code=200, message="已收藏", data=_to_response(existing))
    fav = await repo.add(
        user_id=user["user_id"],
        item_type=req.item_type, item_id=req.item_id,
        title=req.title, summary=req.summary,
        item_data=req.metadata, tags=req.tags,
    )
    await db.commit()
    return ApiResponse(message="已收藏", data=_to_response(fav))


@router.delete("/{fav_id}", response_model=ApiResponse)
async def remove_favorite(
    fav_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消收藏"""
    repo = FavoriteRepository(db)
    fav = await repo.get_by_id(fav_id)
    if not fav:
        return ApiResponse(code=404, message="收藏不存在")
    await repo.remove(fav)
    await db.commit()
    return ApiResponse(message="已取消收藏")


@router.get("/check", response_model=ApiResponse[bool])
async def check_favorite(
    item_type: str = Query(..., description="类型"),
    item_id: str = Query(..., description="资源ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检查是否已收藏某项"""
    repo = FavoriteRepository(db)
    is_fav = await repo.is_favorited(user["user_id"], item_type, item_id)
    return ApiResponse(data=is_fav)
