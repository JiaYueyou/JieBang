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
    User,
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
                "装饰器 @wraps Flask 路由 request context Jinja2 "
                "Flask-SQLAlchemy ORM Flask-Migrate Alembic 数据库迁移"
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
                name="  Flask  ",
                category="framework",
                detail="Flask 是 Python 轻量级 Web 框架，用于构建接口与 Web 服务",
                confidence=0.85,
                evidence_ids=[
                    evidence[0].evidence_id,
                    evidence[1].evidence_id,
                ],
                knowledge_points=[
                    KnowledgePointOutput(
                        name="Flask 请求上下文与扩展生态",
                        description=(
                            "请求上下文隔离单次请求数据；项目通常结合 Jinja2、"
                            "Flask-SQLAlchemy 和 Flask-Migrate 完成模板、ORM 与迁移。"
                        ),
                        difficulty="medium",
                        confidence=0.80,
                        evidence_ids=[
                            evidence[0].evidence_id,
                            evidence[1].evidence_id,
                        ],
                        core_stack=["WSGI", "request context", "Jinja2"],
                        common_solutions=[
                            {
                                "name": "Flask-SQLAlchemy",
                                "purpose": "提供 ORM 数据模型和数据库访问能力",
                            },
                            {
                                "name": "Flask-Migrate",
                                "purpose": "基于 Alembic 管理数据库结构迁移",
                            },
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
        point = validated.tech_points[0]
        assert point.name == "Flask"
        assert point.category == "framework"
        assert point.knowledge_points[0].core_stack == ["WSGI", "request context", "Jinja2"]
        assert [item.name for item in point.knowledge_points[0].common_solutions] == [
            "Flask-SQLAlchemy", "Flask-Migrate",
        ]


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


async def test_enrich_candidate_timeout_is_retryable_and_explicit():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        evidence = await _seed_raw_evidence(db, skill)
        await db.commit()
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="test-timeout", snapshot_type="full", status="running",
        )
        db.add(snapshot)
        await db.flush()
        service = GraphService(
            db,
            llm_provider=_MockProvider(error=RuntimeError("DeepSeek response timed out after 120 seconds")),
            retrieval_service=_MockRetriever(evidence),
        )

        stats = await service._prepare_top_candidates(snapshot.id, user_id=1)
        candidate = (await db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.snapshot_id == snapshot.id
            )
        )).scalar_one()

        assert stats["candidates_failed"] == 1
        assert candidate.candidate_data["reason"] == "llm_timeout"
        assert candidate.candidate_data["retryable"] is True


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
            review_status="approved",
            publication_status="approved",
            evidence_source_ids=["evidence-a", "evidence-b"],
            candidate_data=_make_output([
                TechPointOutput(
                    name="Flask", category="framework",
                    detail="Python 轻量级 Web 框架", confidence=0.85,
                    evidence_ids=["evidence-a", "evidence-b"],
                    knowledge_points=[
                        KnowledgePointOutput(
                            name="请求上下文", description="隔离单次请求数据", difficulty="medium",
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
        tech_count, knowledge_count, candidate_ids, superseded_ids = await service._append_verified_deep_nodes(
            snapshot.id, nodes, edges, {skill.id: skill}
        )

        assert tech_count == 1
        assert knowledge_count == 1
        # 即使中间进度提交，也不能在 Neo4j 写入成功前提前标记 published。
        await db.commit()
        await db.refresh(candidate)
        assert candidate.publication_status == "approved"
        assert candidate_ids == [candidate.id]
        assert superseded_ids == []
        assert len(nodes["TechPoint"]) == 1
        assert len(nodes["KnowledgePoint"]) == 1
        assert len(edges["REFINES_TO"]) == 1
        assert len(edges["HAS_KNOWLEDGE"]) == 1


async def test_machine_validated_candidate_requires_review_before_publication():
    async with async_session() as db:
        user = User(username="graph-review-admin", password_hash="x", role="admin")
        skill = Skill(
            name="Python", canonical_name="Python", canonical_key="python-review",
            category="programming_language", aliases=[],
        )
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="review-v1", snapshot_type="incremental", status="succeeded",
        )
        db.add_all([user, skill, snapshot])
        await db.flush()
        candidate = GraphEnrichmentCandidate(
            snapshot_id=snapshot.id, skill_id=skill.id,
            candidate_data=_make_output([]).model_dump(mode="json"),
            evidence_source_ids=[1, 2], confidence=.88,
            verification_status="machine_validated", machine_validation_status="passed",
            review_status="pending", publication_status="draft",
        )
        db.add(candidate)
        await db.commit()
        service = GraphService(db, llm_provider=_MockProvider())
        reviewed = await service.review_enrichment_candidate(
            candidate.id, action="approve", note="证据充分",
            lock_version=0, user_id=user.id,
        )
        assert reviewed["review_status"] == "approved"
        assert reviewed["publication_status"] == "approved"
        assert reviewed["lock_version"] == 1
        assert reviewed["evidence_source_ids"] == ["1", "2"]
        assert await service.prepare_enrichment_publication([candidate.id]) == 1


async def test_machine_failed_candidates_are_rejected_with_automatic_reasons():
    async with async_session() as db:
        user = User(username="graph-auto-reject", password_hash="x", role="admin")
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="reject-v1",
            snapshot_type="incremental", status="succeeded",
        )
        skills = [
            Skill(
                name=name, canonical_name=name, canonical_key=f"reject-{index}",
                category="tool", aliases=[],
            )
            for index, name in enumerate(("PyTorch", "Git", "Pandas"), 1)
        ]
        db.add_all([user, snapshot, *skills])
        await db.flush()
        failed = GraphEnrichmentCandidate(
            snapshot_id=snapshot.id, skill_id=skills[0].id,
            candidate_data={
                "reason": "insufficient_evidence", "sources": ["智联招聘"]
            },
            evidence_source_ids=["e1"], confidence=0.4,
            machine_validation_status="insufficient_evidence",
        )
        passed = GraphEnrichmentCandidate(
            snapshot_id=snapshot.id, skill_id=skills[1].id,
            candidate_data=_make_output([]).model_dump(mode="json"),
            evidence_source_ids=["e1", "e2"], confidence=0.9,
            machine_validation_status="passed",
        )
        still_running = GraphEnrichmentCandidate(
            snapshot_id=snapshot.id, skill_id=skills[2].id,
            candidate_data={}, evidence_source_ids=[], confidence=0,
            machine_validation_status="pending",
        )
        db.add_all([failed, passed, still_running])
        await db.commit()

        service = GraphService(db, llm_provider=_MockProvider())
        rejected_ids = await service.reject_machine_failed_candidates(user_id=user.id)

        assert rejected_ids == [failed.id]
        await db.refresh(failed)
        await db.refresh(passed)
        await db.refresh(still_running)
        assert failed.review_status == "rejected"
        assert failed.publication_status == "rejected"
        assert failed.review_note == (
            "机器审核未通过：独立证据来源不足，未达到双来源门槛（当前来源：智联招聘）"
        )
        assert failed.reviewed_by == user.id
        assert passed.review_status == "pending"
        assert still_running.review_status == "pending"


async def test_single_machine_failed_rejection_does_not_require_manual_note():
    async with async_session() as db:
        user = User(username="graph-auto-note", password_hash="x", role="admin")
        skill = Skill(
            name="Git", canonical_name="Git", canonical_key="git-auto-note",
            category="tool", aliases=[],
        )
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="reject-v2",
            snapshot_type="incremental", status="succeeded",
        )
        db.add_all([user, skill, snapshot])
        await db.flush()
        candidate = GraphEnrichmentCandidate(
            snapshot_id=snapshot.id, skill_id=skill.id,
            candidate_data={
                "reason": "insufficient_grounding",
                "machine_validation": {"rejected_claim_count": 2},
            },
            evidence_source_ids=["e1", "e2"], confidence=0.2,
            machine_validation_status="failed",
        )
        db.add(candidate)
        await db.commit()

        reviewed = await GraphService(
            db, llm_provider=_MockProvider()
        ).review_enrichment_candidate(
            candidate.id, action="reject", note=None,
            lock_version=0, user_id=user.id,
        )

        assert reviewed["review_note"] == (
            "机器审核未通过：生成内容未通过证据引用校验，2 条技术陈述未被证据支持"
        )


def test_dedupe_by_name_keeps_first_and_ignores_blank():
    points = [
        TechPointOutput(name="Spring Boot", detail="a", confidence=0.9, evidence_ids=["e1", "e2"]),
        TechPointOutput(name="spring boot", detail="b", confidence=0.8, evidence_ids=["e3", "e4"]),
        TechPointOutput(name="", detail="blank", confidence=0.9, evidence_ids=["e5", "e6"]),
        TechPointOutput(name="MyBatis", detail="c", confidence=0.85, evidence_ids=["e7", "e8"]),
    ]
    deduped = GraphService._dedupe_by_name(points)
    assert [p.name for p in deduped] == ["Spring Boot", "MyBatis"]
    assert deduped[0].detail == "a"  # 保留首次出现


def test_filter_grounded_completion_dedupes_same_name_points():
    output = GraphEnrichmentOutput(
        skill_name="Java",
        job_directions=["Java 后端开发工程师"],
        skill_area="Programming Language",
        tech_points=[
            TechPointOutput(
                name="MyBatis", detail="ORM 框架", confidence=0.85,
                evidence_ids=["evidence-a", "evidence-b"],
            ),
            TechPointOutput(
                name="mybatis", detail="重复技术点", confidence=0.82,
                evidence_ids=["evidence-a", "evidence-b"],
            ),
            TechPointOutput(
                name="Spring Boot", detail="微服务框架", confidence=0.88,
                evidence_ids=["evidence-a", "evidence-b"],
            ),
        ],
    )
    filtered, _ = GraphService._filter_grounded_completion(
        output,
        _grounding_report(accepted={"tech:0", "tech:1", "tech:2"}),
    )
    assert [p.name for p in filtered.tech_points] == ["MyBatis", "Spring Boot"]


async def test_append_verified_deep_nodes_dedupes_same_name_points():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="dedup-v1", snapshot_type="incremental", status="running",
        )
        db.add(snapshot)
        await db.flush()
        candidate = GraphEnrichmentCandidate(
            snapshot_id=snapshot.id,
            skill_id=skill.id,
            verification_status="verified",
            review_status="approved",
            publication_status="approved",
            evidence_source_ids=["evidence-a", "evidence-b"],
            candidate_data=_make_output([
                TechPointOutput(
                    name="Flask", category="framework",
                    detail="Python 轻量级 Web 框架", confidence=0.85,
                    evidence_ids=["evidence-a", "evidence-b"],
                    knowledge_points=[
                        KnowledgePointOutput(
                            name="请求上下文", description="隔离单次请求数据", difficulty="medium",
                            confidence=0.80,
                            evidence_ids=["evidence-a", "evidence-b"],
                        ),
                        KnowledgePointOutput(
                            name="请求上下文", description="重复知识点", difficulty="medium",
                            confidence=0.78,
                            evidence_ids=["evidence-a", "evidence-b"],
                        ),
                    ],
                ),
                TechPointOutput(
                    name="flask", category="framework",
                    detail="重复技术点", confidence=0.80,
                    evidence_ids=["evidence-a", "evidence-b"],
                ),
            ]).model_dump(mode="json"),
            confidence=0.85,
        )
        db.add(candidate)
        await db.commit()

        service = GraphService(db, llm_provider=_MockProvider())
        nodes = {"TechPoint": [], "KnowledgePoint": []}
        edges = {"REFINES_TO": [], "HAS_KNOWLEDGE": []}
        tech_count, knowledge_count, _, _ = await service._append_verified_deep_nodes(
            snapshot.id, nodes, edges
        )
        assert tech_count == 1  # Flask / flask 同名去重
        assert knowledge_count == 1  # 请求上下文 同名去重
        point_names = [node["properties"]["name"] for node in nodes["TechPoint"]]
        assert point_names == ["Flask"]
        knowledge_names = [
            node["properties"]["name"] for node in nodes["KnowledgePoint"]
        ]
        assert knowledge_names == ["请求上下文"]
        assert len(edges["REFINES_TO"]) == 1
        assert len(edges["HAS_KNOWLEDGE"]) == 1


async def test_append_verified_deep_nodes_supersedes_older_candidate_for_same_skill():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        old_snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="version-old",
            snapshot_type="incremental", status="succeeded",
        )
        new_snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="version-new",
            snapshot_type="incremental", status="running",
        )
        db.add_all([old_snapshot, new_snapshot])
        await db.flush()

        def candidate(snapshot_id: str, point_name: str) -> GraphEnrichmentCandidate:
            return GraphEnrichmentCandidate(
                snapshot_id=snapshot_id, skill_id=skill.id,
                verification_status="verified", review_status="approved",
                publication_status="approved",
                evidence_source_ids=["e1", "e2"], confidence=0.9,
                candidate_data=_make_output([
                    TechPointOutput(
                        name=point_name, detail=point_name, confidence=0.9,
                        evidence_ids=["e1", "e2"],
                    )
                ]).model_dump(mode="json"),
            )

        older = candidate(old_snapshot.id, "旧版技术点")
        newer = candidate(new_snapshot.id, "新版技术点")
        db.add(older)
        await db.flush()
        db.add(newer)
        await db.commit()

        nodes = {"TechPoint": [], "KnowledgePoint": []}
        edges = {"REFINES_TO": [], "HAS_KNOWLEDGE": []}
        _, _, published_ids, superseded_ids = await GraphService(
            db, llm_provider=_MockProvider()
        )._append_verified_deep_nodes(new_snapshot.id, nodes, edges)

        assert published_ids == [newer.id]
        assert superseded_ids == [older.id]
        assert [row["properties"]["name"] for row in nodes["TechPoint"]] == [
            "新版技术点"
        ]


