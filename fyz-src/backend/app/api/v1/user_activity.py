"""用户收藏与浏览足迹 API。"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.user_activity import (
    FavoriteBatchDeleteRequest,
    FavoriteNoteUpdate,
    FavoriteResponse,
    FavoriteToggleRequest,
    FavoriteToggleResponse,
    HistoryCreateRequest,
    HistoryInsightsResponse,
    HistoryResponse,
)
from app.services.user_activity_service import UserActivityService

router = APIRouter(tags=["用户行为"])


@router.get("/favorites", response_model=ApiResponse[list[FavoriteResponse]])
async def list_favorites(
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse(
        data=await UserActivityService(db).list_favorites(principal.user_id)
    )


@router.post("/favorites", response_model=ApiResponse[FavoriteToggleResponse])
async def toggle_favorite(
    payload: FavoriteToggleRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active = await UserActivityService(db).toggle_favorite(
        user_id=principal.user_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
    )
    return ApiResponse(
        message="已收藏" if active else "已取消收藏",
        data=FavoriteToggleResponse(active=active),
    )


@router.post("/favorites/batch-delete", response_model=ApiResponse[dict])
async def remove_favorites(
    payload: FavoriteBatchDeleteRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await UserActivityService(db).remove_favorites(
        principal.user_id,
        payload.ids,
    )
    return ApiResponse(message="收藏已删除", data={"deleted": deleted})


@router.put("/favorites/{favorite_id}/note", response_model=ApiResponse[dict])
async def update_favorite_note(
    favorite_id: int,
    payload: FavoriteNoteUpdate,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await UserActivityService(db).update_favorite_note(
        principal.user_id,
        favorite_id,
        payload.note,
    )
    return ApiResponse(message="收藏备注已保存", data={"id": favorite_id})


@router.get("/history", response_model=ApiResponse[list[HistoryResponse]])
async def list_history(
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse(
        data=await UserActivityService(db).list_history(principal.user_id)
    )


@router.post("/history", response_model=ApiResponse[HistoryResponse])
async def record_history(
    payload: HistoryCreateRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse(
        message="浏览足迹已记录",
        data=await UserActivityService(db).record_history(principal.user_id, payload),
    )


@router.get(
    "/history/insights",
    response_model=ApiResponse[HistoryInsightsResponse],
)
async def history_insights(
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse(
        data=await UserActivityService(db).history_insights(principal.user_id)
    )


@router.delete("/history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_history(
    history_id: int,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await UserActivityService(db).remove_history(principal.user_id, history_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await UserActivityService(db).clear_history(principal.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
