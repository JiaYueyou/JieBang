import hashlib

from sqlalchemy import select

from app.core.database import async_session
from app.models import (
    EvidenceChunk,
    JobSkillFact,
    RawJobRecord,
    RetrievalIndexVersion,
    RetrievalQueryLog,
    Skill,
    SourceDocument,
    StandardJob,
)
from app.services.retrieval_service import RetrievalService
from app.schemas.retrieval import RetrievalSearchRequest


async def _seed_verified_fact() -> None:
    async with async_session() as db:
        standard = StandardJob(
            name="Python 后端工程师",
            canonical_key="python-backend",
            aliases=[],
            stack="backend",
            level="middle",
            description="Python 服务研发",
            source_count=2,
        )
        skill = Skill(
            name="FastAPI",
            canonical_name="FastAPI",
            canonical_key="fastapi",
            category="框架",
            aliases=[],
            validation_status="approved",
        )
        pending_skill = Skill(
            name="虚构框架",
            canonical_name="虚构框架",
            canonical_key="fictional-framework",
            category="框架",
            aliases=[],
            validation_status="pending_review",
        )
        source = SourceDocument(
            source="来源A",
            external_id="job-1",
            url="https://example.test/jobs/1",
            title="Python 后端工程师",
            company="示例科技",
            content_fingerprint=hashlib.sha256(b"job-1").hexdigest(),
            content_summary="FastAPI 服务开发",
            source_meta={},
        )
        db.add_all([standard, skill, pending_skill, source])
        await db.flush()
        raw = RawJobRecord(
            source_document_id=source.id,
            standard_job_id=standard.id,
            title="Python 后端工程师",
            standardized_title=standard.name,
            company="示例科技",
            jd_text="负责 Python 服务开发，熟悉 FastAPI、MySQL 和接口测试。",
            responsibilities="负责 Python 服务开发",
            requirements="熟悉 FastAPI 和 MySQL",
            keywords="Python,FastAPI,MySQL",
            dedup_status="unique",
            quality_score=0.91,
            freshness_score=0.95,
            source_trust_score=0.9,
            quality_status="accepted",
            quality_flags=[],
            near_duplicate_score=0,
            quality_policy_version="phase1-v1",
            is_excluded=False,
            normalized_data={},
        )
        db.add(raw)
        await db.flush()
        db.add(
            JobSkillFact(
                raw_job_record_id=raw.id,
                skill_id=skill.id,
                kind="required",
                importance=0.9,
                frequency=1,
                confidence=0.93,
                evidence_text="熟悉 FastAPI",
                verification_status="verified",
                extraction_method="rule",
                source_count=2,
            )
        )
        db.add(
            JobSkillFact(
                raw_job_record_id=raw.id,
                skill_id=pending_skill.id,
                kind="preferred",
                importance=0.4,
                frequency=1,
                confidence=0.6,
                evidence_text="模型补充但原文无证据",
                verification_status="unverified",
                extraction_method="llm",
                source_count=1,
            )
        )
        await db.commit()


async def test_admin_rebuilds_and_users_search_traceable_evidence(
    client,
    auth_headers,
):
    await _seed_verified_fact()

    rebuild = await client.post(
        "/api/v1/retrieval/indexes/rebuild",
        headers=auth_headers,
        json={"backend": "local_hash"},
    )
    assert rebuild.status_code == 200
    index = rebuild.json()["data"]
    assert index["status"] == "ready"
    assert index["chunk_count"] == 1
    assert index["entry_count"] == 1

    search = await client.post(
        "/api/v1/retrieval/search",
        headers=auth_headers,
        json={"query": "Python FastAPI", "top_k": 5},
    )
    assert search.status_code == 200
    result = search.json()["data"]
    assert result["index_version"] == index["version"]
    assert len(result["items"]) == 1
    evidence = result["items"][0]
    assert evidence["skill_name"] == "FastAPI"
    assert evidence["source_url"] == "https://example.test/jobs/1"
    assert evidence["retrieval_score"] > 0

    detail = await client.get(
        f"/api/v1/retrieval/evidence/{evidence['evidence_id']}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["job_skill_fact_id"] > 0

    async with async_session() as db:
        assert await db.scalar(select(EvidenceChunk.id)) == evidence["evidence_id"]
        query_log = await db.scalar(select(RetrievalQueryLog))
        assert query_log.result_evidence_ids == [evidence["evidence_id"]]

    no_answer = await client.post(
        "/api/v1/retrieval/search",
        headers=auth_headers,
        json={"query": "quantum chip lithography", "top_k": 5},
    )
    assert no_answer.status_code == 200
    assert no_answer.json()["data"]["items"] == []
    assert "没有足够" in no_answer.json()["data"]["warnings"][0]

    sparse_overlap = await client.post(
        "/api/v1/retrieval/search",
        headers=auth_headers,
        json={"query": "Python 量子芯片光刻设备维护", "top_k": 5},
    )
    assert sparse_overlap.status_code == 200
    assert sparse_overlap.json()["data"]["items"] == []
    assert "没有足够" in sparse_overlap.json()["data"]["warnings"][0]


async def test_local_hash_keeps_exact_authoritative_skill_match_for_short_query(
    client,
    auth_headers,
):
    await _seed_verified_fact()
    async with async_session() as db:
        skill = await db.scalar(select(Skill).where(Skill.canonical_name == "FastAPI"))
        skill.name = "C"
        skill.canonical_name = "C"
        skill.canonical_key = "c"
        fact = await db.scalar(select(JobSkillFact))
        fact.evidence_text = "具备 C 语言开发经验"
        await db.commit()

    rebuild = await client.post(
        "/api/v1/retrieval/indexes/rebuild",
        headers=auth_headers,
        json={"backend": "local_hash"},
    )
    assert rebuild.status_code == 200
    search = await client.post(
        "/api/v1/retrieval/search",
        headers=auth_headers,
        json={"query": "C", "top_k": 5},
    )
    assert search.status_code == 200
    assert [item["skill_name"] for item in search.json()["data"]["items"]] == ["C"]

    class ZeroHashProvider:
        model = "signed-token-hash-v1"
        dimension = 256

        async def embed_texts(self, texts):
            return [[0.0] * self.dimension for _ in texts]

    async with async_session() as db:
        service = RetrievalService(db, embedding_provider=ZeroHashProvider())
        service._provider_for_index = lambda index: ZeroHashProvider()
        result = await service.search(
            RetrievalSearchRequest(query="C", standard_job_id=1, top_k=5),
            user_id=1,
            log_query=False,
        )
        assert [item.skill_name for item in result.items] == ["C"]


async def test_index_rebuild_requires_admin(client):
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "normal", "password": "user123"},
    )
    token = login.json()["data"]["access_token"]
    response = await client.post(
        "/api/v1/retrieval/indexes/rebuild",
        headers={"Authorization": f"Bearer {token}"},
        json={"backend": "local_hash"},
    )

    assert response.status_code == 403


