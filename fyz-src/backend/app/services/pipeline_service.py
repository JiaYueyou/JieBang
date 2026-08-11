"""Persistent end-to-end crawler, ingestion, graph and trend orchestration."""

from __future__ import annotations

import asyncio
import logging
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    AUTO_PIPELINE_BASELINE_LAG_MONTHS,
    AUTO_PIPELINE_BASELINE_LOOKBACK_MONTHS,
    AUTO_PIPELINE_ENRICH_GRAPH,
    AUTO_PIPELINE_INTERVAL_MINUTES,
    AUTO_PIPELINE_SOURCE_IDS,
    AUTO_PIPELINE_SOURCE_TIMEOUT_SECONDS,
)
from app.core.database import async_session
from app.core.pipeline_lock import serialized_pipeline_run
from app.core.time import utc_isoformat, utc_now_naive
from app.models import AnalysisBaselineSnapshot, DataSource, PipelineRun
from app.schemas.analysis import TrendWindow
from app.services.analysis_service import AnalysisService
from app.services.crawler_runtime import get_crawler_service
from app.services.crawler_service import REGISTERED_SPIDERS
from app.services.graph_service import GraphService
from app.services.historical_baseline_service import HistoricalBaselineService
from app.services.import_service import ImportService
from app.services.pipeline_status_cache import publish_pipeline_status
from app.services.task_status_cache import bump_cache_generations

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def next_schedule_at(config: dict, *, after: datetime | None = None) -> datetime:
    """Return the next configured execution time as a naive UTC timestamp."""
    reference = (after or utc_now_naive()).replace(tzinfo=ZoneInfo("UTC")).astimezone(LOCAL_TZ)
    schedule_type = config.get("schedule_type", "interval")
    if schedule_type == "interval":
        return (reference + timedelta(minutes=int(config.get("interval_minutes", 60)))).astimezone(
            ZoneInfo("UTC")
        ).replace(tzinfo=None)

    hour, minute = map(int, str(config.get("run_time", "02:00")).split(":"))
    candidate = reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if schedule_type == "daily":
        if candidate <= reference:
            candidate += timedelta(days=1)
    else:
        weekdays = {int(value) for value in config.get("weekdays", [0])}
        for offset in range(8):
            value = candidate + timedelta(days=offset)
            if value.weekday() in weekdays and value > reference:
                candidate = value
                break
    return candidate.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

_pipeline_tasks: set[asyncio.Task] = set()
_scheduler_task: asyncio.Task | None = None
_shutdown_event: asyncio.Event | None = None
_pipeline_execution_lock = asyncio.Lock()


