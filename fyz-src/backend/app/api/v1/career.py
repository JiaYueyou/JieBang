from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.career import CareerAnalysisRequest, CareerAnalysisResponse, ResumeExtractionResponse
from app.schemas.common import ApiResponse
from app.services.career_service import CareerService

router = APIRouter(prefix="/career", tags=["转岗规划"])


@router.post("/resume-extractions", response_model=ApiResponse[ResumeExtractionResponse])
async def extract_resume(
    file: UploadFile = File(...),
    _principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse(data=await CareerService(db).extract_resume(file))


@router.post("/analyses", response_model=ApiResponse[CareerAnalysisResponse])
async def analyze_career(
    payload: CareerAnalysisRequest,
    principal: TokenPrincipal = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse(data=await CareerService(db).analyze(payload, user_id=principal.user_id))
