"""Automatic pipeline persistence and quality-gate tests."""

import uuid
from datetime import datetime, timedelta

import pytest
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy import func, select

from app.core.database import async_session
from app.models import DataSource, GraphEnrichmentCandidate, GraphSnapshot, PipelineRun, Skill
from app.services.graph_service import GraphService
from app.services.pipeline_service import PipelineService
from app.models import PipelineRun


@pytest.mark.asyncio
async def test_seed_sources_aligns_registry_with_database():
    async with async_session() as db:
        await PipelineService(db).seed_sources()
        rows = list((await db.execute(
            select(DataSource).where(DataSource.source_type.like("crawler:%"))
        )).scalars())

        assert len(rows) == 4
        assert {row.crawl_config["spider_id"] for row in rows} == {2, 4, 5, 6}
        assert all(row.schedule_expression.startswith("interval:") for row in rows)
        assert all(row.next_run_at is not None for row in rows if row.enabled)


@pytest.mark.asyncio
async def test_automation_config_persists_schedule_and_quantity_limits():
    async with async_session() as db:
        service = PipelineService(db)
        saved = await service.save_automation_config({
            "enabled": True,
            "source_ids": [2, 6],
            "schedule_type": "daily",
            "interval_minutes": 60,
            "run_time": "03:30",
            "weekdays": [0, 2, 4],
            "max_records": 80,
            "max_pages": 4,
            "retry_count": 3,
            "retry_delay_minutes": 15,
            "timeout_seconds": 600,
        })

        assert saved["source_ids"] == [2, 6]
        rows = list((await db.execute(
            select(DataSource).where(DataSource.source_type.in_(["crawler:2", "crawler:6"]))
        )).scalars())
        assert all(row.schedule_expression == "每天 03:30" for row in rows)
        assert all(row.crawl_config["max_records"] == 80 for row in rows)
        assert all(row.next_run_at is not None for row in rows)


@pytest.mark.asyncio
async def test_source_health_reports_freshness_and_failure_alerts():
    async with async_session() as db:
        service = PipelineService(db)
        await service.seed_sources()
        row = await db.scalar(select(DataSource).where(DataSource.source_type == "crawler:2"))
        row.last_success_at = datetime.utcnow() - timedelta(minutes=5)
        row.freshness_slo_minutes = 60
        row.consecutive_failures = 0
        row.enabled = True
        row.crawl_config = {**(row.crawl_config or {}), "automation_enabled": True}
        await db.commit()

        healthy = await service.source_health(2)
        assert healthy["status"] == "healthy"
        assert healthy["alert_active"] is False

        row.last_success_at = datetime.utcnow() - timedelta(minutes=120)
        await db.commit()
        stale = await service.source_health(2)
        assert stale["status"] == "stale"
        assert stale["alert_active"] is True

        row.consecutive_failures = 2
        row.last_error = "timeout"
        await db.commit()
        failing = await service.source_health(2)
        assert failing["status"] == "failing"
        assert failing["last_error"] == "timeout"

        row.enabled = False
        await db.commit()
        disabled = await service.source_health(2)
        assert disabled["status"] == "disabled"
        assert disabled["alert_active"] is False

        row.enabled = True
        row.crawl_config = {**row.crawl_config, "automation_enabled": False}
        await db.commit()
        manual = await service.source_health(2)
        assert manual["status"] == "manual"
        assert manual["alert_active"] is False

        row.crawl_config = {**row.crawl_config, "automation_enabled": True}
        row.last_success_at = None
        row.last_run_at = None
        row.consecutive_failures = 0
        row.next_run_at = datetime.utcnow() - timedelta(minutes=10)
        await db.commit()
        overdue = await service.source_health(2)
        assert overdue["status"] == "overdue"
        assert overdue["alert_active"] is True


@pytest.mark.asyncio
async def test_graph_sync_mode_uses_daily_full_reconciliation():
    async with async_session() as db:
        service = PipelineService(db)
        assert await service._graph_sync_mode() == "full"
        db.add(GraphSnapshot(
            id=str(uuid.uuid4()), version="recent-full", snapshot_type="full",
            status="succeeded", created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        ))
        await db.commit()

        assert await service._graph_sync_mode() == "incremental"


@pytest.mark.asyncio
async def test_scheduled_run_idempotency_returns_same_record():
    async with async_session() as db:
        service = PipelineService(db)
        first = await service.create_run(
            trigger="scheduled", source_ids=[4, 5], requested_by=None,
            idempotency_key="scheduled:123", scheduled_for=datetime(2026, 8, 9),
        )
        second = await service.create_run(
            trigger="scheduled", source_ids=[4, 5], requested_by=None,
            idempotency_key="scheduled:123", scheduled_for=datetime(2026, 8, 9),
        )

        assert second.id == first.id
        assert int(await db.scalar(select(func.count(PipelineRun.id))) or 0) == 1


