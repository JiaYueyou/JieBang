"""系统管理 — 管理后台 API"""

import logging

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.auth import TokenPrincipal
from app.schemas.common import ApiResponse
from app.schemas.data_quality import DataQualityDecisionRequest, DataQualityList, RawJobQualityItem
from app.services.crawler_service import CrawlerService
from app.services.crawler_runtime import get_crawler_service
from app.services.data_quality_service import DataQualityService
from app.models import DataSource, PipelineRun
from app.services.pipeline_service import PipelineService, start_pipeline_run
from app.services.pipeline_status_cache import (
    get_cached_pipeline_status,
    publish_pipeline_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["系统管理"],
    dependencies=[Depends(require_admin)],
)


class PipelineRunRequest(BaseModel):
    source_ids: list[int] | None = Field(default=None, max_length=20)


class CrawlerAutomationRequest(BaseModel):
    enabled: bool = True
    source_ids: list[int] = Field(default_factory=list, max_length=20)
    schedule_type: Literal["interval", "daily", "weekly"] = "interval"
    interval_minutes: int = Field(default=60, ge=15, le=10080)
    run_time: str = Field(default="02:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    weekdays: list[int] = Field(default_factory=lambda: [0, 2, 4], max_length=7)
    max_records: int = Field(default=100, ge=1, le=2000)
    max_pages: int = Field(default=5, ge=1, le=100)
    retry_count: int = Field(default=2, ge=0, le=5)
    retry_delay_minutes: int = Field(default=10, ge=1, le=1440)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("weekdays 必须在 0 到 6 之间")
        return sorted(set(value))

# 单例服务实例
@router.get("/overview", response_model=ApiResponse)
async def get_overview(
    service: CrawlerService = Depends(get_crawler_service),
    db: AsyncSession = Depends(get_db),
):
    """获取系统管理总览数据（含爬虫状态、系统指标等）"""
    try:
        data = await service.get_overview(db)
        source_rows = list((await db.execute(
            select(DataSource).where(DataSource.source_type.like("crawler:%"))
        )).scalars())
        source_by_spider = {
            int((row.crawl_config or {}).get("spider_id")): row
            for row in source_rows
            if str((row.crawl_config or {}).get("spider_id", "")).isdigit()
        }
        for crawler in data.get("crawlers", []):
            row = source_by_spider.get(int(crawler["id"]))
            if row is None:
                continue
            crawler["enabled"] = row.enabled
            crawler["schedule"] = row.schedule_expression or "仅手动"
            crawler["nextRun"] = row.next_run_at.isoformat() if row.next_run_at else "仅手动"
            crawler["lastRunAt"] = row.last_run_at.isoformat() if row.last_run_at else None
            crawler["consecutiveFailures"] = row.consecutive_failures
        pipeline = PipelineService(db)
        runs = await pipeline.list_runs(limit=5)
        data["pipelineRuns"] = [pipeline.response(row) for row in runs]
        data["currentPipelineRun"] = next(
            (pipeline.response(row) for row in runs if row.status in {"queued", "running"}),
            None,
        )
        return ApiResponse(data=data)
    except Exception as e:
        logger.exception("获取系统总览失败")
        return ApiResponse(code=500, message=f"获取系统总览失败: {e}")


@router.get("/resources", response_model=ApiResponse)
async def get_resources(
    service: CrawlerService = Depends(get_crawler_service),
):
    """获取轻量级宿主机资源快照，供管理端短周期轮询。"""
    return ApiResponse(data=service.get_resources_snapshot())


@router.get("/data-sources/automation", response_model=ApiResponse)
async def get_crawler_automation(db: AsyncSession = Depends(get_db)):
    data = await PipelineService(db).get_automation_config()
    if data.get("next_run_at"):
        data["next_run_at"] = data["next_run_at"].isoformat()
    return ApiResponse(data=data)


@router.put("/data-sources/automation", response_model=ApiResponse)
async def save_crawler_automation(
    payload: CrawlerAutomationRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.schedule_type == "weekly" and not payload.weekdays:
        raise HTTPException(status_code=400, detail="按周执行时至少选择一天")
    try:
        data = await PipelineService(db).save_automation_config(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if data.get("next_run_at"):
        data["next_run_at"] = data["next_run_at"].isoformat()
    return ApiResponse(message="自动爬取配置已保存", data=data)


@router.put("/data-sources/{spider_id}", response_model=ApiResponse)
async def toggle_crawler(
    spider_id: int,
    service: CrawlerService = Depends(get_crawler_service),
    db: AsyncSession = Depends(get_db),
):
    """切换爬虫启停状态"""
    try:
        row = await db.scalar(
            select(DataSource).where(DataSource.source_type == f"crawler:{spider_id}")
        )
        if row is not None:
            result = service.set_crawler_enabled(spider_id, not row.enabled)
            row.enabled = result["enabled"]
            await db.commit()
        else:
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


@router.post("/pipeline/runs", response_model=ApiResponse)
async def create_pipeline_run(
    payload: PipelineRunRequest,
    principal: TokenPrincipal = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = PipelineService(db)
    try:
        run = await service.create_run(
            trigger="manual",
            source_ids=payload.source_ids,
            requested_by=principal.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    start_pipeline_run(run.id)
    return ApiResponse(message="端到端更新流水线已启动", data=service.response(run))


@router.get("/pipeline/runs", response_model=ApiResponse)
async def list_pipeline_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = PipelineService(db)
    rows = await service.list_runs(limit=limit)
    return ApiResponse(data=[service.response(row) for row in rows])


@router.get("/pipeline/runs/{run_id}", response_model=ApiResponse)
async def get_pipeline_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    cached = await get_cached_pipeline_status(run_id)
    if cached is not None:
        return ApiResponse(data=cached)
    run = await db.get(PipelineRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="流水线运行记录不存在")
    data = PipelineService.response(run)
    await publish_pipeline_status(data)
    return ApiResponse(data=data)


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
