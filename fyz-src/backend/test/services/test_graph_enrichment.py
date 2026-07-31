"""L4/L5 图补全集成测试（使用 MockLLMProvider，不调用真实 DeepSeek）。"""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.database import async_session
from app.models import (
    AgentClaimCitation,
    AgentRun,
    EvidenceChunk,
    GraphEnrichmentCandidate,
    GraphSnapshot,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    StandardJob,
)
from app.providers import MockLLMProvider
from app.schemas.graph import GraphEnrichmentOutput, KnowledgePointOutput, TechPointOutput
from app.schemas.retrieval import RetrievedEvidence, RetrievalSearchResponse
from app.services.agent_grounding_service import (
    AgentGroundingService,
    AgentGroundingReport,
    ClaimGroundingResult,
    GroundedClaim,
)
from app.services.graph_service import GraphService


class _MockProvider:
    enabled = True
    provider_name = "mock"
    model_name = "mock-structured"

    def __init__(self, output: GraphEnrichmentOutput | None = None, error: Exception | None = None):
        self._llm = MockLLMProvider(output=output, error=error)

    async def generate_structured(self, *, response_schema, **_kwargs):
        return await self._llm.generate_structured(response_schema=response_schema)


class _MockRetriever:
    def __init__(
        self,
        items: list[RetrievedEvidence],
        *,
        error: Exception | None = None,
    ) -> None:
        self.items = items
        self.error = error

    async def search(self, payload, **_kwargs) -> RetrievalSearchResponse:
        if self.error:
            raise self.error
        return RetrievalSearchResponse(
            query=payload.query,
            index_version="phase3-test-index",
            backend="mock",
            items=self.items,
            latency_ms=1,
            truncated=False,
            warnings=[],
        )


def _make_output(tech_points: list[TechPointOutput]) -> GraphEnrichmentOutput:
    return GraphEnrichmentOutput(
        skill_name="Python",
        job_directions=["Python 后端开发工程师"],
        skill_area="Programming Language",
        tech_points=tech_points,
    )


async def _seed_python_skill(db) -> Skill:
    skill = Skill(
        name="Python", canonical_name="Python", canonical_key="python",
        category="programming_language", aliases=[],
    )
    db.add(skill)
    await db.flush()
    return skill


async def _seed_raw_evidence(
    db,
    skill: Skill,
) -> list[RetrievedEvidence]:
    standard_job = StandardJob(
        name="Python 后端开发工程师",
        canonical_key=f"python-backend-{uuid.uuid4()}",
        aliases=[],
        stack="backend",
        level="middle",
    )
    db.add(standard_job)
    await db.flush()
    items: list[RetrievedEvidence] = []
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
            standard_job_id=standard_job.id,
        )
        db.add(raw)
        await db.flush()
        fact = JobSkillFact(
            raw_job_record_id=raw.id, skill_id=skill.id, kind="required",
            importance=.9, frequency=1, confidence=.96,
            evidence_text=(
                "Python 类型注解 typing.Generic 异步编程 asyncio "
                "装饰器 @wraps"
            ),
            verification_status="verified", extraction_method="rule", source_count=2,
        )
        db.add(fact)
        await db.flush()
        evidence_id = f"phase3-evidence-{index}"
        chunk = EvidenceChunk(
            id=evidence_id,
            job_skill_fact_id=fact.id,
            source_document_id=document.id,
            raw_job_record_id=raw.id,
            standard_job_id=standard_job.id,
            skill_id=skill.id,
            chunk_text=fact.evidence_text,
            char_start=0,
            char_end=len(fact.evidence_text),
            source_platform=document.source,
            source_url=document.url,
            posted_at=None,
            quality_score=0.9,
            verification_status="human_approved",
            content_fingerprint=document.content_fingerprint,
        )
        db.add(chunk)
        items.append(
            RetrievedEvidence(
                evidence_id=evidence_id,
                job_skill_fact_id=fact.id,
                raw_job_record_id=raw.id,
                source_document_id=document.id,
                standard_job_id=standard_job.id,
                skill_id=skill.id,
                skill_name=skill.name,
                chunk_text=fact.evidence_text,
                char_start=0,
                char_end=len(fact.evidence_text),
                source_platform=document.source,
                source_url=document.url,
                posted_at=None,
                quality_score=0.9,
                verification_status="human_approved",
                near_duplicate_group_id=None,
                retrieval_score=0.9,
                lexical_score=0.9,
                vector_score=0.9,
                graph_score=1.0,
                index_version="phase3-test-index",
            )
        )
    return items


