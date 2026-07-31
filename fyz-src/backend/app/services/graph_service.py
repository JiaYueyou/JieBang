"""标准岗位聚合、图谱同步、深层补全与查询服务。"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DEEPSEEK_TIMEOUT_SECONDS
from app.core.agent_runtime import SkillGraphCompletionAgent
from app.core.exceptions import ResourceNotFoundError
from app.core.time import utc_now, utc_now_naive
from app.domain.job_standardizer import CATEGORY_STACK, infer_job_stack, standardize_job_title
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
)
from app.schemas.retrieval import RetrievalSearchRequest, RetrievalSearchResponse
from app.schemas.skill import TaskStatusResponse
from app.services.agent_grounding_service import (
    AgentGroundingReport,
    AgentGroundingService,
    GroundedClaim,
)
from app.services.retrieval_service import RetrievalService


class GraphService:
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
            self.llm, timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS
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
                name, key, level, confidence = standardize_job_title(title)
                standard = await self.audit.get_standard_job(key)
                if not standard:
                    standard = StandardJob(
                        name=name,
                        canonical_key=key,
                        aliases=[],
                        stack=infer_job_stack(name),
                        level=level,
                        description=f"由多来源岗位数据聚合形成的{name}能力模型。",
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
                link = await self.audit.get_source(source_type, row.id)
                if not link:
                    self.db.add(StandardJobSource(
                        standard_job_id=standard.id,
                        source_type=source_type,
                        source_id=row.id,
                        original_title=row.title,
                        confidence=confidence,
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
    ) -> dict:
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
            standard_count = await self.aggregate_standard_jobs()
            batch.progress = 20
            await self.db.commit()
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
                    await self._prepare_top_candidates(snapshot_id, user_id)
                )
            batch.progress = 45
            await self.db.commit()
            nodes, edges, fact_count = await self._build_payload(snapshot)
            tech_points, knowledge_points = await self._append_verified_deep_nodes(
                snapshot_id, nodes, edges
            )
            enrichment_stats["tech_points_written"] = tech_points
            enrichment_stats["knowledge_points_written"] = knowledge_points
            await asyncio.to_thread(self._write_payload, nodes, edges, version, mode)
            counts = await asyncio.to_thread(self.graph.counts)
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

    async def _prepare_top_candidates(self, snapshot_id: str, user_id: int | None) -> dict[str, int]:
        logger = logging.getLogger(__name__)
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
        for skill, _coverage in rows:
            candidate = GraphEnrichmentCandidate(
                snapshot_id=snapshot_id,
                skill_id=skill.id,
                evidence_source_ids=[],
                candidate_data={"reason": "llm_disabled", "skill_name": skill.name},
                confidence=0,
                verification_status="unverified",
            )
            provider_enabled = bool(getattr(self.llm, "enabled", True))
            if not provider_enabled:
                candidate.candidate_data = {"reason": "llm_disabled", "skill_name": skill.name}
                stats["candidates_skipped"] += 1
                logger.info("graph_enrichment: skill=%s skipped (llm disabled)", skill.name)
                await self.audit.add_candidate(candidate)
                continue

            retrieval_query = f"{skill.name} 技术点 知识点 能力要求"
            try:
                retrieval = await self.retrieval.search(
                    RetrievalSearchRequest(
                        query=retrieval_query,
                        skill_ids=[skill.id],
                        top_k=12,
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
                stats["candidates_skipped"] += 1
                logger.warning(
                    "graph_enrichment: skill=%s skipped (retrieval unavailable: %s)",
                    skill.name,
                    type(exc).__name__,
                )
                await self.audit.add_candidate(candidate)
                continue

            candidate.evidence_source_ids = [
                item.evidence_id for item in retrieval.items
            ]
            independent_sources = {
                item.source_platform.strip().casefold()
                for item in retrieval.items
            }
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
                stats["candidates_skipped"] += 1
                logger.info(
                    "graph_enrichment: skill=%s skipped (insufficient evidence: %d sources, %d platforms)",
                    skill.name, len(retrieval.items), len(independent_sources),
                )
            else:
                await self._enrich_candidate(
                    candidate,
                    skill,
                    retrieval,
                    user_id,
                )
                if candidate.candidate_data.get("reason") == "llm_failed":
                    stats["candidates_failed"] += 1
                    logger.warning("graph_enrichment: skill=%s enrichment failed", skill.name)
                elif candidate.verification_status == "machine_validated":
                    stats["candidates_machine_validated"] += 1
                    logger.info(
                        "graph_enrichment: skill=%s machine validated",
                        skill.name,
                    )
                else:
                    stats["candidates_skipped"] += 1
                    logger.info("graph_enrichment: skill=%s filtered out", skill.name)
            await self.audit.add_candidate(candidate)
        logger.info(
            "graph_enrichment: snapshot=%s total=%d machine_validated=%d failed=%d skipped=%d",
            snapshot_id,
            stats["candidates_total"],
            stats["candidates_machine_validated"],
            stats["candidates_failed"],
            stats["candidates_skipped"],
        )
        return stats

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
                "text": item.chunk_text[:2000],
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
            candidate.candidate_data = {"reason": "llm_failed", "error": str(exc)[:500]}
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
                "fallback_reason": "llm_failed",
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
                        claim_text=f"{item.name}\n{item.description}",
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
        return (
            output.model_copy(update={"tech_points": accepted_points}),
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
    ) -> tuple[int, int]:
        logger = logging.getLogger(__name__)
        candidates = list((await self.db.execute(
            select(GraphEnrichmentCandidate).where(
                GraphEnrichmentCandidate.snapshot_id == snapshot_id,
                GraphEnrichmentCandidate.verification_status == "verified",
            )
        )).scalars())
        tech_points = 0
        knowledge_points = 0
        skills = skills or {}
        for candidate in candidates:
            skill = skills.get(candidate.skill_id) or await self.db.get(Skill, candidate.skill_id)
            if not skill:
                logger.warning("graph_enrichment: candidate skill_id=%d not found", candidate.skill_id)
                continue
            output = GraphEnrichmentOutput.model_validate(candidate.candidate_data)
            for point_index, point in enumerate(output.tech_points):
                point_id = f"point:{skill.id}:{point_index}"
                nodes["TechPoint"].append(self._node(
                    point_id, name=point.name, canonicalKey=point_id,
                    stack=CATEGORY_STACK.get(skill.category, "backend"), level="middle",
                    description=point.detail, importance=point.confidence,
                ))
                edges["REFINES_TO"].append(self._edge(
                    f"skill:{skill.id}", point_id, confidence=point.confidence,
                    sourceCount=len(set(point.evidence_ids)),
                ))
                tech_points += 1
                for knowledge_index, knowledge in enumerate(point.knowledge_points):
                    if knowledge.confidence < 0.75 or len(set(knowledge.evidence_ids)) < 2:
                        continue
                    knowledge_id = f"knowledge:{skill.id}:{point_index}:{knowledge_index}"
                    nodes["KnowledgePoint"].append(self._node(
                        knowledge_id, name=knowledge.name, canonicalKey=knowledge_id,
                        stack=CATEGORY_STACK.get(skill.category, "backend"), level="middle",
                        description=knowledge.description, difficulty=knowledge.difficulty,
                        importance=knowledge.confidence,
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
        return tech_points, knowledge_points

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

    async def node(self, node_id: str) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(self.graph.expand, node_id, 1, 100)
        if not nodes:
            raise ResourceNotFoundError("图谱节点不存在")
        return self._subgraph(nodes, edges)

    async def expand(self, node_id: str, depth: int, limit: int) -> GraphSubgraph:
        nodes, edges = await asyncio.to_thread(self.graph.expand, node_id, depth, limit + 1)
        truncated = len(nodes) > limit
        return self._subgraph(nodes[:limit], edges, truncated=truncated)

    async def search(self, query: str, node_type: str | None, limit: int) -> GraphSubgraph:
        rows = await asyncio.to_thread(
            self.graph.query_nodes, keyword=query, node_type=node_type, limit=limit,
            include_auxiliary=True,
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

    def _subgraph(self, rows, edge_rows, *, truncated=False) -> GraphSubgraph:
        nodes = []
        for row in rows:
            props = dict(row["properties"])
            props.pop("namespace", None)
            props.pop("syncVersion", None)
            nodes.append(GraphNode(
                id=row["id"], type=row["type"], name=props.pop("name", row["id"]),
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
            truncated=truncated,
        )

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
        self, *, mode: str, enrich_top_skills: bool, user_id: int
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
