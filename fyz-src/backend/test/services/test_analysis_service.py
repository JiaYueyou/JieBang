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
from app.schemas.analysis import TrendWindow


async def _add_raw(db, standard, skill, title, month, sequence, index):
    """构造一条带来源文档、标准岗位映射和已确认技能事实的岗位记录。"""
    document = SourceDocument(
        source=f"来源{index % 2 + 1}",
        url=f"https://example.test/jobs/{sequence}",
        title=title,
        content_fingerprint=f"{sequence:064d}",
        content_summary=skill.name,
        source_meta={"posted_at": f"2026-{month:02d}-15"},
    )
    db.add(document)
    await db.flush()
    raw = RawJobRecord(
        source_document_id=document.id,
        standard_job_id=standard.id,
        title=title,
        standardized_title=title,
        company=f"示例企业{index}",
        city="杭州" if index < 3 else "上海",
        salary_text="20K-30K" if index % 2 == 0 else "2-3万",
        jd_text=skill.name,
        responsibilities="负责服务开发",
        requirements=f"熟悉 {skill.name}",
        keywords=skill.name,
        posted_at_text=f"2026-{month:02d}-15",
        dedup_status="unique",
        normalized_data={},
    )
    db.add(raw)
    await db.flush()
    db.add(StandardJobSource(
        standard_job_id=standard.id,
        source_type="raw",
        source_id=raw.id,
        original_title=title,
        confidence=0.95,
    ))
    db.add(JobSkillFact(
        raw_job_record_id=raw.id,
        skill_id=skill.id,
        kind="required",
        importance=0.9,
        frequency=1,
        confidence=0.96,
        evidence_text=skill.name,
        verification_status="verified",
        extraction_method="rule",
        source_count=2,
    ))
    return raw


async def seed_analysis_data(db):
    """构造 6 个月数据：基线期（2026-01~03）只有 Java，窗口期（04~06）出现 Rust。

    - Java：历史常见技能，基线期与窗口期都存在（成熟期）；
    - Rust：历史基线中不存在、仅窗口期出现（新增技能）；
    - Rust 开发工程师：仅在窗口期出现的标准岗位（新增岗位）。
    """
    java = Skill(
        name="Java", canonical_name="Java", canonical_key="java",
        category="programming_language", aliases=[],
    )
    rust = Skill(
        name="Rust", canonical_name="Rust", canonical_key="rust",
        category="programming_language", aliases=[],
    )
    db.add_all([java, rust])
    await db.flush()

    java_standard = StandardJob(
        name="Java 开发工程师", canonical_key="java开发工程师", aliases=[],
        stack="backend", level="middle",
        description="Java 服务端岗位能力模型。",
        source_count=24, status="active",
    )
    rust_standard = StandardJob(
        name="Rust 开发工程师", canonical_key="rust开发工程师", aliases=[],
        stack="backend", level="middle",
        description="Rust 系统开发岗位能力模型。",
        source_count=12, status="active",
    )
    db.add_all([java_standard, rust_standard])
    await db.flush()

    raw_rows = []
    sequence = 0
    # 基线期：2026-01 ~ 2026-03，每月 4 条 Java
    for month in (1, 2, 3):
        for index in range(4):
            sequence += 1
            raw_rows.append(await _add_raw(
                db, java_standard, java, "Java 开发工程师", month, sequence, index
            ))
    # 窗口期：2026-04 ~ 2026-06，每月 4 条 Java + 4 条 Rust
    for month in (4, 5, 6):
        for index in range(4):
            sequence += 1
            raw_rows.append(await _add_raw(
                db, java_standard, java, "Java 开发工程师", month, sequence, index
            ))
            sequence += 1
            raw_rows.append(await _add_raw(
                db, rust_standard, rust, "Rust 开发工程师", month, sequence, index
            ))
    await db.commit()
    return java_standard, rust_standard, raw_rows


def test_salary_and_time_parsers_cover_supported_formats():
    assert AnalysisService.parse_salary_k("20K-30K") == 25
    assert AnalysisService.parse_salary_k("2-3万") == 25
    assert AnalysisService.parse_salary_k("25k") == 25
    assert AnalysisService.parse_salary_k("面议") is None
    assert AnalysisService.parse_datetime("2026年03月15日").strftime("%Y-%m-%d") == "2026-03-15"
    assert AnalysisService.parse_datetime("invalid") is None