async def test_enrich_candidate_success_with_mock_llm():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        evidence = await _seed_raw_evidence(db, skill)
        await db.commit()

        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="test-v3", snapshot_type="full", status="running",
        )
        db.add(snapshot)
        await db.flush()

        output = _make_output([
            TechPointOutput(
                name="  类型注解  ",
                detail="使用类型注解提高代码可维护性",
                confidence=0.85,
                evidence_ids=[
                    evidence[0].evidence_id,
                    evidence[1].evidence_id,
                ],
                knowledge_points=[
                    KnowledgePointOutput(
                        name="typing.Generic",
                        description="泛型类与类型变量",
                        difficulty="medium",
                        confidence=0.80,
                        evidence_ids=[
                            evidence[0].evidence_id,
                            evidence[1].evidence_id,
                        ],
                    )
                ],
            )
        ])
        service = GraphService(
            db,
            llm_provider=_MockProvider(output=output),
            retrieval_service=_MockRetriever(evidence),
        )
        stats = await service._prepare_top_candidates(snapshot.id, user_id=1)

        candidate = (await db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.snapshot_id == snapshot.id
            )
        )).scalar_one()
        assert candidate.verification_status == "machine_validated"
        assert stats == {
            "candidates_total": 1,
            "candidates_machine_validated": 1,
            "candidates_failed": 0,
            "candidates_skipped": 0,
        }

        agent_run = (await db.execute(select(AgentRun).where(AgentRun.id == candidate.agent_run_id))).scalar_one()
        assert agent_run.status == "succeeded"
        assert agent_run.agent_type == "graph_enrichment"
        assert (
            agent_run.structured_output["retrieval"]["index_version"]
            == "phase3-test-index"
        )
        citations = list(
            (
                await db.execute(
                    select(AgentClaimCitation).where(
                        AgentClaimCitation.agent_run_id == agent_run.id
                    )
                )
            ).scalars()
        )
        assert len(citations) == 4
        assert {item.validation_status for item in citations} == {
            "machine_validated"
        }

        # Agent 输出已被规范化（去除首尾空格）
        validated = GraphEnrichmentOutput.model_validate(candidate.candidate_data)
        assert validated.tech_points[0].name == "类型注解"


async def test_enrich_candidate_failure_is_tracked():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        evidence = await _seed_raw_evidence(db, skill)
        await db.commit()

        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="test-v4", snapshot_type="full", status="running",
        )
        db.add(snapshot)
        await db.flush()

        service = GraphService(
            db,
            llm_provider=_MockProvider(
                error=RuntimeError("mock failure")
            ),
            retrieval_service=_MockRetriever(evidence),
        )
        stats = await service._prepare_top_candidates(snapshot.id, user_id=1)

        candidate = (await db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.snapshot_id == snapshot.id
            )
        )).scalar_one()
        assert candidate.verification_status == "unverified"
        assert candidate.candidate_data.get("reason") == "llm_failed"
        assert stats["candidates_failed"] == 1

        agent_run = (await db.execute(select(AgentRun).where(AgentRun.id == candidate.agent_run_id))).scalar_one()
        assert agent_run.status == "failed"
        assert agent_run.error_code == "RuntimeError"


async def test_single_skill_failure_does_not_break_sync():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        evidence = await _seed_raw_evidence(db, skill)
        await db.commit()

        service = GraphService(
            db,
            llm_provider=_MockProvider(error=RuntimeError("boom")),
            retrieval_service=_MockRetriever(evidence),
        )
        with patch.object(service, "_write_payload") as mock_write, \
             patch.object(service.graph, "counts", return_value={"nodes": 0, "edges": 0}):
            result = await service.sync(mode="incremental", enrich_top_skills=True, user_id=1)

        assert result["snapshot_id"]
        assert result["fact_count"] == 1
        mock_write.assert_called_once()
        snapshot = await db.get(GraphSnapshot, result["snapshot_id"])
        assert snapshot.status == "succeeded"
        enrichment = snapshot.metadata_json.get("enrichment", {})
        assert enrichment["candidates_total"] == 1
        assert enrichment["candidates_failed"] == 1
        assert enrichment["tech_points_written"] == 0


