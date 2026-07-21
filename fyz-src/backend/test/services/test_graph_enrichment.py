"""L4/L5 图补全集成测试（使用 MockLLMProvider，不调用真实 DeepSeek）。"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.database import async_session
from app.models import (
    AgentRun,
    GraphEnrichmentCandidate,
    GraphSnapshot,
    JobPosting,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
)
from app.providers import MockLLMProvider
from app.schemas.graph import GraphEnrichmentOutput, KnowledgePointOutput, TechPointOutput
from app.services.graph_service import GraphService


class _MockProvider:
    enabled = True
    provider_name = "mock"
    model_name = "mock-structured"

    def __init__(self, output: GraphEnrichmentOutput | None = None, error: Exception | None = None):
        self._llm = MockLLMProvider(output=output, error=error)

    async def generate_structured(self, *, response_schema, **_kwargs):
        return await self._llm.generate_structured(response_schema=response_schema)


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


async def _seed_raw_evidence(db, skill: Skill) -> None:
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
        )
        db.add(raw)
        await db.flush()
        db.add(JobSkillFact(
            raw_job_record_id=raw.id, skill_id=skill.id, kind="required",
            importance=.9, frequency=1, confidence=.96, evidence_text="Python",
            verification_status="verified", extraction_method="rule", source_count=2,
        ))


async def _seed_internal_evidence(db, skill: Skill) -> None:
    job = JobPosting(
        title="Python 后端开发工程师", company="内部公司", department="技术部", jd_text="Python",
        responsibilities=[], requirements=[], status="published", created_by=1,
    )
    db.add(job)
    await db.flush()
    db.add(JobSkillFact(
        job_id=job.id, skill_id=skill.id, kind="required",
        importance=.9, frequency=1, confidence=.96, evidence_text="Python",
        verification_status="verified", extraction_method="rule", source_count=1,
    ))


async def test_enrich_candidate_success_with_mock_llm():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        await _seed_raw_evidence(db, skill)
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
                source_ids=[1, 2],
                knowledge_points=[
                    KnowledgePointOutput(
                        name="typing.Generic",
                        description="泛型类与类型变量",
                        difficulty="medium",
                        confidence=0.80,
                        source_ids=[1, 2],
                    )
                ],
            )
        ])
        service = GraphService(db, llm_provider=_MockProvider(output=output))
        stats = await service._prepare_top_candidates(snapshot.id, user_id=1)

        candidate = (await db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.snapshot_id == snapshot.id
            )
        )).scalar_one()
        assert candidate.verification_status == "verified"
        assert stats == {
            "candidates_total": 1,
            "candidates_verified": 1,
            "candidates_failed": 0,
            "candidates_skipped": 0,
        }

        agent_run = (await db.execute(select(AgentRun).where(AgentRun.id == candidate.agent_run_id))).scalar_one()
        assert agent_run.status == "succeeded"
        assert agent_run.agent_type == "graph_enrichment"

        # Agent 输出已被规范化（去除首尾空格）
        validated = GraphEnrichmentOutput.model_validate(candidate.candidate_data)
        assert validated.tech_points[0].name == "类型注解"


async def test_enrich_candidate_failure_is_tracked():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        await _seed_raw_evidence(db, skill)
        await db.commit()

        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="test-v4", snapshot_type="full", status="running",
        )
        db.add(snapshot)
        await db.flush()

        service = GraphService(db, llm_provider=_MockProvider(error=RuntimeError("mock failure")))
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
        await _seed_raw_evidence(db, skill)
        await db.commit()

        service = GraphService(db, llm_provider=_MockProvider(error=RuntimeError("boom")))
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


async def test_internal_evidence_is_used_for_enrichment():
    async with async_session() as db:
        skill = await _seed_python_skill(db)
        # Only one raw source and one internal source => still 2 platforms, should enrich.
        document = SourceDocument(
            source="平台A", url="https://example/1", title="Python 工程师",
            content_fingerprint=f"{1:064d}", content_summary="Python", source_meta={},
        )
        db.add(document)
        await db.flush()
        raw = RawJobRecord(
            source_document_id=document.id, title="Python 工程师", jd_text="Python",
            responsibilities="", requirements="", keywords="python",
            dedup_status="unique", normalized_data={},
        )
        db.add(raw)
        await db.flush()
        db.add(JobSkillFact(
            raw_job_record_id=raw.id, skill_id=skill.id, kind="required",
            importance=.9, frequency=1, confidence=.96, evidence_text="Python",
            verification_status="verified", extraction_method="rule", source_count=1,
        ))
        await _seed_internal_evidence(db, skill)
        await db.commit()

        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()), version="test-v5", snapshot_type="full", status="running",
        )
        db.add(snapshot)
        await db.flush()

        output = _make_output([
            TechPointOutput(
                name="异步编程", detail="使用 asyncio 编写并发代码",
                confidence=0.85, source_ids=[1, 10_000_001],
            )
        ])
        service = GraphService(db, llm_provider=_MockProvider(output=output))
        stats = await service._prepare_top_candidates(snapshot.id, user_id=1)

        assert stats["candidates_verified"] == 1
        candidate = (await db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.snapshot_id == snapshot.id
            )
        )).scalar_one()
        # Should contain both the raw source_id and the synthetic internal source_id.
        assert 1 in candidate.evidence_source_ids
        assert 10_000_001 in candidate.evidence_source_ids


def test_filter_verified_completion_boundary():
    output = GraphEnrichmentOutput(
        skill_name="Python",
        job_directions=["Python 后端开发工程师"],
        skill_area="Programming Language",
        tech_points=[
            TechPointOutput(
                name="confidence 0.75", detail="刚好通过", confidence=0.75,
                source_ids=[1, 2],
            ),
            TechPointOutput(
                name="confidence 0.74", detail="刚好不过", confidence=0.74,
                source_ids=[1, 2],
            ),
            TechPointOutput(
                name="single platform", detail="同一平台", confidence=0.85,
                source_ids=[1, 3],
            ),
            TechPointOutput(
                name="unknown source", detail="未知 source_id", confidence=0.85,
                source_ids=[1, 999],
            ),
        ],
    )
    evidence = [
        {"source_id": 1, "source": "平台A", "text": "证据1"},
        {"source_id": 2, "source": "平台B", "text": "证据2"},
        {"source_id": 3, "source": "平台A", "text": "证据3"},
    ]

    filtered, confidence = GraphService._filter_verified_completion(output, evidence)
    assert [p.name for p in filtered.tech_points] == ["confidence 0.75"]
    assert confidence == 0.75


def test_filter_verified_completion_defensive_source_id_parsing():
    """验证 _filter_verified_completion 能防御非整数 source_id。"""
    output = GraphEnrichmentOutput(
        skill_name="Python",
        job_directions=["Python 后端开发工程师"],
        skill_area="Programming Language",
        tech_points=[
            TechPointOutput(
                name="valid", detail="ok", confidence=0.85, source_ids=[1, 2],
            ),
        ],
    )
    evidence = [
        {"source_id": 1, "source": "平台A", "text": "证据1"},
        {"source_id": "not-an-int", "source": "平台B", "text": "证据2"},
    ]

    filtered, _ = GraphService._filter_verified_completion(output, evidence)
    # Only source_id 1 is valid, so the point is filtered out.
    assert filtered.tech_points == []


def test_filter_verified_completion_knowledge_point_boundaries():
    output = GraphEnrichmentOutput(
        skill_name="Python",
        job_directions=["Python 后端开发工程师"],
        skill_area="Programming Language",
        tech_points=[
            TechPointOutput(
                name="有效技术点",
                detail="说明",
                confidence=0.85,
                source_ids=[1, 2],
                knowledge_points=[
                    KnowledgePointOutput(
                        name="有效知识点", description="OK", difficulty="easy",
                        confidence=0.75, source_ids=[1, 2],
                    ),
                    KnowledgePointOutput(
                        name="低置信度知识点", description="filtered", difficulty="easy",
                        confidence=0.74, source_ids=[1, 2],
                    ),
                    KnowledgePointOutput(
                        name="未知来源知识点", description="filtered", difficulty="easy",
                        confidence=0.85, source_ids=[1, 999],
                    ),
                ],
            )
        ],
    )
    evidence = [
        {"source_id": 1, "source": "平台A", "text": "证据1"},
        {"source_id": 2, "source": "平台B", "text": "证据2"},
    ]

    filtered, _ = GraphService._filter_verified_completion(output, evidence)
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
            evidence_source_ids=[1, 2],
            candidate_data=_make_output([
                TechPointOutput(
                    name="装饰器", detail="函数装饰器", confidence=0.85, source_ids=[1, 2],
                    knowledge_points=[
                        KnowledgePointOutput(
                            name="@wraps", description="保留元数据", difficulty="easy",
                            confidence=0.80, source_ids=[1, 2],
                        ),
                        KnowledgePointOutput(
                            name="低置信度", description="被过滤", difficulty="easy",
                            confidence=0.70, source_ids=[1, 2],
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
