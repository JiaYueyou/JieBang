"""Periodic warm-up for the most expensive shared FYZ read models."""

from __future__ import annotations

import asyncio
import logging

from app.core.cache import close_cache
from app.core.celery_app import celery_app
from app.core.database import async_session, engine
from app.schemas.analysis import AnalysisOverview, TrendWindow
from app.schemas.graph import GraphSubgraph
from app.services.analysis_service import AnalysisService
from app.services.dashboard_service import DashboardService
from app.services.graph_service import GraphService
from app.services.query_cache import (
    ANALYSIS_CACHE_NAMESPACE,
    ANALYSIS_OVERVIEW_TTL_SECONDS,
    GRAPH_CACHE_NAMESPACE,
    GRAPH_QUERY_TTL_SECONDS,
    cached_model_query,
)

logger = logging.getLogger(__name__)


async def _warm_popular_queries() -> dict[str, str]:
    # A solo Celery worker creates a new asyncio loop for each task. Discard a
    # client left by a legacy/failed task before opening cache connections.
    await close_cache()
    results: dict[str, str] = {}
    async with async_session() as db:
        try:
            await DashboardService(db)._hot_jobs(force_refresh=True)
            results["hot_jobs"] = "warmed"
        except Exception as exc:
            logger.warning("hot-jobs cache warm-up failed: %s", exc)
            results["hot_jobs"] = "failed"

        analysis_params = {
            "window": TrendWindow.months_3.value,
            "keyword": None,
            "city": None,
            "emerging_page": 1,
            "emerging_page_size": 10,
            "new_job_page": 1,
            "new_job_page_size": 10,
            "new_job_keyword": None,
        }
        try:
            service = AnalysisService(db)
            await cached_model_query(
                generation_namespace=ANALYSIS_CACHE_NAMESPACE,
                operation="overview",
                params=analysis_params,
                ttl_seconds=ANALYSIS_OVERVIEW_TTL_SECONDS,
                model_type=AnalysisOverview,
                loader=lambda: service.overview(
                    window=TrendWindow.months_3,
                    keyword=None,
                    city=None,
                    emerging_page=1,
                    emerging_page_size=10,
                    new_job_page=1,
                    new_job_page_size=10,
                    new_job_keyword=None,
                ),
                force_refresh=True,
            )
            results["analysis_overview"] = "warmed"
        except Exception as exc:
            logger.warning("analysis overview cache warm-up failed: %s", exc)
            results["analysis_overview"] = "failed"

        graph_params = {
            "cursor": None,
            "page_size": 24,
            "max_layer": 3,
            "stack": None,
            "level": None,
            "keyword": None,
        }
        try:
            service = GraphService(db)
            await cached_model_query(
                generation_namespace=GRAPH_CACHE_NAMESPACE,
                operation="overview",
                params=graph_params,
                ttl_seconds=GRAPH_QUERY_TTL_SECONDS,
                model_type=GraphSubgraph,
                loader=lambda: service.overview(**graph_params),
                force_refresh=True,
            )
            results["graph_overview"] = "warmed"
        except Exception as exc:
            logger.warning("graph overview cache warm-up failed: %s", exc)
            results["graph_overview"] = "failed"
    return results


@celery_app.task(name="cache.warm_popular_queries", ignore_result=True)
def warm_popular_queries() -> dict[str, str]:
    async def run() -> dict[str, str]:
        try:
            return await _warm_popular_queries()
        finally:
            await close_cache()
            await engine.dispose()

    return asyncio.run(run())
