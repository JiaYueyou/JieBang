"""
收藏 API —— 用户岗位收藏的增删查。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.favorite_repository import FavoriteRepository
from app.repositories.position_repository import PositionRepository
from app.schemas.position import JobPositionResponse
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/favorites", tags=["收藏"])


@router.get("", response_model=ApiResponse[list[JobPositionResponse]])
async def list_favorites(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户收藏的岗位列表"""
    fav_repo = FavoriteRepository(db)
    pos_repo = PositionRepository(db)
    favs = await fav_repo.list_by_user(user["user_id"])
    positions = []
    for fav in favs:
        pos = await pos_repo.get_by_id(fav.position_id)
        if pos:
            from app.services.position_service import PositionService
            ps = PositionService(db)
            positions.append(ps._position_to_dict(pos))
    return ApiResponse(data=positions)


@router.post("/{position_id}", response_model=ApiResponse)
async def add_favorite(
    position_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加收藏"""
    repo = FavoriteRepository(db)
    existing = await repo.get(user["user_id"], position_id)
    if existing:
        return ApiResponse(message="已收藏")
    await repo.add(user["user_id"], position_id)
    await db.commit()
    return ApiResponse(message="已收藏")


@router.delete("/{position_id}", response_model=ApiResponse)
async def remove_favorite(
    position_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消收藏"""
    repo = FavoriteRepository(db)
    fav = await repo.get(user["user_id"], position_id)
    if not fav:
        return ApiResponse(message="未收藏")
    await repo.remove(fav)
    await db.commit()
    return ApiResponse(message="已取消收藏")


@router.get("/check/{position_id}", response_model=ApiResponse[bool])
async def check_favorite(
    position_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检查是否已收藏某岗位"""
    repo = FavoriteRepository(db)
    is_fav = await repo.is_favorited(user["user_id"], position_id)
    return ApiResponse(data=is_fav)