async def test_single_platform_retrieval_is_not_sent_to_agent():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        evidence = await _seed_raw_evidence(db, skill)
        same_platform = [
            item.model_copy(update={"source_platform": "平台A"})
            for item in evidence
        ]
        await db.commit()

        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="test-v5", snapshot_type="full", status="running",
        )
        db.add(snapshot)
        await db.flush()

        service = GraphService(
            db,
            llm_provider=_MockProvider(
                error=AssertionError("LLM should not be called")
            ),
            retrieval_service=_MockRetriever(same_platform),
        )
        stats = await service._prepare_top_candidates(snapshot.id, user_id=1)

        assert stats["candidates_machine_validated"] == 0
        assert stats["candidates_skipped"] == 1
        candidate = (await db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.snapshot_id == snapshot.id
            )
        )).scalar_one()
        assert candidate.verification_status == "unverified"
        assert candidate.candidate_data["reason"] == "insufficient_evidence"
        assert candidate.evidence_source_ids == [
            item.evidence_id for item in same_platform
        ]


async def test_retrieval_failure_degrades_without_calling_agent():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        evidence = await _seed_raw_evidence(db, skill)
        await db.commit()
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()),
            version="test-retrieval-failure",
            snapshot_type="full",
            status="running",
        )
        db.add(snapshot)
        await db.flush()

        service = GraphService(
            db,
            llm_provider=_MockProvider(
                error=AssertionError("LLM should not be called")
            ),
            retrieval_service=_MockRetriever(
                evidence,
                error=RuntimeError("index unavailable"),
            ),
        )
        stats = await service._prepare_top_candidates(
            snapshot.id,
            user_id=1,
        )

        candidate = (
            await db.execute(
                select(GraphEnrichmentCandidate).where(
                    GraphEnrichmentCandidate.snapshot_id == snapshot.id
                )
            )
        ).scalar_one()
        assert stats["candidates_skipped"] == 1
        assert candidate.candidate_data == {
            "reason": "retrieval_unavailable",
            "skill_name": "Python",
            "error_code": "RuntimeError",
        }
        assert candidate.agent_run_id is None


async def test_grounding_gate_rejects_invalid_citations_and_evidence():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        evidence = await _seed_raw_evidence(db, skill)
        run = AgentRun(
            id=str(uuid.uuid4()),
            agent_type="graph_enrichment",
            provider="mock",
            model="mock",
            prompt_version="phase3-test",
            input_summary="grounding validation",
            status="running",
            retry_count=0,
            created_by=1,
        )
        db.add(run)
        await db.commit()

        service = AgentGroundingService(db)
        cases = [
            (
                "unknown",
                evidence,
                ("missing-evidence", evidence[0].evidence_id),
                "unknown_evidence_id",
                "Python",
            ),
            (
                "single-platform",
                [
                    item.model_copy(
                        update={"source_platform": "same-platform"}
                    )
                    for item in evidence
                ],
                tuple(item.evidence_id for item in evidence),
                "insufficient_independent_sources",
                "Python",
            ),
            (
                "low-quality",
                [
                    evidence[0].model_copy(
                        update={"quality_score": 0.4}
                    ),
                    evidence[1],
                ],
                tuple(item.evidence_id for item in evidence),
                "low_quality_evidence",
                "Python",
            ),
            (
                "stale",
                [
                    item.model_copy(
                        update={"posted_at": datetime(2020, 1, 1)}
                    )
                    for item in evidence
                ],
                tuple(item.evidence_id for item in evidence),
                "stale_evidence",
                "Python",
            ),
            (
                "semantic",
                evidence,
                tuple(item.evidence_id for item in evidence),
                "semantic_mismatch",
                "Kubernetes 集群网络策略",
            ),
        ]

        for case_id, case_evidence, ids, reason, claim_text in cases:
            report = await service.validate_and_persist(
                agent_run_id=run.id,
                claims=[
                    GroundedClaim(
                        claim_id=case_id,
                        claim_type="tech_point",
                        claim_text=claim_text,
                        anchor_text=claim_text,
                        evidence_ids=ids,
                    )
                ],
                evidence=case_evidence,
                minimum_sources=2,
            )
            assert report.accepted_count == 0
            assert reason in report.results[0].reasons

        citations = list(
            (
                await db.execute(
                    select(AgentClaimCitation).where(
                        AgentClaimCitation.agent_run_id == run.id
                    )
                )
            ).scalars()
        )
        assert citations == []


def _grounding_report(
    *,
    accepted: set[str],
    rejected: set[str] | None = None,
) -> AgentGroundingReport:
    results = [
        ClaimGroundingResult(
            claim_id=claim_id,
            accepted=True,
            grounding_score=0.9,
            evidence_ids=("evidence-a", "evidence-b"),
        )
        for claim_id in sorted(accepted)
    ]
    results.extend(
        ClaimGroundingResult(
            claim_id=claim_id,
            accepted=False,
            grounding_score=0,
            evidence_ids=("unknown",),
            reasons=("unknown_evidence_id",),
        )
        for claim_id in sorted(rejected or set())
    )
    return AgentGroundingReport(results=results)


