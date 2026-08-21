"""Build traceable evidence indexes and execute bounded hybrid retrieval."""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    RETRIEVAL_MAX_READY_DROP_RATIO,
    RETRIEVAL_RELATIVE_SCORE_WINDOW,
    RETRIEVAL_SEMANTIC_SCORE_FLOOR,
)
from app.core.exceptions import ResourceNotFoundError
from app.core.neo4j import run_read, run_write
from app.core.time import utc_now_naive
from app.domain.retrieval import (
    CHUNKING_VERSION,
    INDEX_TEXT_VERSION,
    SKILL_SEARCH_CONTEXTS,
    EmbeddingProvider,
    build_evidence_window,
    build_index_text,
    cosine_similarity,
    embedding_checksum,
    lexical_score,
    match_authoritative_labels,
)
from app.domain.job_lifecycle import current_external_job_condition
from app.models import (
    EvidenceChunk,
    JobSkillFact,
    RawJobRecord,
    RetrievalIndexEntry,
    RetrievalIndexVersion,
    RetrievalQueryLog,
    Skill,
    SourceDocument,
    StandardJob,
)
from app.providers.embedding import build_embedding_provider
from app.providers.vector_store import ChromaVectorStore, VectorStore
from app.schemas.retrieval import (
    EvidenceChunkResponse,
    RetrievedEvidence,
    RetrievalIndexResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)


