"""
岗位相关 API —— 岗位列表（来自爬虫数据）、详情、知识图谱。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.repositories.raw_job_repository import RawJobRepository
from app.services.position_service import PositionService
from app.schemas.position import (
    JobPositionResponse, JobPositionDetailResponse, GraphResponse,
)
from app.schemas.common import ApiResponse, PaginatedData
from app.core.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/positions", tags=["岗位"])


# ---------------- 辅助函数 ----------------


def _stack_to_category(stack: str | None) -> str:
    """将 standard_job.stack 映射为岗位分类：ai→新兴, 其余→既有"""
    if stack == "ai":
        return "new"
    return "existing"


def _parse_keywords_to_skills(keywords_str: str) -> list[dict]:
    """将逗号分隔的关键词转为技能列表（最多 8 个）"""
    names = [k.strip() for k in (keywords_str or "").split(",") if k.strip()]
    return [
        {"id": f"sk-{i}", "name": name, "level": "required", "category": ""}
        for i, name in enumerate(names[:8])
    ]


def _row_to_response(row: dict) -> dict:
    """将 raw_job_record 行转为 JobPositionResponse 格式"""
    jd = row.get("jd_text") or ""
    summary = jd[:150] + "..." if len(jd) > 150 else jd
    return {
        "id": f"raw-{row['id']}",
        "name": row.get("standardized_title") or "",
        "category": _stack_to_category(row.get("stack")),
        "summary": summary,
        "company": row.get("company") or "",
        "city": row.get("city") or "",
        "salary_range": row.get("salary_text") or "",
        "experience": row.get("experience_text") or "",
        "education": row.get("education_text") or "",
        "required_skills": _parse_keywords_to_skills(row.get("keywords") or ""),
        "aliases": [], "responsibilities": [], "preferred_skills": [],
        "industry_scenarios": [], "tech_stack": [],
        "career_level": "mid", "skill_changes": None,
        "created_at": None, "updated_at": None,
    }


def _row_to_detail(row: dict) -> dict:
    """将 raw_job_record 行转为 JobPositionDetailResponse 格式"""
    base = _row_to_response(row)
    base.update({
        "original_title": row.get("title") or "",
        "jd_text": row.get("jd_text") or "",
        "responsibilities_text": row.get("responsibilities") or "",
        "requirements_text": row.get("requirements") or "",
        "posted_at": row.get("posted_at_text") or "",
        "stack": row.get("stack") or "",
        "std_job_name": row.get("std_job_name") or "",
    })
    return base


# ---------------- 端点 ----------------


@router.get("", response_model=ApiResponse[PaginatedData[JobPositionResponse]])
async def list_positions(
    category: str | None = Query(None, description="岗位类型: new(新兴) / existing(既有)"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """分页查询岗位列表（数据来源：raw_job_record）"""
    repo = RawJobRepository(db)
    rows, total = await repo.list_jobs(
        category=category, keyword=keyword, page=page, page_size=page_size,
    )
    items = [_row_to_response(r) for r in rows]
    return ApiResponse(data={
        "list": items, "total": total, "page": page, "page_size": page_size,
    })


@router.get("/graph", response_model=ApiResponse[GraphResponse])
async def get_knowledge_graph(
    root_tech: str | None = Query(None, description="根技术筛选，如 Java"),
    db: AsyncSession = Depends(get_db),
):
    """获取知识图谱数据（五级节点 + 边）"""
    service = PositionService(db)
    data = await service.get_graph_data(root_tech)
    return ApiResponse(data=data)


@router.get("/{position_id}", response_model=ApiResponse[JobPositionDetailResponse])
async def get_position_detail(
    position_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取岗位详情（数据来源：raw_job_record）。
    ID 格式为 "raw-{数字}"，如 "raw-123"。
    """
    if not position_id.startswith("raw-"):
        raise ResourceNotFoundError("岗位不存在")
    try:
        raw_id = int(position_id[4:])
    except ValueError:
        raise ResourceNotFoundError("岗位不存在")

    repo = RawJobRepository(db)
    row = await repo.get_by_id(raw_id)
    if not row:
        raise ResourceNotFoundError("岗位不存在")
    return ApiResponse(data=_row_to_detail(row))