async def test_admin_rebuilds_chroma_index_and_searches_it(
    client,
    auth_headers,
):
    await _seed_verified_fact()

    rebuild = await client.post(
        "/api/v1/retrieval/indexes/rebuild",
        headers=auth_headers,
        json={"backend": "chroma"},
    )
    assert rebuild.status_code == 200
    index = rebuild.json()["data"]
    assert index["backend"] == "chroma"
    assert index["status"] == "ready"
    assert index["metadata_json"]["vector_store"] == "chroma"
    assert index["metadata_json"]["collection_name"].startswith(
        "jiebang-evidence-"
    )

    search = await client.post(
        "/api/v1/retrieval/search",
        headers=auth_headers,
        json={"query": "FastAPI", "top_k": 5},
    )
    assert search.status_code == 200
    data = search.json()["data"]
    assert data["backend"] == "chroma"
    assert [item["skill_name"] for item in data["items"]] == ["FastAPI"]
    assert not any("Chroma 向量召回不可用" in item for item in data["warnings"])


async def test_rebuild_rejects_an_empty_index_after_a_nonempty_ready_version():
    await _seed_verified_fact()
    async with async_session() as db:
        first = await RetrievalService(db).rebuild_index(
            created_by=None, backend="local_hash"
        )
        fact = await db.scalar(select(JobSkillFact))
        fact.verification_status = "unverified"
        await db.commit()

        try:
            await RetrievalService(db).rebuild_index(
                created_by=None, backend="local_hash"
            )
        except RuntimeError as exc:
            assert "activation rejected" in str(exc)
        else:
            raise AssertionError("empty replacement index must fail activation")

        ready = list((await db.execute(
            select(RetrievalIndexVersion).where(
                RetrievalIndexVersion.status == "ready"
            )
        )).scalars())
        assert [row.version for row in ready] == [first.version]
        chunk = await db.scalar(select(EvidenceChunk))
        assert chunk.verification_status == "machine_validated"
        fallback = await RetrievalService(db).search(
            RetrievalSearchRequest(
                query="FastAPI",
                index_version=first.version,
                top_k=5,
            ),
            user_id=1,
            log_query=False,
        )
        assert [item.skill_name for item in fallback.items] == ["FastAPI"]


async def test_search_degrades_to_lexical_when_persisted_embedding_provider_is_offline():
    await _seed_verified_fact()
    async with async_session() as db:
        built = await RetrievalService(db).rebuild_index(
            created_by=None, backend="local_hash"
        )
        class OfflineEmbeddingProvider:
            model = "text-embedding-3-large"

            async def embed_texts(self, texts):
                raise RuntimeError("offline")

        service = RetrievalService(db)
        service._provider_for_index = lambda index: OfflineEmbeddingProvider()

        result = await service.search(
            RetrievalSearchRequest(
                query="FastAPI", index_version=built.version, top_k=5
            ),
            user_id=1,
            log_query=False,
        )

        assert [item.skill_name for item in result.items] == ["FastAPI"]
        assert any("已降级为关键词" in warning for warning in result.warnings)