def test_filter_grounded_completion_enforces_confidence_boundary():
    output = GraphEnrichmentOutput(
        skill_name="Python",
        job_directions=["Python 后端开发工程师"],
        skill_area="Programming Language",
        tech_points=[
            TechPointOutput(
                name="confidence 0.75", detail="刚好通过", confidence=0.75,
                evidence_ids=["evidence-a", "evidence-b"],
            ),
            TechPointOutput(
                name="confidence 0.74", detail="刚好不过", confidence=0.74,
                evidence_ids=["evidence-a", "evidence-b"],
            ),
        ],
    )
    filtered, confidence = GraphService._filter_grounded_completion(
        output,
        _grounding_report(accepted={"tech:0", "tech:1"}),
    )
    assert [p.name for p in filtered.tech_points] == ["confidence 0.75"]
    assert confidence == 0.75


def test_graph_schema_reads_legacy_source_ids_but_emits_evidence_ids():
    point = TechPointOutput.model_validate(
        {
            "name": "类型注解",
            "detail": "typing",
            "confidence": 0.85,
            "source_ids": ["legacy-a", "legacy-b"],
        }
    )
    assert point.evidence_ids == ["legacy-a", "legacy-b"]
    assert point.model_dump()["evidence_ids"] == ["legacy-a", "legacy-b"]


def test_filter_grounded_completion_knowledge_point_boundaries():
    output = GraphEnrichmentOutput(
        skill_name="Python",
        job_directions=["Python 后端开发工程师"],
        skill_area="Programming Language",
        tech_points=[
            TechPointOutput(
                name="有效技术点",
                detail="说明",
                confidence=0.85,
                evidence_ids=["evidence-a", "evidence-b"],
                knowledge_points=[
                    KnowledgePointOutput(
                        name="有效知识点", description="OK", difficulty="easy",
                        confidence=0.75,
                        evidence_ids=["evidence-a", "evidence-b"],
                    ),
                    KnowledgePointOutput(
                        name="低置信度知识点", description="filtered", difficulty="easy",
                        confidence=0.74,
                        evidence_ids=["evidence-a", "evidence-b"],
                    ),
                    KnowledgePointOutput(
                        name="未知来源知识点", description="filtered", difficulty="easy",
                        confidence=0.85,
                        evidence_ids=["evidence-a", "unknown"],
                    ),
                ],
            )
        ],
    )
    filtered, _ = GraphService._filter_grounded_completion(
        output,
        _grounding_report(
            accepted={
                "tech:0",
                "knowledge:0:0",
                "knowledge:0:1",
            },
            rejected={"knowledge:0:2"},
        ),
    )
    assert len(filtered.tech_points) == 1
    assert [k.name for k in filtered.tech_points[0].knowledge_points] == ["有效知识点"]


async def test_append_verified_deep_nodes_counts():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="test-v6", snapshot_type="full", status="running",
        )
        db.add(snapshot)
        await db.flush()

        candidate = GraphEnrichmentCandidate(
            snapshot_id=snapshot.id,
            skill_id=skill.id,
            verification_status="verified",
            evidence_source_ids=["evidence-a", "evidence-b"],
            candidate_data=_make_output([
                TechPointOutput(
                    name="装饰器", detail="函数装饰器", confidence=0.85,
                    evidence_ids=["evidence-a", "evidence-b"],
                    knowledge_points=[
                        KnowledgePointOutput(
                            name="@wraps", description="保留元数据", difficulty="easy",
                            confidence=0.80,
                            evidence_ids=["evidence-a", "evidence-b"],
                        ),
                        KnowledgePointOutput(
                            name="低置信度", description="被过滤", difficulty="easy",
                            confidence=0.70,
                            evidence_ids=["evidence-a", "evidence-b"],
                        ),
                    ],
                )
            ]).model_dump(mode="json"),
            confidence=0.85,
        )
        db.add(candidate)
        await db.commit()

        service = GraphService(db, llm_provider=_MockProvider())
        nodes = {"TechPoint": [], "KnowledgePoint": []}
        edges = {"REFINES_TO": [], "HAS_KNOWLEDGE": []}
        tech_count, knowledge_count = await service._append_verified_deep_nodes(
            snapshot.id, nodes, edges, {skill.id: skill}
        )

        assert tech_count == 1
        assert knowledge_count == 1
        assert len(nodes["TechPoint"]) == 1
        assert len(nodes["KnowledgePoint"]) == 1
        assert len(edges["REFINES_TO"]) == 1
        assert len(edges["HAS_KNOWLEDGE"]) == 1