async def test_overview_uses_historical_baseline_for_new_and_growing_skills():
    async with async_session() as db:
        java_standard, rust_standard, _ = await seed_analysis_data(db)
        overview = await AnalysisService(db).overview(
            window=TrendWindow.months_3, keyword=None, city=None
        )

        # 窗口 = 2026-04~06；基线期 = 2026-01~03
        assert overview.months == ["2026-04", "2026-05", "2026-06"]
        assert overview.window == TrendWindow.months_3
        assert overview.window_label == "近 3 个月"
        assert overview.granularity == "month"

        by_skill = {item.skill: item for item in overview.emerging_skills}
        # Rust 不在历史基线 → 新增技能
        assert "Rust" in by_skill
        rust_item = by_skill["Rust"]
        assert rust_item.stage == "新出现"
        assert rust_item.growth is None
        assert rust_item.previous_count == 0
        assert rust_item.current_count >= 2
        # Java 历史基线已有，成熟/增长技能不能混入“新兴技能”。
        assert "Java" not in by_skill

        # 新增岗位：Rust 开发工程师仅在窗口期出现
        assert [job.name for job in overview.new_jobs] == ["Rust 开发工程师"]
        assert overview.new_jobs[0].id == rust_standard.id
        assert "Rust" in overview.new_jobs[0].core_skills

        # 窗口期有充分事实，不应再报"基线不足"
        assert overview.data_quality.insufficient_data is False

        # 参考基线仍包含两个标准岗位
        assert overview.baseline.standard_job_count == 2
        assert overview.baseline.mature_job_count == 2
        assert overview.baseline.job_standards == []


async def test_reference_standards_are_loaded_with_server_side_pagination():
    async with async_session() as db:
        await seed_analysis_data(db)
        service = AnalysisService(db)

        first_page = await service.list_reference_standards(
            page=1, page_size=1, keyword=None, stack=None
        )
        assert first_page.total == 2
        assert first_page.total_pages == 2
        assert len(first_page.items) == 1

        rust_page = await service.list_reference_standards(
            page=1, page_size=20, keyword="Rust", stack="backend"
        )
        assert rust_page.total == 1
        assert [item.name for item in rust_page.items] == ["Rust 开发工程师"]


async def test_overview_locations_use_one_city_level_and_split_multi_city_jobs():
    async with async_session() as db:
        _, _, raw_rows = await seed_analysis_data(db)
        for row in raw_rows[12:]:
            row.city = "广东省"
        raw_rows[12].city = "北京"
        raw_rows[13].city = "北京市"
        raw_rows[14].city = "北京、上海"
        raw_rows[15].city = "上海北京"
        await db.commit()

        overview = await AnalysisService(db).overview(
            window=TrendWindow.months_3, keyword=None, city=None
        )

        assert [(item.city, item.value) for item in overview.locations] == [
            ("北京", 4),
            ("上海", 2),
        ]
        assert overview.stats.active_cities == 2


async def test_overview_day_window_works_without_historical_baseline():
    """短窗口（15 天）也能正常输出：day 粒度、结构完整。"""
    async with async_session() as db:
        await seed_analysis_data(db)
        overview = await AnalysisService(db).overview(
            window=TrendWindow.days_15, keyword=None, city=None
        )
        assert overview.granularity == "day"
        assert len(overview.months) == 15
        # 窗口内仍有数据与月份标签（样本量不足时会标 insufficient_data，但结构完整）
        assert overview.stats.total_jobs > 0
        assert len(overview.months) == len(overview.job_demand[0].values) if overview.job_demand else True


async def test_six_month_window_uses_its_first_half_as_history_when_needed():
    """A full-coverage window must not relabel established skills as new."""
    async with async_session() as db:
        await seed_analysis_data(db)

        overview = await AnalysisService(db).overview(
            window=TrendWindow.months_6, keyword=None, city=None
        )

        by_skill = {item.skill: item for item in overview.emerging_skills}
        assert "Java" not in by_skill
        assert by_skill["Rust"].stage == "新出现"
        assert by_skill["Rust"].previous_count == 0


