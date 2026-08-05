"""标准技能查询、抽取和事实持久化服务。"""

from __future__ import annotations

import time
import uuid
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DEEPSEEK_TIMEOUT_SECONDS
from app.core.agent_runtime import SkillExtractionAgent
from app.core.exceptions import InvalidParameterError, ResourceNotFoundError
from app.core.time import utc_now, utc_now_naive
from app.domain.skill_dictionary import SKILL_DICT, canonical_key
from app.models import AgentRun, JobSkillFact
from app.providers import DeepSeekProvider, LLMProvider
from app.repositories import JobRepository, SkillRepository
from app.schemas.common import PageMeta
from app.schemas.skill import (
    ExtractedSkill,
    JobExtractionResult,
    SkillExtractionOutput,
    SkillFactResponse,
    SkillFactReviewItem,
    SkillFactReviewList,
    SkillFactReviewSummary,
    SkillSummary,
    VerificationStatus,
)
from app.services.job_service import JobService
from app.services.skill_extractor import RuleSkillExtractor, normalize_text


class SkillService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        repository: SkillRepository | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.db = db
        self.skills = repository or SkillRepository(db)
        self.jobs = JobRepository(db)
        self.extractor = RuleSkillExtractor()
        self.llm = llm_provider or DeepSeekProvider()
        self.enrichment_agent = SkillExtractionAgent(
            self.llm, timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS
        )

    async def list_skills(self, *, page: int, page_size: int, keyword: str | None, category: str | None):
        rows, total = await self.skills.list_skills(
            page=page, page_size=page_size, keyword=keyword, category=category
        )
        return [self._skill_summary(row) for row in rows], PageMeta(
            page=page, page_size=page_size, total=total,
            total_pages=ceil(total / page_size) if total else 0,
        )

    async def get_skill(self, skill_id: int) -> SkillSummary:
        row = await self.skills.get_skill(skill_id)
        if not row:
            raise ResourceNotFoundError("技能不存在")
        return self._skill_summary(row)

    async def extract_job(self, job_id: int, *, user_id: int) -> JobExtractionResult:
        job = await self.jobs.get(job_id)
        if not job:
            raise ResourceNotFoundError("岗位不存在")
        result = await self.extract_text(
            jd_text=job.jd_text,
            responsibilities="\n".join(job.responsibilities or []),
            requirements="\n".join(job.requirements or []),
            user_id=user_id,
        )
        try:
            facts = await self._persist_facts(
                result.skills, job_id=job.id, raw_job_record_id=None,
                agent_run_id=result.agent_run_id,
            )
            required = [fact.skill.name for fact in facts if fact.kind == "required"]
            preferred = [fact.skill.name for fact in facts if fact.kind == "preferred"]
            await self.jobs.replace_skills(job, required=required, bonus=preferred)
            job.updated_at = utc_now_naive()
            version_no = await self.jobs.next_version_no(job.id)
            await self.jobs.add_version(
                job_id=job.id,
                version_no=version_no,
                snapshot=JobService._snapshot(job),
                change_reason="技能抽取更新",
                created_by=user_id,
            )
            await self.db.commit()
            return JobExtractionResult(
                job_id=job.id,
                facts=[self._fact_response(fact) for fact in facts],
                llm_enrichment=result.llm_enrichment,
                agent_run_id=result.agent_run_id,
            )
        except Exception:
            await self.db.rollback()
            raise

    async def list_job_facts(self, job_id: int) -> list[SkillFactResponse]:
        if not await self.jobs.get(job_id):
            raise ResourceNotFoundError("岗位不存在")
        return [
            self._fact_response(fact)
            for fact in await self.skills.list_job_facts(job_id)
        ]

    async def list_fact_reviews(
        self,
        *,
        page: int,
        page_size: int,
        status: VerificationStatus | None,
        keyword: str | None,
    ):
        rows, total, counts = await self.skills.list_fact_reviews(
            page=page,
            page_size=page_size,
            status=status.value if status else None,
            keyword=keyword,
        )
        summary = SkillFactReviewSummary(
            all=sum(counts.values()),
            unverified=counts.get("unverified", 0),
            verified=counts.get("verified", 0),
            rejected=counts.get("rejected", 0),
        )
        return SkillFactReviewList(
            items=[self._review_item(row) for row in rows],
            summary=summary,
        ), PageMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total else 0,
        )

    async def review_fact(
        self,
        fact_id: int,
        *,
        decision: VerificationStatus,
        note: str | None,
        reviewer_id: int,
    ) -> SkillFactReviewItem:
        fact = await self.skills.get_fact_for_update(fact_id)
        if not fact:
            raise ResourceNotFoundError("技能事实不存在")
        if fact.verification_status != VerificationStatus.unverified.value:
            raise InvalidParameterError("仅待审核事实可以确认或驳回")
        fact.verification_status = decision.value
        fact.reviewed_by = reviewer_id
        fact.reviewed_at = utc_now()
        fact.review_note = note
        await self.db.commit()
        row = await self.skills.get_fact_review(fact_id)
        if not row:
            raise ResourceNotFoundError("技能事实不存在")
        return self._review_item(row)

    async def review_facts(
        self,
        *,
        fact_ids: list[int] | None,
        keyword: str | None,
        decision: VerificationStatus,
        note: str | None,
        reviewer_id: int,
    ) -> tuple[list[int], int]:
        unique_ids = list(dict.fromkeys(fact_ids or []))
        facts = await self.skills.get_facts_for_review(
            fact_ids=unique_ids if fact_ids is not None else None,
            keyword=keyword,
        )
        reviewed_at = utc_now()
        for fact in facts:
            fact.verification_status = decision.value
            fact.reviewed_by = reviewer_id
            fact.reviewed_at = reviewed_at
            fact.review_note = note
        await self.db.commit()
        processed_ids = [fact.id for fact in facts]
        skipped_count = max(0, len(unique_ids) - len(processed_ids)) if fact_ids is not None else 0
        return processed_ids, skipped_count

    async def extract_text(
        self,
        *,
        jd_text: str,
        responsibilities: str = "",
        requirements: str = "",
        user_id: int | None = None,
    ) -> SkillExtractionOutput:
        result = self.extractor.extract(
            jd_text=jd_text,
            responsibilities=responsibilities,
            requirements=requirements,
        )
        provider_enabled = bool(getattr(self.llm, "enabled", True))
        if not provider_enabled:
            return result
        run_id = str(uuid.uuid4())
        started = time.perf_counter()
        run = AgentRun(
            id=run_id,
            agent_type="skill_extraction",
            provider=self.llm.provider_name,
            model=self.llm.model_name,
            prompt_version=self.enrichment_agent.prompt_version,
            input_summary=normalize_text(jd_text)[:500],
            status="running",
            started_at=utc_now(),
            retry_count=0,
            created_by=user_id,
        )
        await self.skills.add_agent_run(run)
        try:
            enriched = await self.enrichment_agent.enrich(
                text=jd_text + " " + responsibilities + " " + requirements,
                known_skills=[item.name for item in result.skills],
            )
            known_keys = {canonical_key(item.name) for item in result.skills}
            additions = [
                ExtractedSkill(
                    **item.model_dump(), extraction_method="llm"
                )
                for item in enriched.skills
                if canonical_key(item.name) not in known_keys
            ]
            result.skills.extend(additions)
            result.llm_enrichment = bool(additions)
            result.agent_run_id = run_id
            run.status = "succeeded"
            run.structured_output = enriched.model_dump(mode="json")
        except Exception as exc:
            run.status = AgentRunStatus.failed.value
            run.error_code = type(exc).__name__
            run.error_message = str(exc)[:2000]
        finally:
            run.duration_ms = int((time.perf_counter() - started) * 1000)
            run.finished_at = utc_now()
        return result

    async def persist_raw_facts(
        self, *, raw_job_record_id: int, output: SkillExtractionOutput
    ) -> int:
        facts = await self._persist_facts(
            output.skills, job_id=None, raw_job_record_id=raw_job_record_id,
            agent_run_id=output.agent_run_id,
        )
        return len(facts)

    async def _persist_facts(
        self,
        extracted: list[ExtractedSkill],
        *,
        job_id: int | None,
        raw_job_record_id: int | None,
        agent_run_id: str | None,
    ) -> list[JobSkillFact]:
        await self.skills.replace_facts(
            job_id=job_id, raw_job_record_id=raw_job_record_id
        )
        facts: list[JobSkillFact] = []
        for item in extracted:
            skill = await self.skills.get_or_create_skill(
                name=item.name,
                canonical_key=canonical_key(item.name),
                category=item.category,
                aliases=[],
                validation_status=(
                    "pending_review"
                    if item.extraction_method == "llm"
                    else "approved"
                ),
            )
            confidence = item.confidence
            fact = JobSkillFact(
                job_id=job_id,
                raw_job_record_id=raw_job_record_id,
                skill_id=skill.id,
                kind=item.kind.value,
                importance=0.9 if item.kind.value == "required" else 0.6,
                frequency=1,
                confidence=confidence,
                evidence_text=item.evidence,
                verification_status="unverified",
                extraction_method=item.extraction_method,
                source_count=1,
                agent_run_id=agent_run_id,
                skill=skill,
            )
            await self.skills.add_fact(fact)
            facts.append(fact)
        return facts

    @staticmethod
    def _skill_summary(row) -> SkillSummary:
        return SkillSummary(
            id=row.id, name=row.name, canonical_name=row.canonical_name,
            canonical_key=row.canonical_key, category=row.category,
            aliases=row.aliases or [], first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
        )

    @staticmethod
    def _fact_response(fact: JobSkillFact) -> SkillFactResponse:
        return SkillFactResponse(
            id=fact.id, skill_id=fact.skill_id, skill_name=fact.skill.name,
            category=fact.skill.category, kind=fact.kind,
            importance=fact.importance, frequency=fact.frequency,
            confidence=fact.confidence, evidence_text=fact.evidence_text,
            verification_status=fact.verification_status,
            extraction_method=fact.extraction_method, source_count=fact.source_count,
        )

    @staticmethod
    def _review_item(row) -> SkillFactReviewItem:
        fact, skill, raw_job, source_document, job, reviewer_name = row
        return SkillFactReviewItem(
            id=fact.id,
            skill_id=fact.skill_id,
            skill_name=skill.name,
            category=skill.category,
            kind=fact.kind,
            importance=fact.importance,
            frequency=fact.frequency,
            confidence=fact.confidence,
            evidence_text=fact.evidence_text,
            verification_status=fact.verification_status,
            extraction_method=fact.extraction_method,
            source_count=fact.source_count,
            job_id=fact.job_id,
            raw_job_record_id=fact.raw_job_record_id,
            job_title=raw_job.title if raw_job else (job.title if job else "未知岗位"),
            company=raw_job.company if raw_job else (job.company if job else None),
            source=source_document.source if source_document else "内部岗位",
            source_url=source_document.url if source_document else None,
            reviewed_by=fact.reviewed_by,
            reviewer_name=reviewer_name,
            reviewed_at=fact.reviewed_at,
            review_note=fact.review_note,
            created_at=fact.created_at,
        )