async def test_append_verified_deep_nodes_merges_same_name_across_skills():
    """跨技能候选生成同名 TechPoint 时合并为同一节点（多 skill 通过 REFINES_TO 共享）。

    这是"3 个 mybatis / 2 个 spring boot"重复的根治验证：id 基于名称 hash，
    不同 skill 的同名技术点 MERGE 到同一节点。
    """
    async with async_session() as db:
        skill_a = await _seed_python_skill(db)
        java = Skill(
            name="Java", canonical_name="Java", canonical_key="java-merge-test",
            category="programming_language", aliases=[],
        )
        db.add(java)
        await db.flush()
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="merge-v1",
            snapshot_type="incremental", status="running",
        )
        db.add(snapshot)
        await db.flush()

        def make_candidate(skill_id: int, point_name: str) -> GraphEnrichmentCandidate:
            return GraphEnrichmentCandidate(
                snapshot_id=snapshot.id,
                skill_id=skill_id,
                verification_status="verified",
                review_status="approved",
                publication_status="approved",
                evidence_source_ids=["evidence-a", "evidence-b"],
                candidate_data=_make_output([
                    TechPointOutput(
                        name=point_name, category="framework",
                        detail="持久层框架", confidence=0.85,
                        evidence_ids=["evidence-a", "evidence-b"],
                    )
                ]).model_dump(mode="json"),
                confidence=0.85,
            )

        db.add(make_candidate(skill_a.id, "MyBatis"))
        db.add(make_candidate(java.id, "MyBatis"))
        await db.commit()

        service = GraphService(db, llm_provider=_MockProvider())
        nodes = {"TechPoint": [], "KnowledgePoint": []}
        edges = {"REFINES_TO": [], "HAS_KNOWLEDGE": []}
        tech_count, _, _, _ = await service._append_verified_deep_nodes(
            snapshot.id, nodes, edges
        )
        # 两个候选生成同 key 技术点 → 全局收集合并为 1 个唯一节点
        assert tech_count == 1
        assert len({node["id"] for node in nodes["TechPoint"]}) == 1
        assert nodes["TechPoint"][0]["properties"]["name"] == "MyBatis"
        # 两个 skill 的 REFINES_TO 指向同一节点（多父共享）
        assert len(edges["REFINES_TO"]) == 2
        sources = {edge["source"] for edge in edges["REFINES_TO"]}
        assert sources == {f"skill:{skill_a.id}", f"skill:{java.id}"}
        assert len({edge["target"] for edge in edges["REFINES_TO"]}) == 1