async def test_known_historical_technology_is_not_reported_as_new_when_local_baseline_misses_it():
    async with async_session() as db:
        await seed_analysis_data(db)
        perl = Skill(
            name="Perl", canonical_name="Perl", canonical_key="perl-history-catalog",
            category="programming_language", aliases=[],
        )
        standard = StandardJob(
            name="Perl开发工程师", canonical_key="perl-history-catalog-job", aliases=[],
            stack="backend", level="middle", description="", source_count=6,
            status="active",
        )
        db.add_all([perl, standard])
        await db.flush()
        sequence = 20_000
        for month in (4, 5, 6):
            for index in range(2):
                sequence += 1
                await _add_raw(
                    db, standard, perl, standard.name, month, sequence, index
                )
        await db.commit()

        overview = await AnalysisService(db).overview(
            window=TrendWindow.months_3,
            keyword=None,
            city=None,
            emerging_page_size=100,
        )

        by_skill = {item.skill: item for item in overview.emerging_skills}
        assert by_skill["Perl"].stage == "成熟技术"
        assert by_skill["Rust"].stage == "新出现"
        assert overview.stats.new_skills == 1


async def test_new_job_overview_separates_observations_from_confirmed_candidates():
    """Single-source noise is counted but not presented as a decision candidate."""
    async with async_session() as db:
        _, _, _ = await seed_analysis_data(db)
        skill = (await db.execute(
            select(Skill).where(Skill.name == "Rust")
        )).scalar_one()
        standard = StandardJob(
            name="单来源新岗位", canonical_key="single-source-new-job", aliases=[],
            stack="backend", level="middle", description="",
            source_count=1, status="active",
        )
        db.add(standard)
        await db.flush()
        await _add_raw(db, standard, skill, standard.name, 6, 9999, 0)
        await db.commit()

        overview = await AnalysisService(db).overview(
            window=TrendWindow.months_3, keyword=None, city=None,
            new_job_page_size=100,
        )

        assert "单来源新岗位" not in {job.name for job in overview.new_jobs}
        assert overview.new_job_observation_total > overview.new_jobs_total


async def test_new_skill_overview_keeps_single_source_first_observation():
    """Weak first-seen signals stay visible but are clearly downgraded."""
    async with async_session() as db:
        await seed_analysis_data(db)
        zig = Skill(
            name="Zig", canonical_name="Zig", canonical_key="zig-single-signal",
            category="programming_language", aliases=[], validation_status="approved",
        )
        standard = StandardJob(
            name="Zig 开发工程师", canonical_key="zig-single-signal-job", aliases=[],
            stack="backend", level="middle", description="",
            source_count=1, status="active",
        )
        db.add_all([zig, standard])
        await db.flush()
        await _add_raw(db, standard, zig, standard.name, 6, 10000, 0)
        await db.commit()

        overview = await AnalysisService(db).overview(
            window=TrendWindow.months_3, keyword=None, city=None,
            emerging_page_size=100,
        )

        signal = next(item for item in overview.emerging_skills if item.skill == "Zig")
        assert signal.stage == "新出现·单源观察"
        assert signal.current_sources == 1
        assert signal.current_periods == 1


async def test_job_insights_use_standard_job_sources_and_verified_facts():
    async with async_session() as db:
        _, rust_standard, _ = await seed_analysis_data(db)
        insights = await AnalysisService(db).job_insights(
            skill="Rust", limit=10, user_id=1
        )

        assert len(insights.emerging_jobs) == 1
        assert insights.emerging_jobs[0].id == rust_standard.id
        assert "Rust" in insights.emerging_jobs[0].core_skills
        # Java 岗位技能跨期稳定 → 无能力变化；Rust 是新增岗位而非既有岗位变化
        assert insights.capability_changes == []
        assert insights.baseline.standard_job_count == 2