@pytest.mark.asyncio
async def test_auto_publish_requires_strong_complete_grounding():
    async with async_session() as db:
        skill = Skill(name="AutoSkill", canonical_name="AutoSkill", canonical_key="autoskill", category="framework", aliases=[])
        second_skill = Skill(name="WeakSkill", canonical_name="WeakSkill", canonical_key="weakskill", category="framework", aliases=[])
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="auto-gate", snapshot_type="incremental",
            status="running", created_at=datetime.utcnow(),
        )
        db.add_all([skill, second_skill, snapshot])
        await db.flush()
        strong = GraphEnrichmentCandidate(
            snapshot_id=snapshot.id, skill_id=skill.id,
            candidate_data={
                "tech_points": [{"name": "Runtime", "knowledge_points": [{"name": "Scheduler"}]}],
                "machine_validation": {"rejected_count": 0},
            },
            evidence_source_ids=["e1", "e2"], confidence=0.96,
            verification_status="machine_validated", machine_validation_status="passed",
            review_status="pending", publication_status="draft",
        )
        weak = GraphEnrichmentCandidate(
            snapshot_id=snapshot.id, skill_id=second_skill.id,
            candidate_data={"tech_points": []}, evidence_source_ids=["e1"], confidence=0.99,
            verification_status="machine_validated", machine_validation_status="passed",
            review_status="pending", publication_status="draft",
        )
        db.add_all([strong, weak])
        await db.commit()

        approved = await GraphService(db).auto_approve_enrichment_candidates(
            snapshot_id=snapshot.id, minimum_confidence=0.90,
        )
        await db.commit()

        assert approved == [strong.id]
        assert strong.review_status == "approved"
        assert strong.publication_status == "approved"
        assert weak.review_status == "pending"


@pytest.mark.asyncio
async def test_pipeline_acknowledges_crawler_only_after_successful_import():
    async with async_session() as db:
        service = PipelineService(db)
        run = PipelineRun(
            id=str(uuid.uuid4()), idempotency_key=f"test:{uuid.uuid4()}",
            trigger="manual", status="running", stage="crawl", progress=10,
            requested_sources=[2], stage_results={}, quality_summary={},
        )
        db.add(run)
        await db.commit()
        source = Mock(enabled=True, crawl_config={}, consecutive_failures=0)
        service.crawler = Mock()
        service.crawler.poll_spider.return_value = {
            "returncode": 0, "filename": "iflytek_1.json", "records_count": 1,
            "output_changed": True, "elapsed": 1, "error_category": "ok",
            "error_reason": "", "message": "ok",
        }
        service._source_row = AsyncMock(return_value=source)
        service._update = AsyncMock()

        with patch(
            "app.services.pipeline_service.ImportService.import_files",
            new=AsyncMock(return_value={"imported": 1}),
        ):
            result = await service._run_source(run, 2)

        assert result["status"] == "succeeded"
        service.crawler.acknowledge_import.assert_called_once_with(2, "iflytek_1.json")


@pytest.mark.asyncio
async def test_pipeline_import_failure_leaves_crawler_batch_unacknowledged():
    async with async_session() as db:
        service = PipelineService(db)
        run = PipelineRun(
            id=str(uuid.uuid4()), idempotency_key=f"test:{uuid.uuid4()}",
            trigger="manual", status="running", stage="crawl", progress=10,
            requested_sources=[2], stage_results={}, quality_summary={},
        )
        db.add(run)
        await db.commit()
        source = Mock(enabled=True, crawl_config={}, consecutive_failures=0)
        service.crawler = Mock()
        service.crawler.poll_spider.return_value = {
            "returncode": 0, "filename": "iflytek_1.json", "records_count": 1,
            "output_changed": True, "elapsed": 1, "error_category": "ok",
            "error_reason": "", "message": "ok",
        }
        service._source_row = AsyncMock(return_value=source)
        service._update = AsyncMock()

        with patch(
            "app.services.pipeline_service.ImportService.import_files",
            new=AsyncMock(side_effect=RuntimeError("database unavailable")),
        ):
            result = await service._run_source(run, 2)

        assert result["status"] == "failed"
        service.crawler.acknowledge_import.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_refreshes_retrieval_before_graph_publish():
    async with async_session() as db:
        run = PipelineRun(
            id=str(uuid.uuid4()), idempotency_key=f"test:{uuid.uuid4()}",
            trigger="manual", status="queued", stage="queued", progress=0,
            requested_sources=[2], stage_results={}, quality_summary={},
        )
        db.add(run)
        await db.commit()
        service = PipelineService(db)
        service._run_source = AsyncMock(return_value={
            "spider_id": 2,
            "status": "succeeded",
            "import": {
                "imported": 1, "duplicates": 0, "skill_facts": 1,
                "near_duplicates": 0, "low_quality": 0, "time_anomalies": 0,
                "cross_source_verified": 0, "observations": 1,
            },
        })
        service._refresh_baseline = AsyncMock(return_value={"status": "skipped"})
        service._graph_sync_mode = AsyncMock(return_value="incremental")
        retrieval_response = Mock()
        retrieval_response.model_dump.return_value = {
            "version": "retrieval-v1", "chunk_count": 1, "entry_count": 1,
        }
        overview = Mock()
        overview.stats.total_jobs = 1
        overview.stats.new_skills = 0
        overview.baseline.version = "baseline-v1"

        with patch(
            "app.services.pipeline_service.RetrievalService.rebuild_index",
            new=AsyncMock(return_value=retrieval_response),
        ) as rebuild, patch(
            "app.services.pipeline_service.GraphService.sync",
            new=AsyncMock(return_value={"snapshot_id": "graph-v1"}),
        ) as graph_sync, patch(
            "app.services.pipeline_service.AnalysisService.overview",
            new=AsyncMock(return_value=overview),
        ):
            await service.run(run.id)

        rebuilt = rebuild.await_args.kwargs
        assert rebuilt["backend"]
        assert rebuilt["created_by"] is None
        graph_sync.assert_awaited_once()
        assert graph_sync.await_args.kwargs["mode"] == "incremental"
        await db.refresh(run)
        assert run.status == "succeeded"
        assert run.stage_results["retrieval_refresh"]["status"] == "succeeded"
        assert run.stage_results["retrieval_refresh"]["version"] == "retrieval-v1"


