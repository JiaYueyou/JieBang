"""系统管理 — 管理后台 API"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.common import ApiResponse
from app.services.crawler_service import CrawlerService

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