def test_capability_changes_require_same_job_evidence_in_both_periods():
    standard = StandardJob(
        id=99,
        name="Python开发工程师",
        canonical_key="python开发工程师",
        aliases=[],
        stack="backend",
        source_count=2,
        status="active",
    )
    python = Skill(
        id=88,
        name="Python",
        canonical_name="Python",
        canonical_key="python",
        category="programming_language",
        aliases=[],
    )
    current_only_fact = JobSkillFact(
        raw_job_record_id=2,
        skill_id=python.id,
        kind="required",
        importance=0.9,
        frequency=1,
        confidence=0.95,
        evidence_text="Python",
        verification_status="verified",
        extraction_method="rule",
        source_count=2,
    )

    changes = AnalysisService._capability_changes(
        standard_jobs=[standard],
        source_ids={standard.id: {2}},
        facts=[(current_only_fact, python)],
        record_month={1: "2026-05", 2: "2026-06"},
        skill_filter="",
        limit=10,
    )

    assert changes == []


def test_capability_changes_use_recent_multi_evidence_and_exclude_soft_skills():
    standard = StandardJob(
        id=100, name="AI应用工程师", canonical_key="ai应用工程师",
        aliases=[], stack="ai", source_count=6, status="active",
    )
    java = Skill(id=101, name="Java", canonical_name="Java", canonical_key="java", category="programming_language", aliases=[])
    rag = Skill(id=102, name="RAG", canonical_name="RAG", canonical_key="rag", category="ai_ml", aliases=[])
    communication = Skill(id=103, name="沟通能力", canonical_name="沟通能力", canonical_key="沟通能力", category="soft_skill", aliases=[])

    def fact(raw_id: int, skill: Skill) -> tuple[JobSkillFact, Skill]:
        return JobSkillFact(
            raw_job_record_id=raw_id, skill_id=skill.id, kind="required",
            importance=.9, frequency=1, confidence=.95,
            evidence_text=skill.name, verification_status="verified",
            extraction_method="rule", source_count=2,
        ), skill

    changes = AnalysisService._capability_changes(
        standard_jobs=[standard], source_ids={100: {1, 2, 3, 4, 5, 6}},
        facts=[
            fact(1, java), fact(2, java),
            fact(5, java), fact(6, java),
            fact(5, rag), fact(6, rag),
            fact(5, communication), fact(6, communication),
        ],
        record_month={
            1: "2026-05", 2: "2026-05", 3: "2026-06", 4: "2026-06",
            5: "2026-07", 6: "2026-08",
        },
        skill_filter="", limit=10,
    )

    assert len(changes) == 1
    assert changes[0].added == ["RAG"]
    assert changes[0].strengthened == ["Java"]
    assert "沟通能力" not in changes[0].modified + changes[0].added
    assert changes[0].previous_sample_count == 4
    assert changes[0].current_sample_count == 2


def test_capability_changes_do_not_weaken_current_hard_requirements():
    standard = StandardJob(
        id=104, name="AI应用开发工程师", canonical_key="ai应用开发工程师",
        aliases=[], stack="ai", source_count=7, status="active",
    )
    python = Skill(id=105, name="Python", canonical_name="Python", canonical_key="python", category="programming_language", aliases=[])
    rag = Skill(id=106, name="RAG", canonical_name="RAG", canonical_key="rag", category="ai_ml", aliases=[])

    def fact(raw_id: int, skill: Skill) -> tuple[JobSkillFact, Skill]:
        return JobSkillFact(
            raw_job_record_id=raw_id, skill_id=skill.id, kind="required",
            importance=.9, frequency=1, confidence=.95,
            evidence_text=f"硬性要求：{skill.name}", verification_status="verified",
            extraction_method="rule", source_count=2,
        ), skill

    changes = AnalysisService._capability_changes(
        standard_jobs=[standard], source_ids={104: {1, 2, 3, 4, 5, 6, 7}},
        facts=[
            fact(1, python), fact(2, python), fact(3, python), fact(4, python),
            fact(5, python), fact(6, python),
            fact(5, rag), fact(6, rag),
        ],
        record_month={
            1: "2026-05", 2: "2026-05", 3: "2026-06", 4: "2026-06",
            5: "2026-07", 6: "2026-08", 7: "2026-08",
        },
        skill_filter="", limit=10,
    )

    assert len(changes) == 1
    assert changes[0].added == ["RAG"]
    assert "Python" not in changes[0].weakened
    assert "Python" not in changes[0].removed


