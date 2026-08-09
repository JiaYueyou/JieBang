from datetime import date, datetime

from sqlalchemy import select

from app.core.database import async_session
from app.models import (
    AnalysisBaselineSkill,
    AnalysisBaselineSnapshot,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
)
from app.services.historical_baseline_service import HistoricalBaselineService
from app.services.analysis_service import AnalysisService


async def test_builds_and_activates_a_ready_historical_baseline():
    async with async_session() as db:
        skill = Skill(
            name="Python", canonical_name="Python", canonical_key="python-baseline-test",
            category="programming_language", aliases=[], validation_status="approved",
        )
        db.add(skill)
        await db.flush()
        for index, posted_at in enumerate((
            datetime(2025, 7, 2), datetime(2025, 7, 9),
            datetime(2025, 8, 2), datetime(2025, 8, 9),
        ), start=1):
            document = SourceDocument(
                source=f"source-{index % 2}",
                external_id=f"baseline-{index}",
                url=f"https://example.test/baseline/{index}",
                title="Python 工程师",
                company=f"company-{index}",
                content_fingerprint=f"baseline-{index:055d}",
                content_summary="Python 服务开发",
                source_meta={"posted_at": posted_at.isoformat()},
            )
            db.add(document)
            await db.flush()
            raw = RawJobRecord(
                source_document_id=document.id,
                title="Python 工程师",
                standardized_title="Python 工程师",
                company=document.company,
                city="杭州",
                jd_text="Python 服务开发",
                responsibilities="",
                requirements="Python",
                keywords="Python",
                posted_at=posted_at,
                posted_at_text=posted_at.date().isoformat(),
                quality_status="accepted",
                normalized_data={},
            )
            db.add(raw)
            await db.flush()
            db.add(JobSkillFact(
                raw_job_record_id=raw.id,
                skill_id=skill.id,
                kind="required",
                importance=0.9,
                frequency=1,
                confidence=0.95,
                evidence_text="Python",
                verification_status="verified",
                extraction_method="rule",
                source_count=2,
            ))
        await db.commit()

        service = HistoricalBaselineService(db)
        service.MIN_CLUSTERS = 4
        service.MIN_SOURCES = 2
        service.MIN_MONTHS = 2
        service.MIN_REVIEWABLE_FACTS = 4
        result = await service.build(
            version="baseline-test-v1",
            period_start=date(2025, 7, 1),
            period_end=date(2025, 8, 31),
            activate=True,
        )
        assert result.ready is True
        assert result.status == "active"
        snapshot = (await db.execute(select(AnalysisBaselineSnapshot))).scalar_one()
        assert snapshot.status == "active"
        row = (await db.execute(
            select(AnalysisBaselineSkill).where(
                AnalysisBaselineSkill.baseline_id == snapshot.id
            )
        )).scalar_one()
        assert row.cluster_count == 4
        assert row.source_count == 2
        assert row.active_period_count == 2
        active_snapshot, active_skills = await AnalysisService(db)._load_active_trend_baseline()
        assert active_snapshot is not None
        assert active_snapshot.version == "baseline-test-v1"
        assert len(active_skills) == 1


async def test_baseline_unions_skills_from_every_row_in_a_deduplicated_cluster():
    async with async_session() as db:
        skills = []
        for name in ("Java", "Serverless"):
            skill = Skill(
                name=name,
                canonical_name=name,
                canonical_key=f"{name.casefold()}-cluster-union",
                category="programming_language" if name == "Java" else "cloud",
                aliases=[],
                validation_status="approved",
            )
            db.add(skill)
            skills.append(skill)
        await db.flush()

        for index, skill in enumerate(skills, start=1):
            document = SourceDocument(
                source=f"portal-{index}",
                external_id=f"cluster-member-{index}",
                url=f"https://example.test/jobs/{index}",
                title="后端开发工程师",
                company="同一公司",
                content_fingerprint=f"cluster-member-{index:049d}",
                content_summary=skill.name,
                source_meta={"posted_at": "2025-08-10T00:00:00"},
            )
            db.add(document)
            await db.flush()
            raw = RawJobRecord(
                source_document_id=document.id,
                title="后端开发工程师",
                standardized_title="后端开发工程师",
                company="同一公司",
                city="北京",
                jd_text=f"后端开发岗位要求掌握 {skill.name} 技术。",
                responsibilities="",
                requirements=skill.name,
                keywords=skill.name,
                posted_at=datetime(2025, 8, 10),
                posted_at_text="2025-08-10",
                quality_status="accepted",
                normalized_data={},
            )
            db.add(raw)
            await db.flush()
            db.add(JobSkillFact(
                raw_job_record_id=raw.id,
                skill_id=skill.id,
                kind="required",
                importance=0.9,
                frequency=1,
                confidence=0.95,
                evidence_text=skill.name,
                verification_status="unverified",
                extraction_method="rule",
                source_count=1,
            ))
        await db.commit()

        service = HistoricalBaselineService(db)
        service.MIN_CLUSTERS = 1
        service.MIN_SOURCES = 1
        service.MIN_MONTHS = 1
        service.MIN_REVIEWABLE_FACTS = 2
        result = await service.build(
            version="baseline-cluster-skill-union-v1",
            period_start=date(2025, 8, 1),
            period_end=date(2025, 8, 31),
            activate=True,
        )

        assert result.quality_summary["deduplicated_cluster_count"] == 1
        rows = list((await db.execute(select(AnalysisBaselineSkill))).scalars())
        assert {row.skill_id for row in rows} == {skill.id for skill in skills}
        assert all(row.cluster_count == 1 for row in rows)
