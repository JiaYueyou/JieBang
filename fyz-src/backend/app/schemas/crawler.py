"""爬虫模块 Pydantic Schema"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SpiderInfo(BaseModel):
    """爬虫（数据源）信息"""
    id: int
    name: str
    short: str
    endpoint: str
    tone: str = "brand"
    enabled: bool = True
    running: bool = False
    today: str = "0"
    success: float = 100.0
    duration: str = "—"
    progress: int = 0
    schedule: str = "每小时"
    next_run: str = "待调度"


class CrawlerPolicy(BaseModel):
    """全局采集策略"""
    concurrency: int = 4
    retries: int = 3
    interval: int = 5
    deduplicate: bool = True


class AdminOverview(BaseModel):
    """系统管理总览"""
    metrics: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    recent_tasks: list[dict[str, Any]] = []
    system_events: list[dict[str, Any]] = []
    crawlers: list[SpiderInfo] = []
    qualities: list[dict[str, Any]] = []
    crawler_policy: CrawlerPolicy = Field(default_factory=CrawlerPolicy)
    performance_cards: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []


class CrawlerRunResult(BaseModel):
    """爬虫执行结果"""
    spider_id: int
    name: str
    records_count: int
    filepath: str
    started_at: datetime
    finished_at: datetime
    elapsed: float
    errors: int
    duplicates: int


class CrawlerStatusUpdate(BaseModel):
    """爬虫启停状态"""
    enabled: bool