def _minus_months_first(day: date, months: int) -> date:
    value = day.year * 12 + day.month - 1 - months
    return date(value // 12, value % 12 + 1, 1)


class PipelineService:
    STAGES = (
        "collect", "validate_import", "quality_gate", "graph_publish",
        "baseline_refresh", "trend_verify",
    )

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.crawler = get_crawler_service()

    async def seed_sources(self) -> None:
        """Keep the crawler registry and persistent scheduling table aligned."""
        now = utc_now_naive()
        rows = list((await self.db.execute(select(DataSource))).scalars())
        by_type = {row.source_type: row for row in rows}
        for meta in REGISTERED_SPIDERS:
            source_type = f"crawler:{meta.id}"
            row = by_type.get(source_type)
            config = {
                "spider_id": meta.id,
                "module_name": meta.module_name,
                "portal_host": meta.endpoint,
            }
            if row is None:
                enabled = meta.id in AUTO_PIPELINE_SOURCE_IDS
                row = DataSource(
                    name=f"{meta.name} [{meta.endpoint}]",
                    source_type=source_type,
                    entry_url=f"https://{meta.endpoint}",
                    description="独立招聘门户自动采集源",
                    schedule_expression=f"interval:{AUTO_PIPELINE_INTERVAL_MINUTES}m",
                    enabled=enabled,
                    crawl_config={
                        **config,
                        "automation_enabled": enabled,
                        "schedule_type": "interval",
                        "interval_minutes": AUTO_PIPELINE_INTERVAL_MINUTES,
                        "max_records": 100,
                        "max_pages": 5,
                        "retry_count": 2,
                        "retry_delay_minutes": 10,
                        "timeout_seconds": AUTO_PIPELINE_SOURCE_TIMEOUT_SECONDS,
                    },
                    next_run_at=now + timedelta(seconds=30) if enabled else None,
                )
                self.db.add(row)
            else:
                row.crawl_config = {**config, **(row.crawl_config or {})}
                if "automation_enabled" not in row.crawl_config:
                    row.crawl_config = {
                        **row.crawl_config,
                        "automation_enabled": meta.id in AUTO_PIPELINE_SOURCE_IDS,
                        "schedule_type": "interval",
                        "interval_minutes": AUTO_PIPELINE_INTERVAL_MINUTES,
                        "max_records": 100,
                        "max_pages": 5,
                        "retry_count": 2,
                        "retry_delay_minutes": 10,
                        "timeout_seconds": AUTO_PIPELINE_SOURCE_TIMEOUT_SECONDS,
                    }
                if row.schedule_expression is None:
                    row.schedule_expression = f"interval:{AUTO_PIPELINE_INTERVAL_MINUTES}m"
                if row.enabled and row.next_run_at is None:
                    row.next_run_at = now + timedelta(seconds=30)
        registered_types = {f"crawler:{meta.id}" for meta in REGISTERED_SPIDERS}
        for row in rows:
            if row.source_type.startswith("crawler:") and row.source_type not in registered_types:
                row.enabled = False
                row.next_run_at = None
                row.crawl_config = {**(row.crawl_config or {}), "automation_enabled": False}
        await self.db.commit()

    async def get_automation_config(self) -> dict:
        await self.seed_sources()
        registered_ids = {meta.id for meta in REGISTERED_SPIDERS}
        rows = list((await self.db.execute(
            select(DataSource).where(DataSource.source_type.like("crawler:%"))
        )).scalars())
        rows = [
            row for row in rows
            if int((row.crawl_config or {}).get("spider_id", -1)) in registered_ids
        ]
        selected = [
            int(row.crawl_config["spider_id"])
            for row in rows
            if (row.crawl_config or {}).get("automation_enabled")
        ]
        sample = next(
            ((row.crawl_config or {}) for row in rows if row.crawl_config), {}
        )
        return {
            "enabled": bool(selected),
            "source_ids": sorted(selected),
            "schedule_type": sample.get("schedule_type", "interval"),
            "interval_minutes": int(sample.get("interval_minutes", 60)),
            "run_time": sample.get("run_time", "02:00"),
            "weekdays": sample.get("weekdays", [0, 2, 4]),
            "max_records": int(sample.get("max_records", 100)),
            "max_pages": int(sample.get("max_pages", 5)),
            "retry_count": int(sample.get("retry_count", 2)),
            "retry_delay_minutes": int(sample.get("retry_delay_minutes", 10)),
            "timeout_seconds": int(sample.get("timeout_seconds", AUTO_PIPELINE_SOURCE_TIMEOUT_SECONDS)),
            "next_run_at": min(
                (row.next_run_at for row in rows if row.next_run_at), default=None
            ),
        }

    async def save_automation_config(self, payload: dict) -> dict:
        await self.seed_sources()
        registered_ids = {meta.id for meta in REGISTERED_SPIDERS}
        selected = set(payload["source_ids"])
        unknown = selected - registered_ids
        if unknown:
            raise ValueError(f"未知数据源: {sorted(unknown)}")
        if payload["enabled"] and not selected:
            raise ValueError("启用自动爬取时至少选择一个数据源")
        rows = list((await self.db.execute(
            select(DataSource).where(DataSource.source_type.like("crawler:%"))
        )).scalars())
        now = utc_now_naive()
        schedule_expression = self._schedule_expression(payload)
        for row in rows:
            config = row.crawl_config or {}
            spider_id = int(config.get("spider_id", -1))
            if spider_id not in registered_ids:
                continue
            automatic = bool(payload["enabled"] and spider_id in selected)
            row.crawl_config = {**config, **payload, "automation_enabled": automatic}
            row.schedule_expression = schedule_expression if automatic else "仅手动"
            row.next_run_at = next_schedule_at(row.crawl_config, after=now) if automatic else None
        await self.db.commit()
        return await self.get_automation_config()

    @staticmethod
    def _schedule_expression(config: dict) -> str:
        schedule_type = config.get("schedule_type")
        if schedule_type == "interval":
            return f"每 {int(config['interval_minutes'])} 分钟"
        if schedule_type == "daily":
            return f"每天 {config['run_time']}"
        labels = "、".join("一二三四五六日"[int(day)] for day in config.get("weekdays", []))
        return f"每周{labels} {config['run_time']}"

    async def create_run(
        self,
        *,
        trigger: str,
        source_ids: list[int] | None,
        requested_by: int | None,
        idempotency_key: str | None = None,
        scheduled_for: datetime | None = None,
    ) -> PipelineRun:
        ids = sorted(set(source_ids or await self._enabled_spider_ids(
            due_only=trigger == "scheduled"
        )))
        registered_ids = {meta.id for meta in REGISTERED_SPIDERS}
        unknown_ids = set(ids) - registered_ids
        if unknown_ids:
            raise ValueError(f"未知数据源: {sorted(unknown_ids)}")
        if source_ids:
            disabled = list((await self.db.execute(
                select(DataSource).where(
                    DataSource.source_type.in_([f"crawler:{value}" for value in ids]),
                    DataSource.enabled.is_(False),
                )
            )).scalars())
            if disabled:
                raise ValueError("请求包含已停用的数据源")
        if not ids:
            raise ValueError("没有已启用的自动数据源")
        now = utc_now_naive()
        run = PipelineRun(
            id=str(uuid.uuid4()),
            idempotency_key=idempotency_key or f"manual:{uuid.uuid4()}",
            trigger=trigger,
            status="queued",
            stage="queued",
            progress=0,
            requested_sources=ids,
            stage_results={},
            quality_summary={},
            requested_by=requested_by,
            scheduled_for=scheduled_for or now,
            heartbeat_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.add(run)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = await self.db.scalar(
                select(PipelineRun).where(PipelineRun.idempotency_key == run.idempotency_key)
            )
            if existing is None:
                raise
            await publish_pipeline_status(self.response(existing))
            return existing
        await publish_pipeline_status(self.response(run))
        return run

    async def _enabled_spider_ids(self, *, due_only: bool = False) -> list[int]:
        conditions = [
            DataSource.enabled.is_(True),
            DataSource.source_type.like("crawler:%"),
        ]
        if due_only:
            conditions.append(DataSource.next_run_at <= utc_now_naive())
        rows = list((await self.db.execute(
            select(DataSource).where(*conditions)
        )).scalars())
        return [
            int((row.crawl_config or {}).get("spider_id"))
            for row in rows
            if str((row.crawl_config or {}).get("spider_id", "")).isdigit()
            and (not due_only or bool((row.crawl_config or {}).get("automation_enabled", False)))
        ]

    async def run(self, run_id: str) -> None:
        claimed = await self.db.execute(
            update(PipelineRun)
            .where(PipelineRun.id == run_id, PipelineRun.status == "queued")
            .values(
                status="running", stage="collect",
                started_at=utc_now_naive(), heartbeat_at=utc_now_naive(),
            )
        )
        await self.db.commit()
        if claimed.rowcount != 1:
            return
        run = await self.db.get(PipelineRun, run_id)
        await publish_pipeline_status(self.response(run))
        try:
            source_results = []
            for index, spider_id in enumerate(run.requested_sources or [], start=1):
                source_results.append(await self._run_source(run, int(spider_id)))
                run.stage_results = {
                    **(run.stage_results or {}), "sources": list(source_results)
                }
                await self._update(
                    run, "collect", min(45, 5 + int(index * 40 / len(run.requested_sources)))
                )

            importable = [item for item in source_results if item.get("import")]
            failed_sources = [item for item in source_results if item["status"] == "failed"]
            totals = self._aggregate_imports(importable)
            run.stage_results = {**(run.stage_results or {}), "sources": source_results}
            run.quality_summary = totals
            await self._update(run, "quality_gate", 58)
            if not importable:
                raise RuntimeError("所有来源均未产生可验证快照")

            downstream_failed = False
            graph_result: dict = {"status": "skipped", "reason": "no new graph facts"}
            if totals["imported"] > 0 or totals["skill_facts"] > 0:
                await self._update(run, "graph_publish", 68)
                try:
                    graph_result = await GraphService(self.db).sync(
                        mode="full",
                        enrich_top_skills=AUTO_PIPELINE_ENRICH_GRAPH,
                        auto_publish_enrichment=AUTO_PIPELINE_ENRICH_GRAPH,
                        user_id=run.requested_by,
                    )
                    graph_result["status"] = "succeeded"
                    await bump_cache_generations("graph")
                except Exception as exc:
                    await self.db.rollback()
                    run = await self.db.get(PipelineRun, run_id)
                    downstream_failed = True
                    graph_result = {
                        "status": "failed",
                        "error": f"{type(exc).__name__}: {exc}"[:1000],
                    }
            run.stage_results = {**run.stage_results, "graph_publish": graph_result}

            await self._update(run, "baseline_refresh", 85)
            try:
                baseline_result = await self._refresh_baseline(run.requested_by)
            except Exception as exc:
                await self.db.rollback()
                run = await self.db.get(PipelineRun, run_id)
                downstream_failed = True
                baseline_result = {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}"[:1000],
                }
            run.stage_results = {**run.stage_results, "baseline_refresh": baseline_result}

            await self._update(run, "trend_verify", 94)
            try:
                overview = await AnalysisService(self.db).overview(
                    window=TrendWindow.months_6,
                    keyword=None,
                    city=None,
                    emerging_page=1,
                    emerging_page_size=1,
                    new_job_page=1,
                    new_job_page_size=1,
                    new_job_keyword=None,
                )
                trend_result = {
                    "status": "succeeded",
                    "total_jobs": overview.stats.total_jobs,
                    "new_skills": overview.stats.new_skills,
                    "baseline_version": overview.baseline.version,
                }
            except Exception as exc:
                await self.db.rollback()
                run = await self.db.get(PipelineRun, run_id)
                downstream_failed = True
                if baseline_result.get("status") == "activated":
                    await self._rollback_baseline_activation(baseline_result)
                    run = await self.db.get(PipelineRun, run_id)
                    baseline_result["status"] = "rolled_back"
                    run.stage_results = {
                        **run.stage_results, "baseline_refresh": baseline_result
                    }
                trend_result = {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}"[:1000],
                }
            run.stage_results = {**run.stage_results, "trend_verify": trend_result}
            run.status = "partial" if failed_sources or downstream_failed else "succeeded"
            run.stage = "completed"
            run.progress = 100
            run.finished_at = utc_now_naive()
            run.heartbeat_at = run.finished_at
            await self.db.commit()
            await publish_pipeline_status(self.response(run))
            await bump_cache_generations("analysis", "dashboard")
        except asyncio.CancelledError:
            await self.db.rollback()
            run = await self.db.get(PipelineRun, run_id)
            if run is not None:
                run.status = "queued"
                run.stage = "interrupted"
                run.heartbeat_at = utc_now_naive()
                await self.db.commit()
                await publish_pipeline_status(self.response(run))
            raise
        except Exception as exc:
            await self.db.rollback()
            run = await self.db.get(PipelineRun, run_id)
            if run is not None:
                run.status = "failed"
                run.error_message = f"{type(exc).__name__}: {exc}"[:4000]
                run.finished_at = utc_now_naive()
                run.heartbeat_at = run.finished_at
                await self.db.commit()
                await publish_pipeline_status(self.response(run))
            logger.exception("automatic_pipeline_failed run_id=%s", run_id)

    async def _run_source(self, run: PipelineRun, spider_id: int) -> dict:
        started = utc_now_naive()
        item = {"spider_id": spider_id, "status": "running", "started_at": started.isoformat()}
        data_source = await self._source_row(spider_id)
        if data_source is None or not data_source.enabled:
            return {**item, "status": "skipped", "reason": "source_disabled"}
        try:
            self.crawler.run_spider(spider_id, data_source.crawl_config or {})
            deadline = asyncio.get_running_loop().time() + int(
                (data_source.crawl_config or {}).get(
                    "timeout_seconds", AUTO_PIPELINE_SOURCE_TIMEOUT_SECONDS
                )
            )
            result = None
            while result is None:
                if asyncio.get_running_loop().time() >= deadline:
                    self.crawler.stop_spider(spider_id)
                    raise TimeoutError("crawler source timeout")
                await asyncio.sleep(1)
                result = self.crawler.poll_spider(spider_id)
            item["crawl"] = {
                key: result.get(key)
                for key in (
                    "records_count", "filename", "output_changed", "elapsed",
                    "returncode", "error_category", "error_reason", "message",
                )
            }
            filename = result.get("filename")
            if result.get("returncode") != 0 or not filename:
                raise RuntimeError(result.get("message") or "crawler produced no snapshot")
            await self._update(run, "validate_import", run.progress)
            import_result = await ImportService(self.db).import_files([filename])
            item["import"] = import_result
            item["status"] = "succeeded"
            data_source.last_run_at = utc_now_naive()
            data_source.next_run_at = next_schedule_at(
                data_source.crawl_config or {}, after=data_source.last_run_at
            ) if (data_source.crawl_config or {}).get("automation_enabled") else None
            data_source.consecutive_failures = 0
            await self.db.commit()
        except asyncio.CancelledError:
            self.crawler.stop_spider(spider_id)
            await self.db.rollback()
            raise
        except Exception as exc:
            await self.db.rollback()
            data_source = await self._source_row(spider_id)
            if data_source is not None:
                data_source.last_run_at = utc_now_naive()
                data_source.consecutive_failures += 1
                config = data_source.crawl_config or {}
                if config.get("automation_enabled"):
                    retry_count = int(config.get("retry_count", 2))
                    if data_source.consecutive_failures <= retry_count:
                        data_source.next_run_at = data_source.last_run_at + timedelta(
                            minutes=int(config.get("retry_delay_minutes", 10))
                        )
                    else:
                        data_source.next_run_at = next_schedule_at(config, after=data_source.last_run_at)
                else:
                    data_source.next_run_at = None
                await self.db.commit()
            item["status"] = "failed"
            item["error"] = f"{type(exc).__name__}: {exc}"[:1000]
        item["finished_at"] = utc_now_naive().isoformat()
        return item

    async def _source_row(self, spider_id: int) -> DataSource | None:
        return await self.db.scalar(
            select(DataSource).where(DataSource.source_type == f"crawler:{spider_id}")
        )

    async def _update(self, run: PipelineRun, stage: str, progress: int) -> None:
        run.stage = stage
        run.progress = progress
        run.heartbeat_at = utc_now_naive()
        await self.db.commit()
        await publish_pipeline_status(self.response(run))

    @staticmethod
    def _aggregate_imports(items: list[dict]) -> dict:
        keys = (
            "total", "imported", "duplicates", "observations", "skill_facts",
            "near_duplicates", "low_quality", "time_anomalies",
        )
        return {
            key: sum(int(item["import"].get(key, 0)) for item in items)
            for key in keys
        }

    async def _refresh_baseline(self, created_by: int | None) -> dict:
        today = utc_now_naive().date()
        baseline_month = _minus_months_first(today.replace(day=1), AUTO_PIPELINE_BASELINE_LAG_MONTHS)
        period_end = baseline_month - timedelta(days=1)
        period_start = _minus_months_first(
            period_end.replace(day=1), AUTO_PIPELINE_BASELINE_LOOKBACK_MONTHS - 1
        )
        active = await self.db.scalar(
            select(AnalysisBaselineSnapshot)
            .where(AnalysisBaselineSnapshot.status == "active")
            .order_by(AnalysisBaselineSnapshot.activated_at.desc())
        )
        if active is not None and active.period_end >= period_end:
            return {"status": "skipped", "reason": "baseline_current", "version": active.version}
        version = f"rolling-{period_start:%Y%m%d}-{period_end:%Y%m%d}"
        existing = await self.db.scalar(
            select(AnalysisBaselineSnapshot).where(AnalysisBaselineSnapshot.version == version)
        )
        if existing is not None:
            return {"status": "skipped", "reason": "version_exists", "version": version}
        service = HistoricalBaselineService(self.db)
        preview = await service.build(
            version=version,
            period_start=period_start,
            period_end=period_end,
            persist=False,
        )
        if not preview.ready:
            result = await service.build(
                version=version,
                period_start=period_start,
                period_end=period_end,
                activate=False,
                created_by=created_by,
            )
            return {
                "status": "draft", "version": result.version,
                "quality_summary": result.quality_summary,
            }
        result = await service.build(
            version=version,
            period_start=period_start,
            period_end=period_end,
            activate=False,
            created_by=created_by,
        )
        snapshot = await self.db.scalar(
            select(AnalysisBaselineSnapshot).where(
                AnalysisBaselineSnapshot.version == version
            )
        )
        if snapshot is None:
            raise RuntimeError("baseline draft disappeared before activation")
        await self.db.execute(
            update(AnalysisBaselineSnapshot)
            .where(
                AnalysisBaselineSnapshot.status == "active",
                AnalysisBaselineSnapshot.id != snapshot.id,
            )
            .values(status="retired")
        )
        snapshot.status = "active"
        snapshot.activated_at = utc_now_naive()
        await self.db.commit()
        return {
            "status": "activated", "version": result.version,
            "quality_summary": result.quality_summary,
            "snapshot_id": snapshot.id,
            "previous_snapshot_id": active.id if active is not None else None,
        }

    async def _rollback_baseline_activation(self, result: dict) -> None:
        snapshot_id = result.get("snapshot_id")
        previous_id = result.get("previous_snapshot_id")
        if snapshot_id:
            current = await self.db.get(AnalysisBaselineSnapshot, int(snapshot_id))
            if current is not None:
                current.status = "draft"
                current.activated_at = None
        if previous_id:
            previous = await self.db.get(AnalysisBaselineSnapshot, int(previous_id))
            if previous is not None:
                previous.status = "active"
                previous.activated_at = utc_now_naive()
        await self.db.commit()

    async def list_runs(self, *, limit: int = 20) -> list[PipelineRun]:
        return list((await self.db.execute(
            select(PipelineRun).order_by(PipelineRun.created_at.desc()).limit(limit)
        )).scalars())

    @staticmethod
    def response(run: PipelineRun) -> dict:
        def timestamp(value: datetime | None) -> str | None:
            return utc_isoformat(value) if value is not None else None

        return {
            "id": run.id,
            "trigger": run.trigger,
            "status": run.status,
            "stage": run.stage,
            "progress": run.progress,
            "requested_sources": run.requested_sources or [],
            "stage_results": run.stage_results or {},
            "quality_summary": run.quality_summary or {},
            "error_message": run.error_message,
            "scheduled_for": timestamp(run.scheduled_for),
            "started_at": timestamp(run.started_at),
            "finished_at": timestamp(run.finished_at),
            "created_at": timestamp(run.created_at),
        }


