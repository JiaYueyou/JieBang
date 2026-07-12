from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.matching import MatchExplanationResponse, ResumeCreatedResponse, TalentResponse
from app.services.matching_service import MatchingService

router = APIRouter(tags=["简历匹配"])


@router.get("/matching/", response_model=ApiResponse[dict])
async def matching_module_home(_principal: TokenPrincipal = Depends(get_current_user)):
    """Compatibility entrypoint retained for existing module health consumers."""
    return ApiResponse(data={"message": "匹配诊断 — 已接入简历匹配服务"})


@router.post("/resumes", response_model=ApiResponse[ResumeCreatedResponse])
async def upload_resume(
    file: UploadFile = File(...), name: str | None = Form(default=None),
    current_position: str | None = Form(default=None), experience: str | None = Form(default=None),
    education: str | None = Form(default=None), department: str | None = Form(default=None),
    company: str | None = Form(default=None), location: str | None = Form(default=None),
    principal: TokenPrincipal = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await MatchingService(db).create_resume(
        content=await file.read(), filename=file.filename or "resume.txt", content_type=file.content_type,
        user_id=principal.user_id, name=name, current_position=current_position,
        experience=experience, education=education, department=department, company=company, location=location,
    )
    return ApiResponse(data=data)


@router.get("/resumes/{resume_id}/file")
async def download_resume(resume_id: int, principal: TokenPrincipal = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    filename, content_type, path = await MatchingService(db).get_resume_file(resume_id, principal.user_id)
    return FileResponse(path=path, filename=filename, media_type=content_type or "application/octet-stream")


@router.get("/talents", response_model=ApiResponse[list[TalentResponse]])
async def list_talents(principal: TokenPrincipal = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ApiResponse(data=await MatchingService(db).list_talents(principal.user_id))


@router.get("/talents/{resume_id}", response_model=ApiResponse[TalentResponse])
async def get_talent(resume_id: int, principal: TokenPrincipal = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ApiResponse(data=await MatchingService(db).get_talent(resume_id, principal.user_id))


@router.post("/matches/{match_id}/explanation", response_model=ApiResponse[MatchExplanationResponse])
async def explain_match(match_id: int, principal: TokenPrincipal = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ApiResponse(data=await MatchingService(db).explain(match_id, principal.user_id))