def test_name_key_is_deterministic_and_case_insensitive():
    assert GraphService._name_key("Spring Boot") == GraphService._name_key("spring boot")
    assert GraphService._name_key("MyBatis").startswith("point") is False
    assert len(GraphService._name_key("MyBatis")) == 12
    assert GraphService._name_key("") == GraphService._name_key("  ")


def test_normalize_name_key_merges_suffix_variants():
    """'MyBatis' 与 'MyBatis持久层框架' 归一为同一 key（L4 变体合并）。"""
    assert GraphService._normalize_name_key(
        "MyBatis", level="tech_point"
    ) == GraphService._normalize_name_key("MyBatis持久层框架", level="tech_point")
    assert GraphService._normalize_name_key(
        "MySQL", level="tech_point"
    ) == GraphService._normalize_name_key("MySQL 数据库开发与优化", level="tech_point")
    assert GraphService._normalize_name_key(
        "Python", level="tech_point"
    ) == GraphService._normalize_name_key("Python 后端与 Web 开发", level="tech_point")
    assert GraphService._normalize_name_key(
        "Redis", level="tech_point"
    ) == GraphService._normalize_name_key("Redis 中间件使用", level="tech_point")


def test_normalize_name_key_preserves_concept_phrases_for_l5():
    """L5 概念短语不误剥（仅剥课程式后缀）。"""
    l5_key = GraphService._normalize_name_key("Git 三区模型", level="knowledge_point")
    assert l5_key != GraphService._normalize_name_key("Git", level="knowledge_point")
    assert GraphService._normalize_name_key(
        "请求上下文", level="knowledge_point"
    ) == GraphService._normalize_name_key("请求上下文", level="knowledge_point")
    # 课程式后缀在 L5 可剥
    assert GraphService._normalize_name_key(
        "MyBatis 入门", level="knowledge_point"
    ) == GraphService._normalize_name_key("MyBatis", level="knowledge_point")