@pytest.mark.asyncio
async def test_pipeline_quality_gate_blocks_downstream_publication():
    async with async_session() as db:
        run = PipelineRun(
            id=str(uuid.uuid4()), idempotency_key=f"test:{uuid.uuid4()}",
            trigger="manual", status="queued", stage="queued", progress=0,
            requested_sources=[2], stage_results={}, quality_summary={},
        )
        db.add(run)
        await db.commit()
        service = PipelineService(db)
        service._run_source = AsyncMock(return_value={
            "spider_id": 2,
            "status": "succeeded",
            "import": {
                "total": 4, "imported": 4, "duplicates": 0, "skill_facts": 4,
                "near_duplicates": 0, "low_quality": 2, "time_anomalies": 0,
                "observations": 4,
                "quality_status_counts": {
                    "accepted": 2, "warning": 0, "rejected": 2,
                },
            },
        })

        with patch(
            "app.services.pipeline_service.RetrievalService.rebuild_index",
            new=AsyncMock(),
        ) as rebuild, patch(
            "app.services.pipeline_service.GraphService.sync",
            new=AsyncMock(),
        ) as graph_sync:
            await service.run(run.id)

        rebuild.assert_not_awaited()
        graph_sync.assert_not_awaited()
        await db.refresh(run)
        assert run.status == "failed"
        assert run.stage_results["quality_gate"]["status"] == "rejected"
        assert run.quality_summary["gate"]["rejected_ratio"] == 0.5


def test_pipeline_quality_gate_rejects_excessive_quarantine_ratio():
    gate = PipelineService._evaluate_quality_gate({
        "total": 20, "imported": 18, "quarantined_records": 2,
        "quality_evaluated": 18, "rejected": 0, "time_anomalies": 0,
    })

    assert gate["status"] == "rejected"
    assert gate["quarantine_ratio"] == 0.1
    assert any("quarantine_ratio" in reason for reason in gate["reasons"])


def test_incremental_graph_payload_keeps_only_affected_job_sources():
    nodes = {
        "Job": [{"id": "job:1"}, {"id": "job:2"}],
        "SourceDocument": [{"id": "source:1"}, {"id": "source:2"}],
        "TechStack": [{"id": "skill:1"}],
        "GraphSnapshot": [{"id": "snapshot:current"}],
    }
    edges = {
        "REQUIRES_AREA": [
            {"source": "job:1", "target": "area:a"},
            {"source": "job:2", "target": "area:b"},
        ],
        "SUPPORTS": [
            {"source": "source:1", "target": "job:1"},
            {"source": "source:1", "target": "skill:1"},
            {"source": "source:2", "target": "job:2"},
        ],
        "CONTAINS": [{"source": "area:a", "target": "skill:1"}],
    }

    filtered_nodes, filtered_edges = GraphService._filter_incremental_payload(
        nodes, edges, [1]
    )

    assert filtered_nodes["Job"] == [{"id": "job:1"}]
    assert filtered_nodes["SourceDocument"] == [{"id": "source:1"}]
    assert filtered_nodes["TechStack"] == nodes["TechStack"]
    assert len(filtered_edges["REQUIRES_AREA"]) == 1
    assert len(filtered_edges["SUPPORTS"]) == 2
    assert filtered_edges["CONTAINS"] == edges["CONTAINS"]
