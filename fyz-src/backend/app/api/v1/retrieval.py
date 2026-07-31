"""Traceable evidence retrieval and rebuildable index administration."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthorizationError
from app.core.security import get_current_user
from app.models import User
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.retrieval import (
    EvidenceChunkResponse,
    RetrievalIndexResponse,
    RetrievalRebuildRequest,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieval", tags=["证据检索"])


async def require_admin(
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenPrincipal:
    user = await db.get(User, principal.user_id)
    if not user or user.role != "admin":
        raise AuthorizationError("检索索引管理仅限管理员")
    return principal


@router.post(
    "/search",
    response_model=ApiResponse[RetrievalSearchResponse],
)
async def search_evidence(
    payload: RetrievalSearchRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RetrievalSearchResponse]:
    data = await RetrievalService(db).search(
        payload,
        user_id=principal.user_id,
    )
    return ApiResponse(data=data)


@router.post(
    "/indexes/rebuild",
    response_model=ApiResponse[RetrievalIndexResponse],
)
async def rebuild_index(
    payload: RetrievalRebuildRequest,
    principal: TokenPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RetrievalIndexResponse]:
    data = await RetrievalService(db).rebuild_index(
        created_by=principal.user_id,
        backend=payload.backend,
    )
    return ApiResponse(message="检索索引重建完成", data=data)


@router.get(
    "/indexes",
    response_model=ApiResponse[list[RetrievalIndexResponse]],
)
async def list_indexes(
    _principal: TokenPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RetrievalIndexResponse]]:
    return ApiResponse(data=await RetrievalService(db).list_indexes())


@router.get(
    "/evidence/{evidence_id}",
    response_model=ApiResponse[EvidenceChunkResponse],
)
async def get_evidence(
    evidence_id: str,
    _principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EvidenceChunkResponse]:
    return ApiResponse(
        data=await RetrievalService(db).get_evidence(evidence_id)
    )
