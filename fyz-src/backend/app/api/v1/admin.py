"""系统管理 — 管理后台 API"""

import logging

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.data_quality import DataQualityDecisionRequest, DataQualityList, RawJobQualityItem
from app.services.crawler_service import CrawlerService
from app.services.data_quality_service import DataQualityService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["系统管理"],
    dependencies=[Depends(require_admin)],
)

# 单例服务实例
_crawler_service: CrawlerService | None = None


def get_crawler_service() -> CrawlerService:
    global _crawler_service
    if _crawler_service is None:
        _crawler_service = CrawlerService()
    return _crawler_service


@router.get("/overview", response_model=ApiResponse)
async def get_overview(
    service: CrawlerService = Depends(get_crawler_service),
    db: AsyncSession = Depends(get_db),
):
    """获取系统管理总览数据（含爬虫状态、系统指标等）"""
    try:
        data = await service.get_overview(db)
        return ApiResponse(data=data)
    except Exception as e:
        logger.exception("获取系统总览失败")
        return ApiResponse(code=500, message=f"获取系统总览失败: {e}")


@router.put("/data-sources/{spider_id}", response_model=ApiResponse)
async def toggle_crawler(
    spider_id: int,
    service: CrawlerService = Depends(get_crawler_service),
):
    """切换爬虫启停状态"""
    try:
        result = service.toggle_crawler(spider_id)
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("切换爬虫状态失败")
        return ApiResponse(code=500, message=f"操作失败: {e}")


@router.post("/data-sources/{spider_id}/run", response_model=ApiResponse)
async def run_crawler(
    spider_id: int,
    service: CrawlerService = Depends(get_crawler_service),
):
    """启动爬虫执行"""
    try:
        result = service.run_spider(spider_id)
        return ApiResponse(data=result)
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("启动爬虫失败")
        return ApiResponse(code=500, message=f"启动失败: {e}")


@router.get("/data-sources/{spider_id}/status", response_model=ApiResponse)
async def spider_status(
    spider_id: int,
    service: CrawlerService = Depends(get_crawler_service),
):
    """获取单个爬虫状态"""
    try:
        result = service.get_spider_status(spider_id)
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/data-sources/{spider_id}/poll", response_model=ApiResponse)
async def poll_spider(
    spider_id: int,
    service: CrawlerService = Depends(get_crawler_service),
):
    """轮询爬虫完成状态（完成后返回结果）"""
    try:
        result = service.poll_spider(spider_id)
        return ApiResponse(data={"done": result is not None, "result": result})
    except Exception as e:
        logger.exception("轮询爬虫状态失败")
        return ApiResponse(code=500, message=f"轮询失败: {e}")


@router.get(
    "/data-quality/records",
    response_model=ApiResponse[DataQualityList],
)
async def list_data_quality_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source: str | None = Query(default=None, max_length=100),
    quality_status: str | None = Query(default=None, pattern="^(accepted|warning|rejected|pending)$"),
    quality_flag: str | None = Query(default=None, max_length=100),
    near_duplicate_group_id: str | None = Query(default=None, max_length=40),
    posted_from: datetime | None = Query(default=None),
    posted_to: datetime | None = Query(default=None),
    excluded: bool | None = Query(default=None),
    _principal: TokenPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DataQualityList]:
    data, meta = await DataQualityService(db).list_records(
        page=page,
        page_size=page_size,
        source=source,
        quality_status=quality_status,
        quality_flag=quality_flag,
        near_duplicate_group_id=near_duplicate_group_id,
        posted_from=posted_from,
        posted_to=posted_to,
        excluded=excluded,
    )
    return ApiResponse(data=data, meta=meta)


@router.patch(
    "/data-quality/records/{record_id}",
    response_model=ApiResponse[RawJobQualityItem],
)
async def decide_data_quality_record(
    record_id: int,
    payload: DataQualityDecisionRequest,
    principal: TokenPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RawJobQualityItem]:
    data = await DataQualityService(db).decide(
        record_id,
        action=payload.action,
        reason=payload.reason,
        user_id=principal.user_id,
    )
    return ApiResponse(
        message="记录已排除" if payload.action == "exclude" else "记录已恢复",
        data=data,
    )