def test_normalize_name_key_guard_never_empties():
    """守卫：纯后缀/过短名称不剥成空，key 仍确定。"""
    for name in ("框架", "开发", "ab", "A"):
        key = GraphService._normalize_name_key(name, level="tech_point")
        assert len(key) == 12
    assert GraphService._normalize_name_key(
        "框架", level="tech_point"
    ) == GraphService._normalize_name_key("框架", level="tech_point")


async def test_append_verified_deep_nodes_merges_suffix_variant_across_skills():
    """跨技能候选生成"MyBatis"与"MyBatis持久层框架"变体时合并为同一节点。

    这是用户报告的"MyBatis 与 MyBatis持久层框架 同时存在"的根治验证：
    归一化 key 剥离修饰后缀后两者同 key → MERGE 到同一节点。
    """
    async with async_session() as db:
        skill_a = await _seed_python_skill(db)
        java = Skill(
            name="Java", canonical_name="Java", canonical_key="java-variant-test",
            category="programming_language", aliases=[],
        )
        db.add(java)
        await db.flush()
        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="variant-v1",
            snapshot_type="incremental", status="running",
        )
        db.add(snapshot)
        await db.flush()

        def make_candidate(skill_id: int, point_name: str) -> GraphEnrichmentCandidate:
            return GraphEnrichmentCandidate(
                snapshot_id=snapshot.id,
                skill_id=skill_id,
                verification_status="verified",
                review_status="approved",
                publication_status="approved",
                evidence_source_ids=["evidence-a", "evidence-b"],
                candidate_data=_make_output([
                    TechPointOutput(
                        name=point_name, category="framework",
                        detail="持久层 ORM 框架", confidence=0.85,
                        evidence_ids=["evidence-a", "evidence-b"],
                    )
                ]).model_dump(mode="json"),
                confidence=0.85,
            )

        db.add(make_candidate(skill_a.id, "MyBatis"))
        db.add(make_candidate(java.id, "MyBatis持久层框架"))
        await db.commit()

        service = GraphService(db, llm_provider=_MockProvider())
        nodes = {"TechPoint": [], "KnowledgePoint": []}
        edges = {"REFINES_TO": [], "HAS_KNOWLEDGE": []}
        tech_count, _, _, _ = await service._append_verified_deep_nodes(
            snapshot.id, nodes, edges
        )
        # 变体名称归一为同一 key → 全局收集只生成 1 个唯一节点，两个 skill 共享
        assert tech_count == 1
        assert len({node["id"] for node in nodes["TechPoint"]}) == 1
        assert len(edges["REFINES_TO"]) == 2
