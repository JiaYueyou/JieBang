from sqlalchemy import select

from app.core.database import async_session
from app.models import (
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    StandardJob,
    StandardJobSource,
)
from app.services.analysis_service import AnalysisService
from app.schemas.analysis import InsightDecision


async def seed_analysis_data(db):
    java = Skill(
        name="Java",
        canonical_name="Java",
        canonical_key="java",
        category="programming_language",
        aliases=[],
    )
    rust = Skill(
        name="Rust",
        canonical_name="Rust",
        canonical_key="rust",
        category="programming_language",
        aliases=[],
    )
    db.add_all([java, rust])
    await db.flush()

    standard = StandardJob(
        name="Java 开发工程师",
        canonical_key="java开发工程师",
        aliases=[],
        stack="backend",
        level="middle",
        description="Java 服务端岗位能力模型。",
        source_count=12,
        status="active",
    )
    db.add(standard)
    await db.flush()

    raw_rows = []
    for month in (1, 2, 3):
        for index in range(4):
            sequence = (month - 1) * 4 + index + 1
            document = SourceDocument(
                source=f"来源{index % 2 + 1}",
                url=f"https://example.test/jobs/{sequence}",
                title="Java 开发工程师",
                content_fingerprint=f"{sequence:064d}",
                content_summary="Java Rust",
                source_meta={"posted_at": f"2026-{month:02d}-15"},
            )
            db.add(document)
            await db.flush()
            raw = RawJobRecord(
                source_document_id=document.id,
                title="Java 开发工程师",
                standardized_title="Java 开发工程师",
                company="示例企业",
                city="杭州" if index < 3 else "上海",
                salary_text="20K-30K" if index % 2 == 0 else "2-3万",
                jd_text="Java Rust",
                responsibilities="负责服务开发",
                requirements="熟悉 Java",
                keywords="Java",
                posted_at_text=f"2026-{month:02d}-15",
                dedup_status="unique",
                normalized_data={},
            )
            db.add(raw)
            await db.flush()
            raw_rows.append(raw)
            db.add(StandardJobSource(
                standard_job_id=standard.id,
                source_type="raw",
                source_id=raw.id,
                original_title=raw.title,
                confidence=0.95,
            ))
            db.add(JobSkillFact(
                raw_job_record_id=raw.id,
                skill_id=java.id,
                kind="required",
                importance=0.9,
                frequency=1,
                confidence=0.96,
                evidence_text="Java",
                verification_status="verified",
                extraction_method="rule",
                source_count=2,
            ))
            if month == 3:
                db.add(JobSkillFact(
                    raw_job_record_id=raw.id,
                    skill_id=rust.id,
                    kind="preferred",
                    importance=0.6,
                    frequency=1,
                    confidence=0.92,
                    evidence_text="Rust",
                    verification_status="verified",
                    extraction_method="rule",
                    source_count=2,
                ))
    await db.commit()
    return standard, raw_rows


def test_salary_and_time_parsers_cover_supported_formats():
    assert AnalysisService.parse_salary_k("20K-30K") == 25
    assert AnalysisService.parse_salary_k("2-3万") == 25
    assert AnalysisService.parse_salary_k("25k") == 25
    assert AnalysisService.parse_salary_k("面议") is None
    assert AnalysisService.parse_datetime("2026年03月15日").strftime("%Y-%m-%d") == "2026-03-15"
    assert AnalysisService.parse_datetime("invalid") is None


async def test_overview_builds_real_trends_and_emerging_skills():
    async with async_session() as db:
        await seed_analysis_data(db)
        overview = await AnalysisService(db).overview(
            months=3, keyword="Java", city=None
        )

        assert overview.months == ["2026-01", "2026-02", "2026-03"]
        assert overview.stats.total_jobs == 12
        assert overview.stats.average_salary_k == 25
        assert overview.stats.active_cities == 2
        assert overview.data_quality.insufficient_data is False
        assert overview.data_quality.valid_salary_records == 12
        assert overview.job_demand[0].values == [4, 4, 4]
        assert overview.locations[0].city == "杭州"
        assert overview.locations[0].value == 9
        assert [item.skill for item in overview.emerging_skills] == ["Rust"]
        assert overview.emerging_skills[0].growth == 100
        assert any(point.value == 4 for point in overview.heatmap)


async def test_job_insights_use_standard_job_sources_and_verified_facts():
    async with async_session() as db:
        standard, _ = await seed_analysis_data(db)
        insights = await AnalysisService(db).job_insights(
            skill="Rust", limit=10, user_id=1
        )

        assert len(insights.emerging_jobs) == 1
        assert insights.emerging_jobs[0].id == standard.id
        assert "Rust" in insights.emerging_jobs[0].core_skills
        assert len(insights.capability_changes) == 1
        assert insights.capability_changes[0].job_id == standard.id
        assert insights.capability_changes[0].added == ["Rust"]
        assert insights.data_quality.insufficient_data is False


async def test_emerging_job_decision_is_upserted_and_returned_in_insights():
    async with async_session() as db:
        standard, _ = await seed_analysis_data(db)
        service = AnalysisService(db)

        created = await service.decide_emerging_job(
            standard_job_id=standard.id,
            decision=InsightDecision.confirmed,
            note="人工复核通过",
            user_id=1,
        )
        updated = await service.decide_emerging_job(
            standard_job_id=standard.id,
            decision=InsightDecision.planned,
            note="转入招聘计划",
            user_id=1,
        )
        insights = await service.job_insights(skill=None, limit=10, user_id=1)

        assert created.id == updated.id
        assert updated.decision.value == "planned"
        assert insights.emerging_jobs[0].decision == "planned"


async def test_unverified_skills_are_excluded():
    async with async_session() as db:
        await seed_analysis_data(db)
        rows = (await db.execute(
            select(JobSkillFact).where(JobSkillFact.evidence_text == "Rust")
        )).scalars().all()
        for row in rows:
            row.verification_status = "unverified"
        await db.commit()

        overview = await AnalysisService(db).overview(
            months=3, keyword=None, city=None
        )
        assert all(item.skill != "Rust" for item in overview.emerging_skills)
        assert "Rust" not in overview.heatmap_skills