class RetrievalService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.db = db
        self.embedding_provider = (
            embedding_provider or build_embedding_provider()
        )
        self.vector_store = vector_store or ChromaVectorStore()

    async def rebuild_index(
        self,
        *,
        created_by: int | None,
        backend: str,
    ) -> RetrievalIndexResponse:
        previous_ready = await self.db.scalar(
            select(RetrievalIndexVersion)
            .where(RetrievalIndexVersion.status == "ready")
            .order_by(RetrievalIndexVersion.completed_at.desc())
        )
        index_id = str(uuid.uuid4())
        now = utc_now_naive()
        version = now.strftime("%Y%m%dT%H%M%S") + "-" + index_id[:8]
        base_metadata = {
            "authority": "mysql",
            "allowed_quality_statuses": ["accepted", "warning"],
            "allowed_fact_statuses": ["verified"],
            "index_text_version": INDEX_TEXT_VERSION,
        }
        index_values = dict(
            id=index_id,
            version=version,
            backend=backend,
            embedding_provider=self.embedding_provider.name,
            embedding_model=self.embedding_provider.model,
            embedding_dimension=self.embedding_provider.dimension,
            chunking_version=CHUNKING_VERSION,
            created_by=created_by,
            created_at=now,
        )
        index = RetrievalIndexVersion(
            **index_values,
            status="building",
            chunk_count=0,
            entry_count=0,
            metadata_json=base_metadata,
        )

        async def record_failed_build(
            *, error_stage: str, error: str, chunk_count: int, metadata: dict | None = None
        ) -> None:
            # Candidate EvidenceChunk mutations and index entries share the
            # build transaction. Roll them all back so the previous ready
            # index remains fully searchable, then persist only the audit row.
            await self.db.rollback()
            failed = RetrievalIndexVersion(
                **index_values,
                status="failed",
                chunk_count=chunk_count,
                entry_count=0,
                metadata_json={
                    **base_metadata,
                    **(metadata or {}),
                    "error_stage": error_stage,
                    "error": error[:500],
                },
                completed_at=utc_now_naive(),
            )
            self.db.add(failed)
            await self.db.commit()

        self.db.add(index)
        await self.db.flush()

        rows = (
            await self.db.execute(
                select(JobSkillFact, RawJobRecord, SourceDocument, Skill)
                .join(
                    RawJobRecord,
                    JobSkillFact.raw_job_record_id == RawJobRecord.id,
                )
                .join(
                    SourceDocument,
                    RawJobRecord.source_document_id == SourceDocument.id,
                )
                .join(Skill, JobSkillFact.skill_id == Skill.id)
                .where(
                    JobSkillFact.raw_job_record_id.is_not(None),
                    JobSkillFact.verification_status == "verified",
                    RawJobRecord.standard_job_id.is_not(None),
                    RawJobRecord.quality_status.in_(("accepted", "warning")),
                    RawJobRecord.is_excluded.is_(False),
                    Skill.validation_status == "approved",
                    current_external_job_condition(),
                )
                .order_by(JobSkillFact.id)
            )
        ).all()

        active_chunks: list[EvidenceChunk] = []
        index_texts: list[str] = []
        seen_ids: set[str] = set()
        for fact, raw, source, skill in rows:
            window = build_evidence_window(
                fact_id=fact.id,
                raw_job_record_id=raw.id,
                skill_id=skill.id,
                jd_text=raw.jd_text,
                evidence_text=fact.evidence_text,
                skill_name=skill.canonical_name,
            )
            seen_ids.add(window.evidence_id)
            chunk = await self.db.get(EvidenceChunk, window.evidence_id)
            if chunk is None:
                chunk = EvidenceChunk(
                    id=window.evidence_id,
                    job_skill_fact_id=fact.id,
                    source_document_id=source.id,
                    raw_job_record_id=raw.id,
                    standard_job_id=raw.standard_job_id,
                    skill_id=skill.id,
                    chunk_text=window.text,
                    char_start=window.char_start,
                    char_end=window.char_end,
                    source_platform=source.source,
                    source_url=source.url,
                    posted_at=raw.posted_at,
                    quality_score=raw.quality_score,
                    verification_status=(
                        "human_approved"
                        if fact.reviewed_by is not None
                        else "machine_validated"
                    ),
                    content_fingerprint=source.content_fingerprint,
                    near_duplicate_group_id=raw.near_duplicate_group_id,
                )
                self.db.add(chunk)
            else:
                chunk.job_skill_fact_id = fact.id
                chunk.source_document_id = source.id
                chunk.raw_job_record_id = raw.id
                chunk.standard_job_id = raw.standard_job_id
                chunk.skill_id = skill.id
                chunk.chunk_text = window.text
                chunk.char_start = window.char_start
                chunk.char_end = window.char_end
                chunk.source_platform = source.source
                chunk.source_url = source.url
                chunk.posted_at = raw.posted_at
                chunk.quality_score = raw.quality_score
                chunk.verification_status = (
                    "human_approved"
                    if fact.reviewed_by is not None
                    else "machine_validated"
                )
                chunk.content_fingerprint = source.content_fingerprint
                chunk.near_duplicate_group_id = raw.near_duplicate_group_id
            active_chunks.append(chunk)
            index_texts.append(
                build_index_text(
                    standard_job_name=raw.standardized_title or raw.title,
                    skill_name=skill.canonical_name,
                    skill_aliases=skill.aliases,
                    chunk_text=window.text,
                )
            )

        existing_chunks = list(
            (await self.db.execute(select(EvidenceChunk))).scalars()
        )
        for chunk in existing_chunks:
            if chunk.id not in seen_ids:
                chunk.verification_status = "expired"

        await self.db.flush()
        try:
            vectors = await self.embedding_provider.embed_texts(
                index_texts
            )
        except Exception as exc:
            await record_failed_build(
                error_stage="embedding",
                error=f"{type(exc).__name__}: {exc}",
                chunk_count=len(active_chunks),
            )
            raise
        entries: list[RetrievalIndexEntry] = []
        for chunk, index_text, vector in zip(
            active_chunks,
            index_texts,
            vectors,
        ):
            entry = RetrievalIndexEntry(
                index_version_id=index.id,
                evidence_id=chunk.id,
                embedding=vector,
                embedding_checksum=embedding_checksum(vector),
                lexical_text=index_text,
                backend_document_id=chunk.id,
            )
            self.db.add(entry)
            entries.append(entry)

        index.chunk_count = len(active_chunks)
        index.entry_count = len(entries)
        index.metadata_json = {
            **index.metadata_json,
            "expired_chunk_count": len(existing_chunks) - len(
                [chunk for chunk in existing_chunks if chunk.id in seen_ids]
            ),
        }
        if index.entry_count != index.chunk_count:
            raise RuntimeError("retrieval index entry/chunk count mismatch")
        if previous_ready is not None and previous_ready.chunk_count > 0:
            drop_ratio = 1 - (index.chunk_count / previous_ready.chunk_count)
            index.metadata_json = {
                **index.metadata_json,
                "previous_ready_version": previous_ready.version,
                "ready_drop_ratio": round(drop_ratio, 6),
            }
            if drop_ratio > RETRIEVAL_MAX_READY_DROP_RATIO:
                await record_failed_build(
                    error_stage="activation_gate",
                    error="retrieval evidence count dropped beyond configured threshold",
                    chunk_count=index.chunk_count,
                    metadata={
                        "previous_ready_version": previous_ready.version,
                        "ready_drop_ratio": round(drop_ratio, 6),
                    },
                )
                raise RuntimeError(
                    "retrieval activation rejected: evidence count dropped "
                    f"{drop_ratio:.1%} from previous ready index"
                )
        try:
            if backend == "neo4j_vector":
                await self._sync_neo4j(index, active_chunks, vectors)
            elif backend == "chroma":
                collection_name = await self._sync_chroma(
                    index,
                    active_chunks,
                    index_texts,
                    vectors,
                )
                index.metadata_json = {
                    **index.metadata_json,
                    "vector_store": "chroma",
                    "vector_store_mode": getattr(
                        self.vector_store,
                        "mode",
                        "configured",
                    ),
                    "collection_name": collection_name,
                }
            index.status = "ready"
            index.completed_at = utc_now_naive()
            await self.db.commit()
        except Exception as exc:
            await record_failed_build(
                error_stage="backend_sync",
                error=f"{type(exc).__name__}: {exc}",
                chunk_count=len(active_chunks),
                metadata=index.metadata_json,
            )
            raise
        return self._index_response(index)

    async def search(
        self,
        payload: RetrievalSearchRequest,
        *,
        user_id: int,
        log_query: bool = True,
    ) -> RetrievalSearchResponse:
        started = time.perf_counter()
        index = await self._resolve_index(payload.index_version)
        embedding_provider = self._provider_for_index(index)
        backend_warnings: list[str] = []
        query_vector: list[float] | None = None
        try:
            query_vector = (await embedding_provider.embed_texts([payload.query]))[0]
        except Exception as exc:
            backend_warnings.append(
                "查询向量服务不可用，已降级为关键词与权威标签检索："
                f"{type(exc).__name__}"
            )
        vector_store_scores: dict[str, float] = {}
        chroma_scores_available = False
        if query_vector is not None and index.backend == "neo4j_vector":
            try:
                vector_store_scores = await self._neo4j_scores(
                    query_vector,
                    index.version,
                    max(payload.top_k * 10, 50),
                )
            except Exception as exc:
                backend_warnings.append(
                    "Neo4j 向量召回不可用，已降级为 MySQL 可重建镜像："
                    f"{type(exc).__name__}"
                )
        elif query_vector is not None and index.backend == "chroma":
            try:
                vector_store_scores = await self.vector_store.query(
                    index_version=index.version,
                    embedding=query_vector,
                    limit=max(payload.top_k * 3, 30),
                    where=self._chroma_where(payload),
                )
                chroma_scores_available = True
            except Exception as exc:
                backend_warnings.append(
                    "Chroma 向量召回不可用，已降级为 MySQL 可重建镜像："
                    f"{type(exc).__name__}"
                )
        filters = [
            RetrievalIndexEntry.index_version_id == index.id,
            EvidenceChunk.verification_status.in_(
                payload.verification_statuses
            ),
            EvidenceChunk.quality_score >= payload.minimum_quality_score,
        ]
        if chroma_scores_available:
            filters.append(
                EvidenceChunk.id.in_(list(vector_store_scores))
            )
        if payload.standard_job_id is not None:
            filters.append(
                EvidenceChunk.standard_job_id == payload.standard_job_id
            )
        if payload.skill_ids:
            filters.append(EvidenceChunk.skill_id.in_(payload.skill_ids))
        if payload.source_platforms:
            filters.append(
                EvidenceChunk.source_platform.in_(payload.source_platforms)
            )
        if payload.posted_from is not None:
            filters.append(EvidenceChunk.posted_at >= payload.posted_from)

        rows = (
            await self.db.execute(
                select(
                    RetrievalIndexEntry,
                    EvidenceChunk,
                    Skill,
                    StandardJob,
                )
                .join(
                    EvidenceChunk,
                    RetrievalIndexEntry.evidence_id == EvidenceChunk.id,
                )
                .join(Skill, EvidenceChunk.skill_id == Skill.id)
                .join(
                    StandardJob,
                    EvidenceChunk.standard_job_id == StandardJob.id,
                )
                .where(*filters)
            )
        ).all()
        matched_job_ids, matched_skill_ids = match_authoritative_labels(
            payload.query,
            standard_jobs={
                standard_job.id: standard_job.name
                for _, _, _, standard_job in rows
            },
            skills={
                skill.id: skill.canonical_name
                for _, _, skill, _ in rows
            },
        )

        ranked: list[tuple[float, RetrievedEvidence]] = []
        for entry, chunk, skill, standard_job in rows:
            if (
                matched_job_ids
                and chunk.standard_job_id not in matched_job_ids
            ):
                continue
            if matched_skill_ids and chunk.skill_id not in matched_skill_ids:
                continue
            keyword = lexical_score(payload.query, entry.lexical_text)
            vector = vector_store_scores.get(
                chunk.id,
                cosine_similarity(query_vector, entry.embedding)
                if query_vector is not None else 0.0,
            )
            authoritative_match = bool(
                payload.standard_job_id is not None
                or payload.skill_ids
                or matched_job_ids
                or matched_skill_ids
            )
            graph = (
                1.0
                if authoritative_match
                else max(
                    lexical_score(payload.query, skill.canonical_name),
                    lexical_score(payload.query, standard_job.name),
                )
            )
            semantic_skill = max(
                lexical_score(payload.query, skill.canonical_name),
                lexical_score(
                    payload.query,
                    SKILL_SEARCH_CONTEXTS.get(
                        skill.canonical_name,
                        "",
                    ),
                ),
            )
            if matched_job_ids or matched_skill_ids:
                score = min(
                    1.0,
                    0.15 * vector
                    + 0.15 * keyword
                    + 0.15 * float(chunk.quality_score)
                    + 0.25 * graph
                    + 0.3 * semantic_skill,
                )
            else:
                score = min(
                    1.0,
                    0.4 * vector
                    + 0.2 * keyword
                    + 0.15 * float(chunk.quality_score)
                    + 0.15 * graph
                    + 0.1 * semantic_skill,
                )
            deterministic_baseline = query_vector is not None and embedding_provider.model.startswith(
                "signed-token-hash"
            )
            if (
                (deterministic_baseline and keyword <= 0)
                or (keyword <= 0 and vector <= 0)
                or (
                    not authoritative_match
                    and keyword <= 0
                    and vector < RETRIEVAL_SEMANTIC_SCORE_FLOOR
                )
                or score < payload.minimum_retrieval_score
            ):
                continue
            ranked.append(
                (
                    score,
                    RetrievedEvidence(
                        **self._evidence_response(chunk, skill).model_dump(),
                        retrieval_score=round(score, 6),
                        lexical_score=keyword,
                        vector_score=vector,
                        graph_score=graph,
                        index_version=index.version,
                    ),
                )
            )
        ranked.sort(
            key=lambda item: (
                item[0],
                item[1].quality_score,
                item[1].evidence_id,
            ),
            reverse=True,
        )

        selected: list[RetrievedEvidence] = []
        seen_groups: set[str] = set()
        relative_floor = (
            max(
                payload.minimum_retrieval_score,
                ranked[0][0] - RETRIEVAL_RELATIVE_SCORE_WINDOW,
            )
            if ranked
            else payload.minimum_retrieval_score
        )
        for score, item in ranked:
            if score < relative_floor:
                break
            group = item.near_duplicate_group_id
            if group and group in seen_groups:
                continue
            if group:
                seen_groups.add(group)
            selected.append(item)
            if len(selected) >= payload.top_k:
                break

        latency_ms = int((time.perf_counter() - started) * 1000)
        query_log = RetrievalQueryLog(
            id=str(uuid.uuid4()),
            index_version_id=index.id,
            query_hash=hashlib.sha256(
                payload.query.encode("utf-8")
            ).hexdigest(),
            query_summary=self._redact_query(payload.query),
            filters_json={
                "standard_job_id": payload.standard_job_id,
                "skill_ids": payload.skill_ids,
                "source_platforms": payload.source_platforms,
                "verification_statuses": payload.verification_statuses,
                "minimum_quality_score": payload.minimum_quality_score,
                "minimum_retrieval_score": payload.minimum_retrieval_score,
                "posted_from": (
                    payload.posted_from.isoformat()
                    if payload.posted_from
                    else None
                ),
            },
            top_k=payload.top_k,
            result_evidence_ids=[item.evidence_id for item in selected],
            latency_ms=latency_ms,
            created_by=user_id,
            created_at=utc_now_naive(),
        )
        if log_query:
            self.db.add(query_log)
            await self.db.commit()
        warnings = list(backend_warnings)
        if not selected:
            warnings.append("当前过滤条件下没有足够的已认证证据")
        if embedding_provider.model.startswith("signed-token-hash"):
            warnings.append("当前向量为确定性离线基线，不等同于语义 Embedding")
        return RetrievalSearchResponse(
            query=payload.query,
            index_version=index.version,
            backend=index.backend,
            items=selected,
            latency_ms=latency_ms,
            truncated=len(ranked) > len(selected),
            warnings=warnings,
        )

    async def _neo4j_scores(
        self,
        query_vector: list[float],
        index_version: str,
        limit: int,
    ) -> dict[str, float]:
        rows = await asyncio.to_thread(
            run_read,
            """
            CYPHER 25
            MATCH (node:EvidenceChunk)
            WHERE node.namespace = 'jiebang'
              AND node.index_version = $index_version
            SEARCH node IN (
                VECTOR INDEX jiebang_evidence_embedding
                FOR $embedding
                LIMIT $limit
            ) SCORE AS score
            RETURN node.evidence_id AS evidence_id, score
            """,
            {
                "limit": limit,
                "embedding": query_vector,
                "index_version": index_version,
            },
        )
        return {
            row["evidence_id"]: round(float(row["score"]), 6)
            for row in rows
            if row.get("evidence_id")
        }

    async def _sync_chroma(
        self,
        index: RetrievalIndexVersion,
        chunks: list[EvidenceChunk],
        index_texts: list[str],
        vectors: list[list[float]],
    ) -> str:
        records = [
            {
                "evidence_id": chunk.id,
                "embedding": vector,
                "document": index_text,
                "metadata": {
                    "namespace": "jiebang",
                    "index_version": index.version,
                    "standard_job_id": chunk.standard_job_id,
                    "skill_id": chunk.skill_id,
                    "source_platform": chunk.source_platform,
                    "quality_score": float(chunk.quality_score),
                    "verification_status": chunk.verification_status,
                    "posted_at_epoch": (
                        int(chunk.posted_at.timestamp())
                        if chunk.posted_at
                        else 0
                    ),
                    "near_duplicate_group_id": (
                        chunk.near_duplicate_group_id or ""
                    ),
                },
            }
            for chunk, index_text, vector in zip(
                chunks,
                index_texts,
                vectors,
            )
        ]
        return await self.vector_store.sync_index(
            index_version=index.version,
            dimension=index.embedding_dimension,
            records=records,
        )

    @staticmethod
    def _chroma_where(
        payload: RetrievalSearchRequest,
    ) -> dict:
        conditions: list[dict] = [
            {
                "verification_status": {
                    "$in": payload.verification_statuses
                }
            },
            {
                "quality_score": {
                    "$gte": float(payload.minimum_quality_score)
                }
            },
        ]
        if payload.standard_job_id is not None:
            conditions.append(
                {"standard_job_id": payload.standard_job_id}
            )
        if payload.skill_ids:
            conditions.append({"skill_id": {"$in": payload.skill_ids}})
        if payload.source_platforms:
            conditions.append(
                {
                    "source_platform": {
                        "$in": payload.source_platforms
                    }
                }
            )
        if payload.posted_from is not None:
            conditions.append(
                {
                    "posted_at_epoch": {
                        "$gte": int(payload.posted_from.timestamp())
                    }
                }
            )
        return {"$and": conditions}

    async def list_indexes(self) -> list[RetrievalIndexResponse]:
        rows = list(
            (
                await self.db.execute(
                    select(RetrievalIndexVersion).order_by(
                        RetrievalIndexVersion.created_at.desc()
                    )
                )
            ).scalars()
        )
        return [self._index_response(row) for row in rows]

    async def get_evidence(self, evidence_id: str) -> EvidenceChunkResponse:
        row = (
            await self.db.execute(
                select(EvidenceChunk, Skill)
                .join(Skill, EvidenceChunk.skill_id == Skill.id)
                .where(EvidenceChunk.id == evidence_id)
            )
        ).one_or_none()
        if row is None:
            raise ResourceNotFoundError("检索证据不存在")
        return self._evidence_response(*row)

    async def _resolve_index(
        self,
        version: str | None,
    ) -> RetrievalIndexVersion:
        statement = select(RetrievalIndexVersion).where(
            RetrievalIndexVersion.status == "ready"
        )
        if version:
            statement = statement.where(
                RetrievalIndexVersion.version == version
            )
        statement = statement.order_by(
            RetrievalIndexVersion.created_at.desc()
        )
        index = await self.db.scalar(statement)
        if index is None:
            raise ResourceNotFoundError("没有可用的检索索引，请先执行重建")
        return index

    def _provider_for_index(
        self,
        index: RetrievalIndexVersion,
    ) -> EmbeddingProvider:
        if (
            self.embedding_provider.model == index.embedding_model
            and self.embedding_provider.dimension
            == index.embedding_dimension
        ):
            return self.embedding_provider
        return build_embedding_provider(
            provider_name=index.embedding_provider,
            model=index.embedding_model,
            dimension=index.embedding_dimension,
        )

    async def _sync_neo4j(
        self,
        index: RetrievalIndexVersion,
        chunks: list[EvidenceChunk],
        vectors: list[list[float]],
    ) -> None:
        dimension = int(self.embedding_provider.dimension)
        await asyncio.to_thread(
            run_write,
            (
                "CREATE VECTOR INDEX jiebang_evidence_embedding IF NOT EXISTS "
                "FOR (n:EvidenceChunk) ON (n.embedding) "
                f"OPTIONS {{indexConfig: {{`vector.dimensions`: {dimension}, "
                "`vector.similarity_function`: 'cosine'}}"
            ),
        )
        payload = [
            {
                "id": chunk.id,
                "index_version": index.version,
                "standard_job_id": chunk.standard_job_id,
                "skill_id": chunk.skill_id,
                "quality_score": chunk.quality_score,
                "verification_status": chunk.verification_status,
                "embedding": vector,
            }
            for chunk, vector in zip(chunks, vectors)
        ]
        await asyncio.to_thread(
            run_write,
            """
            UNWIND $rows AS row
            MERGE (e:EvidenceChunk {namespace: 'jiebang', evidence_id: row.id})
            SET e.index_version = row.index_version,
                e.standard_job_id = row.standard_job_id,
                e.skill_id = row.skill_id,
                e.quality_score = row.quality_score,
                e.verification_status = row.verification_status,
                e.embedding = row.embedding
            RETURN count(e) AS indexed
            """,
            {"rows": payload},
        )

    @staticmethod
    def _redact_query(query: str) -> str:
        value = re.sub(
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
            "[email]",
            query,
        )
        value = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[phone]", value)
        return value[:500]

    @staticmethod
    def _evidence_response(
        chunk: EvidenceChunk,
        skill: Skill,
    ) -> EvidenceChunkResponse:
        return EvidenceChunkResponse(
            evidence_id=chunk.id,
            job_skill_fact_id=chunk.job_skill_fact_id,
            raw_job_record_id=chunk.raw_job_record_id,
            source_document_id=chunk.source_document_id,
            standard_job_id=chunk.standard_job_id,
            skill_id=chunk.skill_id,
            skill_name=skill.canonical_name,
            chunk_text=chunk.chunk_text,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            source_platform=chunk.source_platform,
            source_url=chunk.source_url,
            posted_at=chunk.posted_at,
            quality_score=chunk.quality_score,
            verification_status=chunk.verification_status,
            near_duplicate_group_id=chunk.near_duplicate_group_id,
        )

    @staticmethod
    def _index_response(
        row: RetrievalIndexVersion,
    ) -> RetrievalIndexResponse:
        return RetrievalIndexResponse(
            id=row.id,
            version=row.version,
            backend=row.backend,
            embedding_provider=row.embedding_provider,
            embedding_model=row.embedding_model,
            embedding_dimension=row.embedding_dimension,
            chunking_version=row.chunking_version,
            status=row.status,
            chunk_count=row.chunk_count,
            entry_count=row.entry_count,
            metadata_json=row.metadata_json,
            created_by=row.created_by,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )
