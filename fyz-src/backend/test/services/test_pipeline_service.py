"""Automatic pipeline persistence and quality-gate tests."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import func, select

from app.core.database import async_session
from app.models import DataSource, GraphEnrichmentCandidate, GraphSnapshot, PipelineRun, Skill
from app.services.graph_service import GraphService
from app.services.pipeline_service import PipelineService


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
