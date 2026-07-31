"""标准岗位聚合、verified 过滤和 Top 技能候选测试。"""

import uuid

from sqlalchemy import func, select

from app.core.database import async_session
from app.models import (
    GraphEnrichmentCandidate,
    GraphSnapshot,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    StandardJob,
)
from app.services.graph_service import GraphService


class DisabledProvider:
    enabled = False
    provider_name = "disabled"
    model_name = "disabled"


async def test_aggregate_dual_sources_and_only_verified_facts_enter_graph():
    async with async_session() as db:
        python = Skill(
            name="Python", canonical_name="Python", canonical_key="python",
            category="programming_language", aliases=[],
        )
        redis = Skill(
            name="Redis", canonical_name="Redis", canonical_key="redis",
            category="database", aliases=[],
        )
        db.add_all([python, redis])
        await db.flush()
        raws = []
        for index, title in enumerate(
            ["高级 Python 后端开发工程师（双休）", "Python 后端开发工程师"],
            1,
        ):
            document = SourceDocument(
                source=f"来源{index}", url=f"https://example/{index}", title=title,
                content_fingerprint=f"{index:064d}", content_summary="Python Redis",
                source_meta={},
            )
            db.add(document)
            await db.flush()
            raw = RawJobRecord(
                source_document_id=document.id, title=title, company="A", jd_text="Python Redis",
                responsibilities="", requirements="", keywords="python",
                dedup_status="unique", normalized_data={},
                quality_status="accepted", quality_score=.9,
            )
            db.add(raw)
            await db.flush()
            raws.append(raw)
            db.add(JobSkillFact(
                raw_job_record_id=raw.id, skill_id=python.id, kind="required",
                importance=.9, frequency=1, confidence=.96, evidence_text="Python",
                verification_status="verified", extraction_method="rule", source_count=2,
            ))
        db.add(JobSkillFact(
            raw_job_record_id=raws[0].id, skill_id=redis.id, kind="preferred",
            importance=.6, frequency=1, confidence=.92, evidence_text="Redis",
            verification_status="unverified", extraction_method="rule", source_count=1,
        ))
        await db.commit()

        service = GraphService(db, llm_provider=DisabledProvider())
        assert await service.aggregate_standard_jobs() == 1
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="test-v1", snapshot_type="full",
            status="running",
        )
        db.add(snapshot)
        await db.flush()
        nodes, edges, fact_count = await service._build_payload(snapshot)
        assert fact_count == 1
        assert {row["properties"]["name"] for row in nodes["TechStack"]} == {"Python"}
        assert len(edges["REQUIRES_AREA"]) == 1
        assert len(edges["CONTAINS"][0]["properties"]["sourceIds"]) == 2
        assert await db.scalar(select(func.count(StandardJob.id))) == 1


async def test_top_candidate_is_saved_unverified_without_llm():
    async with async_session() as db:
        skill = Skill(
            name="Python", canonical_name="Python", canonical_key="python",
            category="programming_language", aliases=[],
        )
        db.add(skill)
        await db.flush()
        for index in (1, 2):
            document = SourceDocument(
                source=f"来源{index}", url=f"https://example/{index}", title="Python 工程师",
                content_fingerprint=f"{index:064d}", content_summary="Python",
                source_meta={},
            )
            db.add(document)
            await db.flush()
            raw = RawJobRecord(
                source_document_id=document.id, title="Python 工程师", jd_text="Python",
                responsibilities="", requirements="", keywords="python",
                dedup_status="unique", normalized_data={},
                quality_status="accepted", quality_score=.9,
            )
            db.add(raw)
            await db.flush()
            db.add(JobSkillFact(
                raw_job_record_id=raw.id, skill_id=skill.id, kind="required",
                importance=.9, frequency=1, confidence=.96, evidence_text="Python",
                verification_status="verified", extraction_method="rule", source_count=2,
            ))
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="test-v2", snapshot_type="full",
            status="running",
        )
        db.add(snapshot)
        await db.flush()
        service = GraphService(db, llm_provider=DisabledProvider())
        await service._prepare_top_candidates(snapshot.id, user_id=1)
        candidate = (await db.execute(select(GraphEnrichmentCandidate))).scalar_one()
        assert candidate.verification_status == "unverified"
        # Phase 3 does not load evidence until the LLM path is enabled, and
        # never falls back to direct fact-table prompt injection.
        assert candidate.evidence_source_ids == []
        assert candidate.candidate_data["reason"] == "llm_disabled"
