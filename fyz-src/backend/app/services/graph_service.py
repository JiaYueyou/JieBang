"""标准岗位聚合、图谱同步、深层补全与查询服务。"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    AUTO_PIPELINE_AUTO_PUBLISH_CONFIDENCE,
    GRAPH_ENRICHMENT_CONCURRENCY,
    GRAPH_ENRICHMENT_MAX_ATTEMPTS,
    GRAPH_ENRICHMENT_TIMEOUT_SECONDS,
)
from app.core.database import async_session
from app.core.agent_runtime import SkillGraphCompletionAgent
from app.core.exceptions import InvalidParameterError, ResourceNotFoundError
from app.core.graph_sync_lock import serialized_graph_sync
from app.core.time import utc_now, utc_now_naive
from app.domain.job_standardizer import CATEGORY_STACK, normalize_job_title
from app.domain.skill_dictionary import canonical_key
from app.domain.statuses import AgentRunStatus, TaskStatus
from app.models import (
    AgentRun,
    AsyncTask,
    GraphEnrichmentCandidate,
    GraphSnapshot,
    GraphSyncBatch,
    JobPosting,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    StandardJob,
    StandardJobAlias,
    StandardJobSource,
)
from app.providers import DeepSeekProvider, LLMProvider
from app.repositories import GraphAuditRepository, Neo4jGraphRepository
from app.schemas.graph import (
    GraphEdge,
    GraphEnrichmentOutput,
    GraphNode,
    GraphSnapshotResponse,
    GraphSubgraph,
    KnowledgePointOutput,
    TechPointOutput,
)
from app.schemas.retrieval import RetrievalSearchRequest, RetrievalSearchResponse
from app.schemas.skill import TaskStatusResponse
from app.services.agent_grounding_service import (
    AgentGroundingReport,
    AgentGroundingService,
    GroundedClaim,
)
from app.services.retrieval_service import RetrievalService


_local_graph_tasks: set[asyncio.Task] = set()
logger = logging.getLogger(__name__)


class GraphService:
    # L4 技术点名称可剥离的复合修饰后缀（最长匹配优先，基于快照真实样本校准）
    _L4_COMPOUND_SUFFIXES = (
        "持久层框架", "数据库开发与优化", "开发与多语言协同", "开发基础与工程规范",
        "基础与简单编程配置", "语言核心与工程应用", "后端与web开发",
        "基本数据库操作", "项目研发经验", "项目开发实践", "提交与对象模型",
        "分支与合并机制", "基本语法与结构", "基础语法与常用类库",
        "环境下的应用与嵌入式编程", "中间件使用", "脚本编写",
    )
    # L4 技术点名称可剥离的单修饰后缀（守卫保证剥离后长度 ≥2）
    _L4_SUFFIXES = (
        "框架", "技术", "原理", "详解", "实战", "开发", "优化", "调优",
        "基础", "工程", "规范", "应用", "使用", "操作", "编写", "配置",
        "实现", "设计", "分析", "维护", "部署", "协同", "经验", "实践",
        "机制", "模型", "核心", "中间件", "模块", "方案", "组件", "库",
        "平台", "数据库", "编程",
    )
    # L5 知识点仅剥课程式后缀，避免误伤概念短语（如 "Git 三区模型"）
    _L5_SUFFIXES = ("详解", "实战", "入门", "进阶", "原理", "教程")

    def __init__(
        self,
        db: AsyncSession,
        *,
        graph_repository: Neo4jGraphRepository | None = None,
        llm_provider: LLMProvider | None = None,
        retrieval_service: RetrievalService | None = None,
        grounding_service: AgentGroundingService | None = None,
    ) -> None:
        self.db = db
        self.audit = GraphAuditRepository(db)
        self.graph = graph_repository or Neo4jGraphRepository()
        self.llm = llm_provider or DeepSeekProvider()
        self.enrichment_agent = SkillGraphCompletionAgent(
            self.llm,
            timeout_seconds=GRAPH_ENRICHMENT_TIMEOUT_SECONDS,
            max_attempts=GRAPH_ENRICHMENT_MAX_ATTEMPTS,
        )
        self.retrieval = retrieval_service or RetrievalService(db)
        self.grounding = grounding_service or AgentGroundingService(db)

    async def aggregate_standard_jobs(self) -> int:
        raw_jobs = list(
            (
                await self.db.execute(
                    select(RawJobRecord).where(
                        RawJobRecord.quality_status.in_(("accepted", "warning")),
                        RawJobRecord.is_excluded.is_(False),
                    )
                )
            ).scalars()
        )
        internal_jobs = list((await self.db.execute(
            select(JobPosting).where(JobPosting.deleted_at.is_(None))
        )).scalars())
        for source_type, rows in (("raw", raw_jobs), ("internal", internal_jobs)):
            for row in rows:
                title = row.standardized_title or row.title
                normalized = normalize_job_title(
                    row.title,
                    city=getattr(row, "city", None) or getattr(row, "location", None),
                    company=getattr(row, "company", None),
                    jd_text=getattr(row, "jd_text", None),
                )
                standard = await self.audit.get_standard_job(normalized.canonical_key)
                if not standard:
                    standard = StandardJob(
                        name=normalized.name,
                        canonical_key=normalized.canonical_key,
                        aliases=[],
                        stack={
                            "algorithm": "ai",
                            "data": "data",
                            "devops": "devops",
                            "product": "product",
                            "operations": "business",
                            "sales": "business",
                        }.get(normalized.role_family, "backend"),
                        level=normalized.level,
                        role_family=normalized.role_family,
                        specialization_key=normalized.specialization_key,
                        occupation_code=normalized.occupation_code,
                        normalization_version=normalized.version,
                        description=f"由多来源岗位数据聚合形成的{normalized.name}能力模型。",
                        source_count=0,
                    )
                    self.db.add(standard)
                    await self.db.flush()
                aliases = set(standard.aliases or [])
                if row.title != standard.name:
                    aliases.add(row.title)
                standard.aliases = sorted(aliases)
                standard.last_seen_at = utc_now_naive()
                if source_type == "raw":
                    row.standardized_title = standard.name
                    row.standard_job_id = standard.id
                    row.city_code = normalized.city_code
                    row.company_key = normalized.company_key
                    row.work_mode = normalized.work_mode
                    row.employment_type = normalized.employment_type
                    row.normalization_version = normalized.version
                    row.normalization_status = normalized.status
                    row.normalization_confidence = normalized.confidence
                alias_key = "".join(ch for ch in row.title.casefold() if ch.isalnum())
                alias = await self.db.scalar(select(StandardJobAlias).where(
                    StandardJobAlias.standard_job_id == standard.id,
                    StandardJobAlias.alias_key == alias_key,
                ))
                if alias is None:
                    self.db.add(StandardJobAlias(
                        standard_job_id=standard.id,
                        alias=row.title,
                        alias_key=alias_key,
                        source_type=source_type,
                        confidence=normalized.confidence,
                        normalization_version=normalized.version,
                    ))
                link = await self.audit.get_source(source_type, row.id)
                if not link:
                    self.db.add(StandardJobSource(
                        standard_job_id=standard.id,
                        source_type=source_type,
                        source_id=row.id,
                        original_title=row.title,
                        confidence=normalized.confidence,
                    ))
        await self.db.flush()
        counts = (await self.db.execute(
            select(StandardJobSource.standard_job_id, func.count(StandardJobSource.id))
            .group_by(StandardJobSource.standard_job_id)
        )).all()
        for standard_job_id, count in counts:
            standard = await self.db.get(StandardJob, standard_job_id)
            standard.source_count = int(count)
        await self.db.flush()
        return await self.audit.count_standard_jobs()

    async def sync(
        self,
        *,
        mode: str,
        enrich_top_skills: bool,
        user_id: int | None,
        task_id: str | None = None,
        auto_publish_enrichment: bool = False,
        _lock_acquired: bool = False,
    ) -> dict:
        if not _lock_acquired:
            async with serialized_graph_sync():
                return await self.sync(
                    mode=mode,
                    enrich_top_skills=enrich_top_skills,
                    user_id=user_id,
                    task_id=task_id,
                    auto_publish_enrichment=auto_publish_enrichment,
                    _lock_acquired=True,
                )
        snapshot_id = str(uuid.uuid4())
        version = utc_now_naive().strftime("%Y%m%dT%H%M%S") + "-" + snapshot_id[:8]
        snapshot = GraphSnapshot(
            id=snapshot_id,
            version=version,
            snapshot_type=mode,
            status=TaskStatus.running.value,
            created_by=user_id,
            created_at=utc_now_naive(),
        )
        batch = GraphSyncBatch(
            id=str(uuid.uuid4()),
            async_task_id=task_id,
            snapshot_id=snapshot_id,
            sync_mode=mode,
            status=TaskStatus.running.value,
            started_at=utc_now_naive(),
            created_at=utc_now_naive(),
        )
        self.db.add_all([snapshot, batch])
        await self.db.commit()
        try:
            await self._report_progress(task_id, batch, 8, "standardizing", "正在聚合标准岗位")
            standard_count = await self.aggregate_standard_jobs()
            await self._report_progress(task_id, batch, 20, "retrieving", "正在检索可补全技术栈")
            enrichment_stats = {
                "enabled": bool(getattr(self.llm, "enabled", True)),
                "candidates_total": 0,
                "candidates_verified": 0,
                "candidates_machine_validated": 0,
                "candidates_failed": 0,
                "candidates_skipped": 0,
                "tech_points_written": 0,
                "knowledge_points_written": 0,
            }
            if enrich_top_skills:
                enrichment_stats.update(
                    await self._prepare_top_candidates(
                        snapshot_id,
                        user_id,
                        progress_callback=lambda completed, total, skill_name, status: self._report_progress(
                            task_id,
                            batch,
                            20 + int(50 * completed / max(total, 1)),
                            "generating",
                            f"并发生成 L4/L5：{completed}/{total}（{skill_name}：{status}）",
                            completed=completed,
                            total=total,
                        ),
                    )
                )
                if auto_publish_enrichment:
                    auto_approved = await self.auto_approve_enrichment_candidates(
                        snapshot_id=snapshot_id,
                        minimum_confidence=AUTO_PIPELINE_AUTO_PUBLISH_CONFIDENCE,
                    )
                    enrichment_stats["candidates_auto_approved"] = len(auto_approved)
            await self._report_progress(task_id, batch, 76, "building", "正在构建图谱节点与关系")
            nodes, edges, fact_count = await self._build_payload(snapshot)
            (
                tech_points,
                knowledge_points,
                published_candidate_ids,
                superseded_candidate_ids,
            ) = await self._append_verified_deep_nodes(
                snapshot_id, nodes, edges
            )
            enrichment_stats["tech_points_written"] = tech_points
            enrichment_stats["knowledge_points_written"] = knowledge_points
            await self._report_progress(task_id, batch, 88, "publishing", "正在写入 Neo4j 正式图谱")
            await asyncio.to_thread(self._write_payload, nodes, edges, version, mode)
            counts = await asyncio.to_thread(self.graph.counts)
            for candidate_id in published_candidate_ids:
                candidate = await self.db.get(GraphEnrichmentCandidate, candidate_id)
                if candidate:
                    candidate.verification_status = "verified"
                    candidate.publication_status = "published"
                    candidate.published_at = utc_now_naive()
            for candidate_id in superseded_candidate_ids:
                candidate = await self.db.get(GraphEnrichmentCandidate, candidate_id)
                if candidate:
                    candidate.publication_status = "superseded"
            for row in nodes.get("TechStack", []):
                skill_id = int(row["id"].split(":", 1)[1])
                skill = await self.db.get(Skill, skill_id)
                if skill:
                    skill.graph_node_id = row["id"]
            snapshot.status = TaskStatus.succeeded.value
            snapshot.node_count = counts["nodes"]
            snapshot.edge_count = counts["edges"]
            snapshot.fact_count = fact_count
            snapshot.completed_at = utc_now_naive()
            snapshot.metadata_json = {
                "standard_jobs": standard_count,
                "enrichment": enrichment_stats,
            }
            batch.status = TaskStatus.succeeded.value
            batch.progress = 100
            batch.node_count = counts["nodes"]
            batch.edge_count = counts["edges"]
            batch.finished_at = utc_now_naive()
            await self.db.commit()
            return {
                "snapshot_id": snapshot.id,
                "version": snapshot.version,
                "standard_jobs": standard_count,
                "node_count": snapshot.node_count,
                "edge_count": snapshot.edge_count,
                "fact_count": fact_count,
                "published_candidate_count": len(published_candidate_ids),
                "superseded_candidate_count": len(superseded_candidate_ids),
            }
        except Exception as exc:
            await self.db.rollback()
            snapshot = await self.db.get(GraphSnapshot, snapshot_id)
            batch = (await self.db.execute(
                select(GraphSyncBatch).where(GraphSyncBatch.snapshot_id == snapshot_id)
            )).scalar_one()
            snapshot.status = TaskStatus.failed.value
            snapshot.completed_at = utc_now_naive()
            batch.status = TaskStatus.failed.value
            batch.error_message = str(exc)[:2000]
            batch.finished_at = utc_now_naive()
            await self.db.commit()
            raise

    async def _report_progress(
        self,
        task_id: str | None,
        batch: GraphSyncBatch,
        progress: int,
        stage: str,
        detail: str,
        *,
        completed: int | None = None,
        total: int | None = None,
    ) -> None:
        batch.progress = progress
        if task_id:
            task = await self.db.get(AsyncTask, task_id)
            if task:
                task.progress = progress
                task.result = {
                    "stage": stage,
                    "detail": detail,
                    "completed": completed,
                    "total": total,
                }
        await self.db.commit()
        logger.info(
            "graph_sync_progress task_id=%s snapshot_id=%s progress=%d stage=%s detail=%s",
            task_id,
            batch.snapshot_id,
            progress,
            stage,
            detail,
        )

    async def _prepare_top_candidates(
        self,
        snapshot_id: str,
        user_id: int | None,
        progress_callback=None,
    ) -> dict[str, int]:
        rows = (await self.db.execute(
            select(Skill, func.count(JobSkillFact.id).label("coverage"))
            .join(JobSkillFact, JobSkillFact.skill_id == Skill.id)
            .where(
                JobSkillFact.verification_status == "verified",
                Skill.validation_status == "approved",
                Skill.category != "soft_skill",
            )
            .group_by(Skill.id)
            .order_by(func.count(JobSkillFact.id).desc(), Skill.id)
            .limit(20)
        )).all()
        stats = {
            "candidates_total": len(rows),
            "candidates_machine_validated": 0,
            "candidates_failed": 0,
            "candidates_skipped": 0,
        }
        logger.info("graph_enrichment: preparing %d top candidates for snapshot %s", len(rows), snapshot_id)
        semaphore = asyncio.Semaphore(GRAPH_ENRICHMENT_CONCURRENCY)

        async def run_one(skill_id: int) -> tuple[str, str]:
            async with semaphore:
                if GRAPH_ENRICHMENT_CONCURRENCY == 1:
                    result = await self._prepare_candidate(snapshot_id, skill_id, user_id)
                    await self.db.flush()
                    return result
                async with async_session() as worker_db:
                    worker = GraphService(
                        worker_db,
                        graph_repository=self.graph,
                        llm_provider=self.llm,
                    )
                    status, skill_name = await worker._prepare_candidate(
                        snapshot_id, skill_id, user_id
                    )
                    await worker_db.commit()
                    return status, skill_name

        tasks = [asyncio.create_task(run_one(skill.id)) for skill, _coverage in rows]
        for completed, task in enumerate(asyncio.as_completed(tasks), start=1):
            status, skill_name = await task
            stats[f"candidates_{status}"] += 1
            if progress_callback:
                await progress_callback(completed, len(tasks), skill_name, status)
        logger.info(
            "graph_enrichment: snapshot=%s total=%d machine_validated=%d failed=%d skipped=%d concurrency=%d",
            snapshot_id,
            stats["candidates_total"],
            stats["candidates_machine_validated"],
            stats["candidates_failed"],
            stats["candidates_skipped"],
            GRAPH_ENRICHMENT_CONCURRENCY,
        )
        return stats

    async def _prepare_candidate(
        self, snapshot_id: str, skill_id: int, user_id: int | None
    ) -> tuple[str, str]:
        skill = await self.db.get(Skill, skill_id)
        if skill is None:
            logger.warning("graph_enrichment: skill_id=%s disappeared", skill_id)
            return "skipped", str(skill_id)
        candidate = GraphEnrichmentCandidate(
            snapshot_id=snapshot_id,
            skill_id=skill.id,
            evidence_source_ids=[],
            candidate_data={"reason": "llm_disabled", "skill_name": skill.name},
            confidence=0,
            verification_status="unverified",
            machine_validation_status="pending",
            review_status="pending",
            publication_status="draft",
        )
        provider_enabled = bool(getattr(self.llm, "enabled", True))
        if not provider_enabled:
            candidate.candidate_data = {"reason": "llm_disabled", "skill_name": skill.name}
            candidate.machine_validation_status = "skipped"
            logger.info("graph_enrichment: skill=%s skipped (llm disabled)", skill.name)
            await self.audit.add_candidate(candidate)
            return "skipped", skill.name

        retrieval_query = f"{skill.name} 技术点 知识点 常用方案 核心组件"
        try:
            retrieval = await self.retrieval.search(
                RetrievalSearchRequest(
                    query=retrieval_query,
                    skill_ids=[skill.id],
                    top_k=8,
                    minimum_quality_score=0.55,
                    minimum_retrieval_score=0.2,
                ),
                user_id=user_id or 0,
                log_query=user_id is not None,
            )
        except Exception as exc:
            candidate.candidate_data = {
                "reason": "retrieval_unavailable",
                "skill_name": skill.name,
                "error_code": type(exc).__name__,
            }
            candidate.machine_validation_status = "retrieval_failed"
            logger.warning(
                "graph_enrichment: skill=%s skipped (retrieval unavailable: %s)",
                skill.name,
                type(exc).__name__,
            )
            await self.audit.add_candidate(candidate)
            return "skipped", skill.name

        candidate.evidence_source_ids = [item.evidence_id for item in retrieval.items]
        independent_sources = {item.source_platform.strip().casefold() for item in retrieval.items}
        if len(retrieval.items) < 2 or len(independent_sources) < 2:
            candidate.candidate_data = {
                "reason": "insufficient_evidence",
                "skill_name": skill.name,
                "sources": sorted(independent_sources),
                "evidence_ids": candidate.evidence_source_ids,
                "source_count": len(retrieval.items),
                "index_version": retrieval.index_version,
                "warnings": retrieval.warnings,
            }
            candidate.machine_validation_status = "insufficient_evidence"
            logger.info(
                "graph_enrichment: skill=%s skipped (insufficient evidence: %d sources, %d platforms)",
                skill.name, len(retrieval.items), len(independent_sources),
            )
            status = "skipped"
        else:
            await self._enrich_candidate(candidate, skill, retrieval, user_id)
            if candidate.candidate_data.get("reason") in {"llm_failed", "llm_timeout"}:
                logger.warning("graph_enrichment: skill=%s enrichment failed", skill.name)
                status = "failed"
            elif candidate.verification_status == "machine_validated":
                logger.info("graph_enrichment: skill=%s machine validated", skill.name)
                status = "machine_validated"
            else:
                logger.info("graph_enrichment: skill=%s filtered out", skill.name)
                status = "skipped"
        await self.audit.add_candidate(candidate)
        return status, skill.name

    async def _job_directions_for_skill(self, skill_id: int) -> list[str]:
        raw_names = (await self.db.execute(
            select(StandardJob.name)
            .join(StandardJobSource, StandardJobSource.standard_job_id == StandardJob.id)
            .join(JobSkillFact, JobSkillFact.raw_job_record_id == StandardJobSource.source_id)
            .where(
                StandardJobSource.source_type == "raw",
                JobSkillFact.skill_id == skill_id,
                JobSkillFact.verification_status == "verified",
            )
        )).scalars()
        internal_names = (await self.db.execute(
            select(StandardJob.name)
            .join(StandardJobSource, StandardJobSource.standard_job_id == StandardJob.id)
            .join(JobSkillFact, JobSkillFact.job_id == StandardJobSource.source_id)
            .where(
                StandardJobSource.source_type == "internal",
                JobSkillFact.skill_id == skill_id,
                JobSkillFact.verification_status == "verified",
            )
        )).scalars()
        return list(dict.fromkeys([*raw_names, *internal_names]))[:20]

    async def _enrich_candidate(
        self,
        candidate: GraphEnrichmentCandidate,
        skill: Skill,
        retrieval: RetrievalSearchResponse,
        user_id: int | None,
    ) -> None:
        logger = logging.getLogger(__name__)
        run_id = str(uuid.uuid4())
        started = time.perf_counter()
        logger.info("graph_enrichment: enriching skill=%s run_id=%s", skill.name, run_id)
        run = AgentRun(
            id=run_id,
            agent_type="graph_enrichment",
            provider=self.llm.provider_name,
            model=self.llm.model_name,
            prompt_version=self.enrichment_agent.prompt_version,
            input_summary=(
                f"{skill.name}: {len(retrieval.items)} evidence rows; "
                f"index={retrieval.index_version}"
            ),
            status=AgentRunStatus.running.value,
            retry_count=0,
            created_by=user_id,
            started_at=utc_now(),
        )
        self.db.add(run)
        await self.db.flush()
        candidate.agent_run_id = run_id
        evidence = [
            {
                "evidence_id": item.evidence_id,
                "source": item.source_platform[:100],
                "text": item.chunk_text[:1200],
            }
            for item in retrieval.items
        ]
        try:
            output = await self.enrichment_agent.enrich(
                skill_name=skill.name,
                evidence=evidence,
                skill_area=skill.category.replace("_", " ").title(),
                job_directions=await self._job_directions_for_skill(skill.id),
            )
            claims = self._grounding_claims(output)
            report = await self.grounding.validate_and_persist(
                agent_run_id=run_id,
                claims=claims,
                evidence=retrieval.items,
                minimum_sources=2,
                minimum_quality_score=0.55,
                maximum_age_days=1095,
                minimum_semantic_score=0.12,
            )
            filtered, confidence = self._filter_grounded_completion(
                output,
                report,
            )
            candidate.candidate_data = {
                **filtered.model_dump(mode="json"),
                "reason": (
                    None
                    if filtered.tech_points
                    else "insufficient_grounding"
                ),
                "machine_validation": report.to_dict(),
            }
            candidate.confidence = confidence
            candidate.verification_status = (
                "machine_validated"
                if filtered.tech_points
                else "unverified"
            )
            candidate.machine_validation_status = (
                "passed" if filtered.tech_points else "failed"
            )
            run.status = (
                AgentRunStatus.succeeded.value
                if filtered.tech_points and report.rejected_count == 0
                else AgentRunStatus.degraded.value
            )
            run.structured_output = {
                "raw_output": output.model_dump(mode="json"),
                "validated_output": filtered.model_dump(mode="json"),
                "retrieval": {
                    "query_summary": retrieval.query,
                    "evidence_ids": [
                        item.evidence_id for item in retrieval.items
                    ],
                    "index_version": retrieval.index_version,
                    "backend": retrieval.backend,
                    "warnings": retrieval.warnings,
                },
                "validation": report.to_dict(),
                "fallback_reason": (
                    None
                    if filtered.tech_points
                    else "insufficient_grounding"
                ),
            }
            logger.info(
                "graph_enrichment: skill=%s run_id=%s tech_points=%d knowledge_points=%d confidence=%.2f",
                skill.name,
                run_id,
                len(filtered.tech_points),
                sum(len(p.knowledge_points) for p in filtered.tech_points),
                confidence,
            )
        except Exception as exc:
            error_message = str(exc)
            failure_reason = (
                "llm_timeout" if "timed out" in error_message.casefold() else "llm_failed"
            )
            candidate.candidate_data = {
                "reason": failure_reason,
                "error": error_message[:500],
                "retryable": failure_reason == "llm_timeout",
            }
            candidate.machine_validation_status = "failed"
            run.status = AgentRunStatus.failed.value
            run.error_code = type(exc).__name__
            run.error_message = str(exc)[:2000]
            run.structured_output = {
                "retrieval": {
                    "query_summary": retrieval.query,
                    "evidence_ids": [
                        item.evidence_id for item in retrieval.items
                    ],
                    "index_version": retrieval.index_version,
                    "backend": retrieval.backend,
                    "warnings": retrieval.warnings,
                },
                "validation": {
                    "status": "not_run",
                    "accepted_claim_count": 0,
                    "rejected_claim_count": 0,
                    "claims": [],
                },
                "fallback_reason": failure_reason,
            }
            logger.exception("graph_enrichment: skill=%s run_id=%s failed", skill.name, run_id)
        finally:
            run.duration_ms = int((time.perf_counter() - started) * 1000)
            run.finished_at = utc_now()

    @staticmethod
    def _grounding_claims(
        output: GraphEnrichmentOutput,
    ) -> list[GroundedClaim]:
        claims: list[GroundedClaim] = []
        for point_index, point in enumerate(output.tech_points):
            claims.append(
                GroundedClaim(
                    claim_id=f"tech:{point_index}",
                    claim_type="tech_point",
                    claim_text=f"{point.name}\n{point.detail}",
                    anchor_text=point.name,
                    evidence_ids=tuple(point.evidence_ids),
                )
            )
            for knowledge_index, item in enumerate(
                point.knowledge_points
            ):
                claims.append(
                    GroundedClaim(
                        claim_id=(
                            f"knowledge:{point_index}:{knowledge_index}"
                        ),
                        claim_type="knowledge_point",
                        claim_text="\n".join(filter(None, [
                            item.name,
                            item.description,
                            "核心技术：" + "、".join(item.core_stack) if item.core_stack else "",
                            "常用方案：" + "；".join(
                                f"{solution.name}：{solution.purpose}"
                                for solution in item.common_solutions
                            ) if item.common_solutions else "",
                        ])),
                        anchor_text=item.name,
                        evidence_ids=tuple(item.evidence_ids),
                    )
                )
        return claims

    @staticmethod
    def _filter_grounded_completion(
        output: GraphEnrichmentOutput,
        report: AgentGroundingReport,
    ) -> tuple[GraphEnrichmentOutput, float]:
        accepted = report.accepted_claim_ids
        accepted_points = []
        confidences: list[float] = []
        for point_index, point in enumerate(output.tech_points):
            if (
                point.confidence < 0.75
                or f"tech:{point_index}" not in accepted
            ):
                continue
            accepted_knowledge = [
                item
                for knowledge_index, item in enumerate(
                    point.knowledge_points
                )
                if item.confidence >= 0.75
                and (
                    f"knowledge:{point_index}:{knowledge_index}"
                    in accepted
                )
            ]
            accepted_points.append(
                point.model_copy(
                    update={"knowledge_points": accepted_knowledge}
                )
            )
            confidences.append(point.confidence)
            confidences.extend(
                item.confidence for item in accepted_knowledge
            )
        deduped_points = GraphService._dedupe_by_name(accepted_points)
        return (
            output.model_copy(update={"tech_points": deduped_points}),
            min(confidences, default=0),
        )

    async def _build_payload(self, snapshot: GraphSnapshot) -> tuple[dict, dict, int]:
        standard_jobs = list((await self.db.execute(select(StandardJob))).scalars())
        sources = list((await self.db.execute(select(StandardJobSource))).scalars())
        source_map = {(row.source_type, row.source_id): row.standard_job_id for row in sources}
        eligible_raw_rows = (
            await self.db.execute(
                select(RawJobRecord).where(
                    RawJobRecord.quality_status.in_(("accepted", "warning")),
                    RawJobRecord.is_excluded.is_(False),
                )
            )
        ).scalars().all()
        raw_to_document = {
            row.id: row.source_document_id for row in eligible_raw_rows
        }
        documents = {
            row.id: row for row in (await self.db.execute(select(SourceDocument))).scalars()
        }
        fact_rows = (await self.db.execute(
            select(JobSkillFact, Skill).join(Skill, Skill.id == JobSkillFact.skill_id)
            .where(
                JobSkillFact.verification_status == "verified",
                Skill.validation_status == "approved",
            )
        )).all()

        nodes: dict[str, list[dict]] = defaultdict(list)
        edges: dict[str, list[dict]] = defaultdict(list)
        job_by_id = {job.id: job for job in standard_jobs}
        for job in standard_jobs:
            nodes["Job"].append(self._node(
                f"job:{job.id}", name=job.name, canonicalKey=job.canonical_key,
                stack=job.stack, level=job.level, description=job.description,
                sourceCount=job.source_count,
            ))
        areas: dict[str, dict] = {}
        skills: dict[int, Skill] = {}
        job_skill_stats: dict[tuple[int, int], dict] = {}
        support_pairs: set[tuple[int, int, int]] = set()
        for fact, skill in fact_rows:
            if (
                fact.raw_job_record_id is not None
                and fact.raw_job_record_id not in raw_to_document
            ):
                continue
            source_type = "raw" if fact.raw_job_record_id else "internal"
            source_id = fact.raw_job_record_id or fact.job_id
            standard_job_id = source_map.get((source_type, source_id))
            if not standard_job_id:
                continue
            skills[skill.id] = skill
            stat = job_skill_stats.setdefault((standard_job_id, skill.id), {
                "frequency": 0, "source_ids": set(), "confidence": 0.0,
                "importance": 0.0, "first_seen": fact.created_at, "last_seen": fact.updated_at,
            })
            stat["frequency"] += 1
            stat["confidence"] = max(stat["confidence"], fact.confidence)
            stat["importance"] = max(stat["importance"], fact.importance)
            stat["first_seen"] = min(stat["first_seen"], fact.created_at)
            stat["last_seen"] = max(stat["last_seen"], fact.updated_at)
            if fact.raw_job_record_id:
                document_id = raw_to_document.get(fact.raw_job_record_id)
                if document_id:
                    stat["source_ids"].add(document_id)
                    support_pairs.add((document_id, standard_job_id, skill.id))
        for skill in skills.values():
            stack = CATEGORY_STACK.get(skill.category, "backend")
            areas.setdefault(skill.category, {
                "name": skill.category.replace("_", " ").title(),
                "stack": stack,
            })
            nodes["TechStack"].append(self._node(
                f"skill:{skill.id}", name=skill.name, canonicalKey=skill.canonical_key,
                stack=stack, level="middle", description=f"{skill.category} 标准技能",
                frequency=sum(s["frequency"] for (j, sid), s in job_skill_stats.items() if sid == skill.id),
            ))
            edges["CONTAINS"].append(self._edge(
                f"area:{skill.category}", f"skill:{skill.id}",
                category=skill.category,
            ))
        for category, area in areas.items():
            nodes["SkillArea"].append(self._node(
                f"area:{category}", name=area["name"], canonicalKey=category,
                stack=area["stack"], level="middle", description=f"{category} 技能领域",
            ))
        skill_stats: dict[int, dict] = defaultdict(lambda: {
            "frequency": 0, "source_ids": set(), "confidence": 0.0,
            "importance": 0.0, "first_seen": None, "last_seen": None,
            "job_ids": set(),
        })
        job_areas: dict[tuple[int, str], dict] = defaultdict(lambda: {
            "frequency": 0, "source_ids": set(), "confidence": 0.0,
            "importance": 0.0, "first_seen": None, "last_seen": None,
        })
        for (standard_job_id, skill_id), stat in job_skill_stats.items():
            aggregate = skill_stats[skill_id]
            aggregate["frequency"] += stat["frequency"]
            aggregate["source_ids"].update(stat["source_ids"])
            aggregate["confidence"] = max(aggregate["confidence"], stat["confidence"])
            aggregate["importance"] = max(aggregate["importance"], stat["importance"])
            aggregate["first_seen"] = min(
                filter(None, (aggregate["first_seen"], stat["first_seen"]))
            )
            aggregate["last_seen"] = max(
                filter(None, (aggregate["last_seen"], stat["last_seen"]))
            )
            aggregate["job_ids"].add(f"job:{standard_job_id}")
        # Replace the basic area-to-skill edges with full fact aggregates.
        edges["CONTAINS"] = []
        for skill_id, stat in skill_stats.items():
            skill = skills[skill_id]
            edges["CONTAINS"].append(self._edge(
                f"area:{skill.category}", f"skill:{skill.id}",
                frequency=stat["frequency"], sourceCount=len(stat["source_ids"]),
                confidence=stat["confidence"], importance=stat["importance"],
                firstSeenAt=stat["first_seen"].isoformat(),
                lastSeenAt=stat["last_seen"].isoformat(),
                jobIds=sorted(stat["job_ids"]),
                sourceIds=sorted(stat["source_ids"]),
            ))
        for (job_id, skill_id), stat in job_skill_stats.items():
            skill = skills[skill_id]
            area_stat = job_areas[(job_id, skill.category)]
            area_stat["frequency"] += stat["frequency"]
            area_stat["source_ids"].update(stat["source_ids"])
            area_stat["confidence"] = max(area_stat["confidence"], stat["confidence"])
            area_stat["importance"] = max(area_stat["importance"], stat["importance"])
            area_stat["first_seen"] = min(
                filter(None, (area_stat["first_seen"], stat["first_seen"]))
            )
            area_stat["last_seen"] = max(
                filter(None, (area_stat["last_seen"], stat["last_seen"]))
            )
        for (job_id, category), stat in job_areas.items():
            edges["REQUIRES_AREA"].append(self._edge(
                f"job:{job_id}", f"area:{category}",
                frequency=stat["frequency"], sourceCount=len(stat["source_ids"]),
                confidence=stat["confidence"], importance=stat["importance"],
                firstSeenAt=stat["first_seen"].isoformat(),
                lastSeenAt=stat["last_seen"].isoformat(),
                sourceIds=sorted(stat["source_ids"]),
            ))
        for document_id, job_id, skill_id in support_pairs:
            document = documents.get(document_id)
            if not document:
                continue
            nodes["SourceDocument"].append(self._node(
                f"source:{document.id}", name=document.title, canonicalKey=document.content_fingerprint,
                stack=job_by_id[job_id].stack, level=job_by_id[job_id].level,
                description=document.content_summary[:500], source=document.source, url=document.url,
            ))
            edges["SUPPORTS"].append(self._edge(f"source:{document_id}", f"skill:{skill_id}"))
            edges["SUPPORTS"].append(self._edge(f"source:{document_id}", f"job:{job_id}"))

        nodes["GraphSnapshot"].append(self._node(
            "snapshot:current", name=snapshot.version, canonicalKey="current",
            snapshotId=snapshot.id, description=f"{snapshot.snapshot_type} graph snapshot",
        ))
        for job in standard_jobs:
            edges["HAS_SNAPSHOT"].append(self._edge(
                f"job:{job.id}", "snapshot:current", version=snapshot.version,
                snapshotId=snapshot.id,
            ))
        # Deduplicate source nodes and edges generated by repeated facts.
        for label, rows in nodes.items():
            nodes[label] = list({row["id"]: row for row in rows}.values())
        for relation, rows in edges.items():
            edges[relation] = list({
                (row["source"], row["target"]): row for row in rows
            }.values())
        return nodes, edges, len(job_skill_stats)

    async def _append_verified_deep_nodes(
        self, snapshot_id, nodes, edges, skills: dict[int, Skill] | None = None
    ) -> tuple[int, int, list[int], list[int]]:
        logger = logging.getLogger(__name__)
        candidates = list((await self.db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.review_status == "approved",
                GraphEnrichmentCandidate.publication_status.in_(("approved", "published")),
            ).order_by(
                GraphEnrichmentCandidate.skill_id,
                GraphEnrichmentCandidate.updated_at.desc(),
                GraphEnrichmentCandidate.id.desc(),
            )
        )).scalars())
        latest_by_skill: dict[int, GraphEnrichmentCandidate] = {}
        for candidate in candidates:
            latest_by_skill.setdefault(candidate.skill_id, candidate)
        superseded_candidate_ids = [
            candidate.id
            for candidate in candidates
            if latest_by_skill[candidate.skill_id].id != candidate.id
        ]
        candidates = list(latest_by_skill.values())
        tech_points = 0
        knowledge_points = 0
        candidate_ids: list[int] = []
        skills = skills or {}
        # 跨候选全局收集：同一归一化 key（含变体 "MyBatis" vs "MyBatis持久层框架"）
        # 节点只生成一个（最短展示名），但每个 skill 各保留一条 REFINES_TO（多父共享）。
        point_entries: dict[str, list[tuple[Skill, TechPointOutput]]] = defaultdict(list)
        collected_knowledge: dict[tuple[str, str], tuple[str, KnowledgePointOutput]] = {}
        for candidate in candidates:
            skill = skills.get(candidate.skill_id) or await self.db.get(Skill, candidate.skill_id)
            if not skill:
                logger.warning("graph_enrichment: candidate skill_id=%d not found", candidate.skill_id)
                continue
            output = GraphEnrichmentOutput.model_validate(candidate.candidate_data)
            candidate_ids.append(candidate.id)
            for point in self._dedupe_by_name(output.tech_points):
                point_key = self._normalize_name_key(
                    point.name, level="tech_point"
                )
                point_entries[point_key].append((skill, point))
            for point in self._dedupe_by_name(output.tech_points):
                point_key = self._normalize_name_key(
                    point.name, level="tech_point"
                )
                for knowledge in self._dedupe_by_name(
                    point.knowledge_points, level="knowledge_point"
                ):
                    if knowledge.confidence < 0.75 or len(set(knowledge.evidence_ids)) < 2:
                        continue
                    knowledge_key = self._normalize_name_key(
                        knowledge.name, level="knowledge_point"
                    )
                    k_id = (point_key, knowledge_key)
                    existing = collected_knowledge.get(k_id)
                    if existing is None or len(knowledge.name or "") < len(existing[1].name or ""):
                        collected_knowledge[k_id] = (point_key, knowledge)
        for point_key, entries in point_entries.items():
            # 展示名取同 key 组内最短（更接近标准专有名），stack 取该条目
            skill, point = min(entries, key=lambda e: len(e[1].name or ""))
            # L4 节点 id 基于归一化名称的确定性 hash：跨技能候选生成同名
            # 或同义变体技术点时 MERGE 到同一节点（多 skill 通过 REFINES_TO 共享）
            point_id = f"point:{point_key}"
            nodes["TechPoint"].append(self._node(
                point_id, name=point.name, canonicalKey=point_id,
                stack=CATEGORY_STACK.get(skill.category, "backend"), level="middle",
                description=point.detail, importance=point.confidence,
                evidence_ids=list(dict.fromkeys(point.evidence_ids)),
                source_count=len(set(point.evidence_ids)),
            ))
            edges["REFINES_TO"].extend(
                self._edge(
                    f"skill:{entry_skill.id}", point_id,
                    confidence=entry_point.confidence,
                    sourceCount=len(set(entry_point.evidence_ids)),
                )
                for entry_skill, entry_point in entries
            )
            tech_points += 1
            for (point_key2, knowledge_key), (_, knowledge) in collected_knowledge.items():
                if point_key2 != point_key:
                    continue
                # L5 节点 id 在所属 L4 下按归一化名称 hash 唯一
                knowledge_id = f"knowledge:{point_key}:{knowledge_key}"
                nodes["KnowledgePoint"].append(self._node(
                    knowledge_id, name=knowledge.name, canonicalKey=knowledge_id,
                    stack=CATEGORY_STACK.get(skill.category, "backend"), level="middle",
                    description=knowledge.description, difficulty=knowledge.difficulty,
                    core_stack=knowledge.core_stack,
                    common_solutions=[solution.model_dump(mode="json") for solution in knowledge.common_solutions],
                    importance=knowledge.confidence,
                    evidence_ids=list(dict.fromkeys(knowledge.evidence_ids)),
                    source_count=len(set(knowledge.evidence_ids)),
                ))
                edges["HAS_KNOWLEDGE"].append(self._edge(
                    point_id, knowledge_id, confidence=knowledge.confidence,
                    sourceCount=len(set(knowledge.evidence_ids)),
                ))
                knowledge_points += 1
        logger.info(
            "graph_enrichment: appended tech_points=%d knowledge_points=%d for snapshot=%s",
            tech_points, knowledge_points, snapshot_id,
        )
        return tech_points, knowledge_points, candidate_ids, superseded_candidate_ids

    @staticmethod
    def _name_key(name: str) -> str:
        """L4 技术点名称的全局唯一 key（默认层级，兼容旧调用）。"""
        return GraphService._normalize_name_key(name, level="tech_point")

    @staticmethod
    def _normalize_name_key(name: str, *, level: str) -> str:
        """L4/L5 名称归一化 key：strip+casefold → 按层级剥修饰后缀 →
        canonical_key 字符压缩 → sha256 前缀（12 hex）。

        - tech_point：剥复合/单修饰后缀（"MyBatis持久层框架"→"MyBatis"）；
        - knowledge_point：仅剥课程式后缀（详解/实战/入门/进阶/原理），
          避免误伤概念短语（如 "Git 三区模型" 不剥"模型"）；
        - 守卫：剥离后非空且剩余长度 ≥2。
        """
        normalized = (name or "").strip().casefold().replace(" ", "")
        if not normalized:
            return ""
        stripped = normalized
        suffixes: tuple[str, ...] = ()
        if level == "tech_point":
            for suffix in GraphService._L4_COMPOUND_SUFFIXES:
                if stripped.endswith(suffix) and len(stripped) - len(suffix) >= 2:
                    stripped = stripped[: -len(suffix)]
                    break
            for suffix in GraphService._L4_SUFFIXES:
                if stripped.endswith(suffix) and len(stripped) - len(suffix) >= 2:
                    stripped = stripped[: -len(suffix)]
                    break
        else:
            for suffix in GraphService._L5_SUFFIXES:
                if stripped.endswith(suffix) and len(stripped) - len(suffix) >= 2:
                    stripped = stripped[: -len(suffix)]
                    break
        key = canonical_key(stripped) if stripped else stripped
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _dedupe_by_name(items, *, level: str = "tech_point") -> list:
        """按归一化名称 key 去重（保留首次出现）。

        L4/L5 节点的 id 由规范化名称 hash 构成，Neo4j MERGE 只认该 id——
        同名/同义变体（"MyBatis" vs "MyBatis持久层框架"）会生成多个独立
        节点。写入前按归一化 key 去重可根治图谱重复技术点。
        """
        seen: dict[str, object] = {}
        for item in items:
            key = GraphService._normalize_name_key(
                item.name or "", level=level
            )
            if not key:
                continue
            existing = seen.get(key)
            if existing is None:
                seen[key] = item
                continue
            # 同 key 变体（"MyBatis" vs "MyBatis持久层框架"）：
            # 优先保留更短名称（更接近标准专有名的展示名）
            if len(item.name or "") < len(existing.name or ""):
                seen[key] = item
        return list(seen.values())

    async def list_enrichment_candidates(
        self, *, page: int, page_size: int, review_status: str | None,
    ) -> dict:
        filters = []
        if review_status:
            filters.append(GraphEnrichmentCandidate.review_status == review_status)
        total = int(await self.db.scalar(
            select(func.count(GraphEnrichmentCandidate.id)).where(*filters)
        ) or 0)
        rows = (await self.db.execute(
            select(GraphEnrichmentCandidate, Skill.name)
            .join(Skill, Skill.id == GraphEnrichmentCandidate.skill_id)
            .where(*filters)
            .order_by(GraphEnrichmentCandidate.created_at.desc(), GraphEnrichmentCandidate.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all()
        pending_candidates = list((await self.db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.review_status == "pending"
            )
        )).scalars())
        return {
            "items": [self._candidate_response(candidate, skill_name) for candidate, skill_name in rows],
            "total": total, "page": page, "page_size": page_size,
            "machine_failed_pending_count": sum(
                self._resolved_machine_status(candidate) not in {"passed", "pending"}
                for candidate in pending_candidates
            ),
        }

    async def auto_approve_enrichment_candidates(
        self, *, snapshot_id: str, minimum_confidence: float
    ) -> list[int]:
        """Promote only strongly grounded machine candidates for publication.

        This is intentionally stricter than the manual approval endpoint: the
        candidate must pass grounding, meet the confidence threshold, cite at
        least two evidence chunks and contain both L4 and L5 output.  Anything
        ambiguous stays pending for an administrator.
        """
        rows = list((await self.db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.snapshot_id == snapshot_id,
                GraphEnrichmentCandidate.review_status == "pending",
                GraphEnrichmentCandidate.publication_status == "draft",
                GraphEnrichmentCandidate.machine_validation_status == "passed",
                GraphEnrichmentCandidate.verification_status == "machine_validated",
                GraphEnrichmentCandidate.confidence >= minimum_confidence,
            )
        )).scalars())
        approved_at = utc_now_naive()
        approved_ids: list[int] = []
        for candidate in rows:
            data = candidate.candidate_data or {}
            tech_points = data.get("tech_points") or []
            knowledge_count = sum(
                len(point.get("knowledge_points") or [])
                for point in tech_points
                if isinstance(point, dict)
            )
            if len(set(candidate.evidence_source_ids or [])) < 2:
                continue
            if not tech_points or knowledge_count == 0:
                continue
            validation = data.get("machine_validation") or {}
            if int(validation.get("rejected_count") or 0) > 0:
                continue
            candidate.review_status = "approved"
            candidate.publication_status = "approved"
            candidate.verification_status = "verified"
            candidate.reviewed_at = approved_at
            candidate.review_note = (
                f"automatic quality gate: confidence>={minimum_confidence:.2f}, "
                "grounding passed, multi-evidence L4/L5"
            )
            candidate.lock_version += 1
            approved_ids.append(candidate.id)
        await self.db.flush()
        return approved_ids

    async def review_enrichment_candidate(
        self, candidate_id: int, *, action: str, note: str | None,
        lock_version: int, user_id: int,
    ) -> dict:
        candidate = await self.db.get(GraphEnrichmentCandidate, candidate_id)
        if candidate is None:
            raise ResourceNotFoundError("L4/L5 补充候选不存在")
        if candidate.lock_version != lock_version:
            raise InvalidParameterError("候选已被其他审核操作更新，请刷新后重试")
        if action == "approve" and candidate.machine_validation_status != "passed":
            raise InvalidParameterError("只有机器校验通过的候选可以批准")
        candidate.review_status = "approved" if action == "approve" else "rejected"
        candidate.publication_status = "approved" if action == "approve" else "rejected"
        candidate.verification_status = "verified" if action == "approve" else "rejected"
        candidate.reviewed_by = user_id
        candidate.reviewed_at = utc_now_naive()
        candidate.review_note = (note or "").strip() or (
            self._machine_rejection_note(candidate) if action == "reject" else None
        )
        candidate.lock_version += 1
        await self.db.flush()
        await self.db.refresh(candidate)
        skill = await self.db.get(Skill, candidate.skill_id)
        response = self._candidate_response(
            candidate, skill.name if skill else f"技能 {candidate.skill_id}"
        )
        await self.db.commit()
        return response

    async def reject_machine_failed_candidates(self, *, user_id: int) -> list[int]:
        """驳回所有已经得到机器失败终态、但仍等待人工处理的候选。"""
        candidates = list((await self.db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.review_status == "pending"
            ).order_by(GraphEnrichmentCandidate.id)
        )).scalars())
        rejected_at = utc_now_naive()
        rejected_ids: list[int] = []
        for candidate in candidates:
            if self._resolved_machine_status(candidate) in {"passed", "pending"}:
                continue
            candidate.review_status = "rejected"
            candidate.publication_status = "rejected"
            candidate.verification_status = "rejected"
            candidate.reviewed_by = user_id
            candidate.reviewed_at = rejected_at
            candidate.review_note = self._machine_rejection_note(candidate)
            candidate.lock_version += 1
            rejected_ids.append(candidate.id)
        await self.db.commit()
        return rejected_ids

    async def prepare_enrichment_publication(self, candidate_ids: list[int]) -> int:
        query = select(GraphEnrichmentCandidate).where(
            GraphEnrichmentCandidate.review_status == "approved",
            GraphEnrichmentCandidate.publication_status == "approved",
        )
        if candidate_ids:
            query = query.where(GraphEnrichmentCandidate.id.in_(candidate_ids))
        rows = list((await self.db.execute(query)).scalars())
        if candidate_ids and len(rows) != len(set(candidate_ids)):
            raise InvalidParameterError("选中的候选包含未批准或不存在的记录")
        if not rows:
            raise InvalidParameterError("当前没有可发布的 L4/L5 候选")
        for row in rows:
            row.publication_status = "approved"
        await self.db.commit()
        return len(rows)

    @staticmethod
    def _candidate_response(candidate: GraphEnrichmentCandidate, skill_name: str) -> dict:
        machine_status = GraphService._resolved_machine_status(candidate)
        return {
            "id": candidate.id, "snapshot_id": candidate.snapshot_id,
            "skill_id": candidate.skill_id, "skill_name": skill_name,
            "candidate_data": candidate.candidate_data or {},
            "evidence_source_ids": [str(value) for value in (candidate.evidence_source_ids or [])],
            "confidence": candidate.confidence,
            "machine_validation_status": machine_status,
            "review_status": candidate.review_status,
            "publication_status": candidate.publication_status,
            "review_note": candidate.review_note, "reviewed_at": candidate.reviewed_at,
            "published_at": candidate.published_at, "lock_version": candidate.lock_version,
            "agent_run_id": candidate.agent_run_id, "created_at": candidate.created_at,
            "updated_at": candidate.updated_at,
        }

    @staticmethod
    def _resolved_machine_status(candidate: GraphEnrichmentCandidate) -> str:
        status = candidate.machine_validation_status
        if status != "pending":
            return status
        return {
            "llm_disabled": "skipped",
            "retrieval_unavailable": "retrieval_failed",
            "insufficient_evidence": "insufficient_evidence",
            "insufficient_grounding": "failed",
            "llm_failed": "failed",
            "llm_timeout": "failed",
        }.get((candidate.candidate_data or {}).get("reason"), status)

    @staticmethod
    def _machine_rejection_note(candidate: GraphEnrichmentCandidate) -> str:
        data = candidate.candidate_data or {}
        reason = data.get("reason")
        if reason == "insufficient_evidence":
            sources = "、".join(str(value) for value in data.get("sources") or [])
            detail = f"（当前来源：{sources}）" if sources else ""
            return f"机器审核未通过：独立证据来源不足，未达到双来源门槛{detail}"[:500]
        if reason == "insufficient_grounding":
            report = data.get("machine_validation") or {}
            rejected = int(report.get("rejected_claim_count") or 0)
            suffix = f"，{rejected} 条技术陈述未被证据支持" if rejected else ""
            return f"机器审核未通过：生成内容未通过证据引用校验{suffix}"[:500]
        if reason in {"llm_failed", "llm_timeout"}:
            error = str(data.get("error") or "模型未返回可用的结构化技术内容")
            return f"机器审核未通过：模型生成失败（{error}）"[:500]
        if reason == "llm_disabled":
            return "机器审核未通过：模型服务未配置，本次未生成可审核的 L4/L5 技术内容"
        if reason == "retrieval_unavailable":
            return "机器审核未通过：证据检索服务不可用，无法形成可验证的技术内容"
        labels = {
            "failed": "机器生成或证据校验失败",
            "skipped": "机器任务已跳过，未形成可审核技术内容",
            "retrieval_failed": "证据检索失败，无法形成可验证技术内容",
            "insufficient_evidence": "独立证据不足，未达到发布门槛",
        }
        status = GraphService._resolved_machine_status(candidate)
        return f"机器审核未通过：{labels.get(status, '未达到机器审核发布门槛')}"[:500]

    def _write_payload(self, nodes, edges, version: str, mode: str) -> None:
        self.graph.ensure_schema()
        for label, rows in nodes.items():
            self.graph.merge_nodes(label, rows, version)
        for relation, rows in edges.items():
            self.graph.merge_edges(relation, rows, version)
        if mode == "full":
            self.graph.cleanup_stale(version)

    async def panorama(self, **filters) -> GraphSubgraph:
        limit = min(int(filters.pop("limit", 1000)), 1000)
        filters["include_auxiliary"] = filters.get("node_type") in {
            "SourceDocument", "GraphSnapshot"
        }
        rows = await asyncio.to_thread(self.graph.query_nodes, limit=limit + 1, **filters)
        truncated = len(rows) > limit
        rows = rows[:limit]
        edges = await asyncio.to_thread(self.graph.query_edges, [row["id"] for row in rows])
        return self._subgraph(rows, edges, truncated=truncated)

    async def overview(
        self, *, cursor: str | None, page_size: int, max_layer: int,
        keyword: str | None = None, stack: str | None = None,
        level: str | None = None,
    ) -> GraphSubgraph:
        offset = self._decode_cursor(cursor)
        seeds = await asyncio.to_thread(
            self.graph.query_overview_jobs,
            offset=offset, page_size=page_size, keyword=keyword,
            stack=stack, level=level,
        )
        has_more = len(seeds) > page_size
        seeds = seeds[:page_size]
        nodes, edges = await asyncio.to_thread(
            self.graph.query_overview_context,
            [row["id"] for row in seeds], max_layer,
        )
        return self._subgraph(
            nodes, edges, truncated=has_more, has_more=has_more,
            next_cursor=self._encode_cursor(offset + page_size) if has_more else None,
            query_scope=f"overview:L1-L{max_layer}",
        )

    async def node(self, node_id: str) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(self.graph.expand, node_id, 1, 100)
        if not nodes:
            raise ResourceNotFoundError("图谱节点不存在")
        return self._subgraph(nodes, edges)

    async def expand(self, node_id: str, depth: int, limit: int) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(self.graph.expand, node_id, depth, limit + 1)
        truncated = len(nodes) > limit
        return self._subgraph(nodes[:limit], edges, truncated=truncated)

    async def neighbors(
        self, node_id: str, *, cursor: str | None, page_size: int, max_layer: int,
    ) -> GraphSubgraph:
        offset = self._decode_cursor(cursor)
        nodes, edges = await asyncio.to_thread(
            self.graph.query_neighbors,
            node_id=node_id, offset=offset, page_size=page_size, max_layer=max_layer,
        )
        if not nodes:
            # Distinguish a leaf from a missing node through the existing detail query.
            detail = await self.node(node_id)
            return self._subgraph(
                [self._schema_node_row(detail.nodes[0])], [],
                query_scope=f"neighbors:L1-L{max_layer}",
            )
        has_more = len(nodes) - 1 > page_size
        kept_nodes = nodes[:page_size + 1]
        kept_ids = {row["id"] for row in kept_nodes}
        kept_edges = [
            row for row in edges
            if row["source"] in kept_ids and row["target"] in kept_ids
        ]
        return self._subgraph(
            kept_nodes, kept_edges, truncated=has_more, has_more=has_more,
            next_cursor=self._encode_cursor(offset + page_size) if has_more else None,
            query_scope=f"neighbors:L1-L{max_layer}",
        )

    async def search(self, query: str, node_type: str | None, limit: int) -> GraphSubgraph:
        rows = await asyncio.to_thread(
            self.graph.search_nodes, query=query, node_type=node_type, limit=limit,
        )
        edges = await asyncio.to_thread(self.graph.query_edges, [row["id"] for row in rows])
        return self._subgraph(rows, edges)

    async def path(self, from_id: str, to_id: str, max_depth: int) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(self.graph.path, from_id, to_id, max_depth)
        return self._subgraph(nodes, edges)

    async def job_tree(self, job_id: int, depth: int) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(self.graph.job_tree, f"job:{job_id}", depth)
        if not nodes:
            raise ResourceNotFoundError("标准岗位图谱不存在")
        return self._subgraph(nodes, edges)

    async def list_snapshots(self) -> list[GraphSnapshotResponse]:
        return [self._snapshot_response(row) for row in await self.audit.list_snapshots()]

    async def get_snapshot(self, snapshot_id: str) -> GraphSnapshotResponse:
        row = await self.audit.get_snapshot(snapshot_id)
        if not row:
            raise ResourceNotFoundError("图谱快照不存在")
        return self._snapshot_response(row)

    def _subgraph(
        self, rows, edge_rows, *, truncated=False, has_more=False,
        next_cursor: str | None = None, query_scope: str | None = None,
        total_available: int | None = None,
    ) -> GraphSubgraph:
        nodes = []
        for row in rows:
            props = dict(row["properties"])
            props.pop("namespace", None)
            props.pop("syncVersion", None)
            common_solutions = props.get("common_solutions")
            if isinstance(common_solutions, str):
                try:
                    decoded = json.loads(common_solutions)
                    props["common_solutions"] = decoded if isinstance(decoded, list) else []
                except json.JSONDecodeError:
                    logger.warning("graph_node_invalid_common_solutions node_id=%s", row["id"])
                    props["common_solutions"] = []
            nodes.append(GraphNode(
                id=row["id"], type=row["type"], name=props.pop("name", None) or row["id"],
                stack=props.pop("stack", None), level=props.pop("level", None),
                description=props.pop("description", ""),
                importance=props.pop("importance", None),
                frequency=props.pop("frequency", None), properties=props,
            ))
        self._layout(nodes)
        node_ids = {node.id for node in nodes}
        edges = [
            GraphEdge(
                id=f"{row['relation']}:{row['source']}:{row['target']}",
                source=row["source"], target=row["target"], relation=row["relation"],
                properties={
                    key: value for key, value in row.get("properties", {}).items()
                    if key not in {"namespace", "syncVersion"}
                },
            )
            for row in edge_rows
            if row["source"] in node_ids and row["target"] in node_ids
        ]
        return GraphSubgraph(
            nodes=nodes, edges=edges, node_count=len(nodes), edge_count=len(edges),
            truncated=truncated, returned=len(nodes), total_available=total_available,
            next_cursor=next_cursor, has_more=has_more, query_scope=query_scope,
        )

    @staticmethod
    def _encode_cursor(offset: int) -> str:
        return base64.urlsafe_b64encode(f"offset:{offset}".encode()).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int:
        if not cursor:
            return 0
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            value = base64.urlsafe_b64decode(padded.encode()).decode()
            prefix, raw_offset = value.split(":", 1)
            if prefix != "offset":
                raise ValueError
            return max(int(raw_offset), 0)
        except (ValueError, UnicodeDecodeError):
            return 0

    @staticmethod
    def _schema_node_row(node: GraphNode) -> dict:
        return {
            "id": node.id,
            "type": node.type,
            "properties": {
                "name": node.name, "stack": node.stack, "level": node.level,
                "description": node.description, "importance": node.importance,
                "frequency": node.frequency, **node.properties,
            },
        }

    @staticmethod
    def _layout(nodes: list[GraphNode]) -> None:
        columns = {
            "Job": 110, "SkillArea": 290, "TechStack": 470,
            "TechPoint": 650, "KnowledgePoint": 830,
            "SourceDocument": 470, "GraphSnapshot": 110,
        }
        grouped: dict[str, list[GraphNode]] = defaultdict(list)
        for node in nodes:
            grouped[node.type].append(node)
        for node_type, items in grouped.items():
            items.sort(key=lambda item: (item.stack or "", item.name))
            step = max(42, 500 / (len(items) + 1))
            for index, node in enumerate(items, 1):
                node.x = columns[node_type]
                node.y = min(500, round(index * step, 2))

    @staticmethod
    def _node(node_id: str, **properties) -> dict:
        return {"id": node_id, "properties": {k: v for k, v in properties.items() if v is not None}}

    @staticmethod
    def _edge(source: str, target: str, **properties) -> dict:
        return {"source": source, "target": target, "properties": properties}

    @staticmethod
    def _snapshot_response(row: GraphSnapshot) -> GraphSnapshotResponse:
        return GraphSnapshotResponse(
            id=row.id, version=row.version, snapshot_type=row.snapshot_type,
            status=row.status, node_count=row.node_count, edge_count=row.edge_count,
            fact_count=row.fact_count, metadata=row.metadata_json or {},
            created_at=row.created_at, completed_at=row.completed_at,
        )


class GraphTaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_sync(
        self, *, mode: str, enrich_top_skills: bool, user_id: int,
        run_eager_in_background: bool = False,
    ) -> TaskStatusResponse:
        from app.core.config import CELERY_TASK_ALWAYS_EAGER
        from app.tasks.graph_sync import _process_graph_sync, process_graph_sync

        task = AsyncTask(
            id=str(uuid.uuid4()), task_type="graph_sync", status=TaskStatus.queued.value, progress=0,
            request_data={"mode": mode, "enrich_top_skills": enrich_top_skills},
            created_by=user_id,
        )
        self.db.add(task)
        await self.db.commit()
        if CELERY_TASK_ALWAYS_EAGER:
            if run_eager_in_background:
                local_task = asyncio.create_task(
                    _process_graph_sync(task.id, mode, enrich_top_skills, user_id),
                    name=f"graph-sync-{task.id}",
                )
                _local_graph_tasks.add(local_task)
                local_task.add_done_callback(self._finish_local_task)
            else:
                await _process_graph_sync(task.id, mode, enrich_top_skills, user_id)
        else:
            process_graph_sync.delay(task.id, mode, enrich_top_skills, user_id)
        await self.db.refresh(task)
        return TaskStatusResponse(
            task_id=task.id, task_type=task.task_type, status=task.status,
            progress=task.progress, result=task.result, error_code=task.error_code,
            error_message=task.error_message, created_at=task.created_at,
            started_at=task.started_at, finished_at=task.finished_at,
        )

    async def create_sync_in_background(
        self, *, mode: str, enrich_top_skills: bool, user_id: int,
    ) -> TaskStatusResponse:
        """审核通过后的自动流转：进程内后台执行图谱同步，不依赖 Celery/Redis。

        与 create_sync 的区别：无论 CELERY_TASK_ALWAYS_EAGER 如何配置，都使用
        asyncio.create_task 在 FastAPI 进程内异步执行 _process_graph_sync，
        保证"审核通过即入库可查询"不因 Celery Worker 未启动而卡在 queued。
        """
        from app.tasks.graph_sync import _process_graph_sync

        task = AsyncTask(
            id=str(uuid.uuid4()), task_type="graph_sync",
            status=TaskStatus.queued.value, progress=0,
            request_data={
                "mode": mode,
                "enrich_top_skills": enrich_top_skills,
                "auto_triggered": True,
            },
            created_by=user_id,
        )
        self.db.add(task)
        await self.db.commit()
        local_task = asyncio.create_task(
            _process_graph_sync(task.id, mode, enrich_top_skills, user_id),
            name=f"graph-sync-auto-{task.id}",
        )
        _local_graph_tasks.add(local_task)
        local_task.add_done_callback(self._finish_local_task)
        await self.db.refresh(task)
        return TaskStatusResponse(
            task_id=task.id, task_type=task.task_type, status=task.status,
            progress=task.progress, result=task.result, error_code=task.error_code,
            error_message=task.error_message, created_at=task.created_at,
            started_at=task.started_at, finished_at=task.finished_at,
        )

    @staticmethod
    def _finish_local_task(task: asyncio.Task) -> None:
        _local_graph_tasks.discard(task)
        if task.cancelled():
            return
        # 读取异常，避免后台任务产生 "Task exception was never retrieved"；
        # _process_graph_sync 已经把失败详情持久化到 AsyncTask。
        task.exception()