def start_pipeline_run(run_id: str) -> None:
    async def runner() -> None:
        async with _pipeline_execution_lock:
            async with serialized_pipeline_run():
                async with async_session() as db:
                    await PipelineService(db).run(run_id)

    task = asyncio.create_task(runner(), name=f"pipeline:{run_id}")
    _pipeline_tasks.add(task)
    task.add_done_callback(_pipeline_tasks.discard)


async def recover_pipeline_runs() -> None:
    async with async_session() as db:
        service = PipelineService(db)
        await service.seed_sources()
        stale_before = utc_now_naive() - timedelta(hours=2)
        await db.execute(
            update(PipelineRun)
            .where(
                PipelineRun.status == "running",
                PipelineRun.heartbeat_at < stale_before,
            )
            .values(status="queued", stage="recovered", error_message=None)
        )
        await db.commit()
        rows = list((await db.execute(
            select(PipelineRun).where(PipelineRun.status == "queued")
        )).scalars())
    for row in rows:
        start_pipeline_run(row.id)


async def start_pipeline_scheduler(startup_delay_seconds: int) -> None:
    global _scheduler_task, _shutdown_event
    if _scheduler_task and not _scheduler_task.done():
        return
    _shutdown_event = asyncio.Event()

    async def scheduler() -> None:
        try:
            await asyncio.wait_for(_shutdown_event.wait(), timeout=startup_delay_seconds)
            return
        except asyncio.TimeoutError:
            pass
        while not _shutdown_event.is_set():
            now = utc_now_naive()
            slot = now.strftime("%Y%m%d%H%M")
            async with async_session() as db:
                service = PipelineService(db)
                due_ids = await service._enabled_spider_ids(due_only=True)
                try:
                    run = await service.create_run(
                        trigger="scheduled",
                        source_ids=due_ids,
                        requested_by=None,
                        idempotency_key=(
                            f"scheduled:{slot}:" + ",".join(map(str, sorted(due_ids)))
                        ),
                        scheduled_for=now,
                    )
                except ValueError:
                    run = None
                if run is not None and run.status == "queued":
                    start_pipeline_run(run.id)
            try:
                await asyncio.wait_for(_shutdown_event.wait(), timeout=60)
            except asyncio.TimeoutError:
                continue

    _scheduler_task = asyncio.create_task(scheduler(), name="pipeline-scheduler")


async def shutdown_pipeline_scheduler() -> None:
    if _shutdown_event is not None:
        _shutdown_event.set()
    if _scheduler_task is not None:
        await asyncio.gather(_scheduler_task, return_exceptions=True)
    if _pipeline_tasks:
        for task in list(_pipeline_tasks):
            task.cancel()
        await asyncio.gather(*list(_pipeline_tasks), return_exceptions=True)