async def test_emerging_job_decision_is_upserted_and_returned_in_insights():
    async with async_session() as db:
        _, rust_standard, _ = await seed_analysis_data(db)
        service = AnalysisService(db)

        created = await service.decide_emerging_job(
            standard_job_id=rust_standard.id,
            decision=InsightDecision.confirmed,
            note="人工复核通过",
            user_id=1,
        )
        updated = await service.decide_emerging_job(
            standard_job_id=rust_standard.id,
            decision=InsightDecision.planned,
            note="转入招聘计划",
            user_id=1,
        )
        insights = await service.job_insights(skill=None, limit=10, user_id=1)

        assert created.id == updated.id
        assert updated.decision.value == "planned"
        rust_insights = [
            item for item in insights.emerging_jobs
            if item.id == rust_standard.id
        ]
        assert rust_insights[0].decision == "planned"


async def test_overview_paginates_emerging_and_new_jobs():
    """新兴技能与新增岗位支持分页查询：total 全量、每页切片、页码稳定。"""
    async with async_session() as db:
        await seed_analysis_data(db)
        service = AnalysisService(db)

        full = await service.overview(
            window=TrendWindow.months_3, keyword=None, city=None,
            emerging_page_size=50, new_job_page_size=50,
        )
        assert full.emerging_total == len(full.emerging_skills) == 1
        assert full.new_jobs_total == len(full.new_jobs) >= 1

        page1 = await service.overview(
            window=TrendWindow.months_3, keyword=None, city=None,
            emerging_page=1, emerging_page_size=1,
            new_job_page=1, new_job_page_size=1,
        )
        assert len(page1.emerging_skills) == 1
        assert len(page1.new_jobs) == 1
        assert page1.emerging_total == full.emerging_total
        assert page1.new_jobs_total == full.new_jobs_total

        page2 = await service.overview(
            window=TrendWindow.months_3, keyword=None, city=None,
            emerging_page=2, emerging_page_size=1,
            new_job_page=1, new_job_page_size=1,
        )
        assert page2.emerging_skills == []
        # 统计口径不受分页影响
        assert page2.emerging_total == full.emerging_total
        assert page2.stats.new_skills == full.stats.new_skills

        matched = await service.overview(
            window=TrendWindow.months_3, keyword=None, city=None,
            new_job_keyword="rUsT",
        )
        assert [job.name for job in matched.new_jobs] == ["Rust 开发工程师"]
        assert matched.new_jobs_total == 1

        no_match = await service.overview(
            window=TrendWindow.months_3, keyword=None, city=None,
            new_job_keyword="not-a-job",
        )
        assert no_match.new_jobs == []
        assert no_match.new_jobs_total == 0


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
            window=TrendWindow.months_3, keyword=None, city=None
        )
        assert all(item.skill != "Rust" for item in overview.emerging_skills)
        assert "Rust" not in overview.heatmap_skills
        # 新增岗位判定基于标准岗位出现（与技能事实无关），但核心技能不再含 Rust
        rust_job = next(
            (job for job in overview.new_jobs if job.name == "Rust 开发工程师"),
            None,
        )
        if rust_job is not None:
            assert "Rust" not in rust_job.core_skills


async def test_unverified_new_technology_is_shown_as_observation_candidate():
    async with async_session() as db:
        await seed_analysis_data(db)
        rows = (await db.execute(
            select(JobSkillFact).where(JobSkillFact.evidence_text == "Rust")
        )).scalars().all()
        for row in rows:
            row.verification_status = "unverified"
        raw_rows = (await db.execute(select(RawJobRecord))).scalars().all()
        for raw in raw_rows:
            raw.quality_status = "accepted"
        await db.commit()

        service = AnalysisService(db)
        service.MIN_VERIFIED_FACTS = 1
        overview = await service.overview(
            window=TrendWindow.months_3, keyword=None, city=None
        )

        rust = next(item for item in overview.emerging_skills if item.skill == "Rust")
        # Market evidence is now evaluated independently from the manual fact
        # review queue.  Repeated cross-company/source/period observations form
        # a strong first-seen signal even while individual facts await review.
        assert rust.stage == "新出现"
        assert rust.previous_count == 0
        assert rust.current_sources == 2
        assert rust.current_periods == 3
        assert rust.trend_score >= 75
        assert "数据集中首次出现" in rust.evidence_note
