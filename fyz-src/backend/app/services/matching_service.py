from __future__ import annotations

import time
import uuid
from hashlib import sha256

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.agent_runtime import (
    MatchEvidenceInput,
    MatchExplanationAgent,
    MatchExplanationOutput,
    MatchExplanationRequest,
)
from app.core.config import DEEPSEEK_TIMEOUT_SECONDS
from app.core.exceptions import InvalidParameterError, ResourceNotFoundError
from app.core.time import utc_now
from app.domain.agent_status import AgentRunStatus
from app.domain.skill_dictionary import canonical_key, normalize_skill
from app.models import AgentRun, JobPosting, MatchEvidence, MatchRecord, Resume, ResumeParseResult, ResumeSkill
from app.providers import DeepSeekProvider, LLMProvider
from app.schemas.matching import MatchEvidenceResponse, MatchExplanationResponse, MatchResponse, ResumeCreatedResponse, ResumeSkillDetailResponse, TalentDetailResponse, TalentResponse, TalentUpdateRequest
from app.services.agent_grounding_service import (
    AgentGroundingReport,
    AgentGroundingService,
    GroundedClaim,
)
from app.services.resume_parser import ResumeParser
from app.services.resume_profile_extractor import ResumeProfileExtractor
from app.services.resume_storage import ResumeStorage
from app.services.skill_extractor import RuleSkillExtractor
from app.services.task_status_cache import bump_cache_generations


def calculate_skill_coverage(
    resume_skill_names: list[str] | set[str] | tuple[str, ...],
    job_skill_names: list[str] | set[str] | tuple[str, ...],
) -> tuple[int, list[str], list[str]]:
    """Return the deterministic score used by FYZ resume/job matching.

    Keeping the calculation separate from persistence makes the production
    algorithm directly measurable without duplicating its rules in the
    quality evaluation suite.
    """
    def normalized_key(name: str) -> str:
        normalized = normalize_skill(name)
        return canonical_key(normalized[0] if normalized else name)

    unique_job_skills = list(dict.fromkeys(job_skill_names))
    if not unique_job_skills:
        return 0, [], []
    resume_keys = {normalized_key(name) for name in resume_skill_names}
    matched = [
        name for name in unique_job_skills if normalized_key(name) in resume_keys
    ]
    missing = [
        name for name in unique_job_skills if normalized_key(name) not in resume_keys
    ]
    return round(len(matched) / len(unique_job_skills) * 100), matched, missing


_MISSING_CANDIDATE_NAMES = {"", "姓名待补充", "候选人"}


def candidate_display_name(resume_id: int, name: str | None) -> str:
    """Return a stable anonymous nickname when a resume has no parsed name."""
    normalized_name = (name or "").strip()
    if normalized_name in _MISSING_CANDIDATE_NAMES:
        return f"候选人{resume_id}"
    return normalized_name


class MatchingService:
    algorithm_version = "skill-coverage-v1"

    def __init__(
        self,
        db: AsyncSession,
        *,
        llm_provider: LLMProvider | None = None,
        grounding_service: AgentGroundingService | None = None,
    ) -> None:
        self.db = db
        self.llm = llm_provider or DeepSeekProvider()
        self.parser = ResumeParser()
        self.profile_extractor = ResumeProfileExtractor()
        self.storage = ResumeStorage()
        self.extractor = RuleSkillExtractor()
        self.grounding = grounding_service or AgentGroundingService(db)

    async def create_resume(self, *, content: bytes, filename: str, content_type: str | None, user_id: int, name: str | None = None, current_position: str | None = None, experience: str | None = None, education: str | None = None, department: str | None = None, company: str | None = None, location: str | None = None, preparsed_text: str | None = None, parse_warnings: list[str] | None = None) -> ResumeCreatedResponse:
        if preparsed_text is None:
            parsed_text, warnings = self.parser.parse(content, filename)
        else:
            parsed_text = preparsed_text
            warnings = list(parse_warnings or [])
        profile = self.profile_extractor.extract(parsed_text)
        digest = sha256(content).hexdigest()
        duplicate = await self.db.scalar(select(Resume.id).where(Resume.created_by == user_id, Resume.content_hash == digest, Resume.deleted_at.is_(None)))
        if duplicate:
            raise InvalidParameterError(f"该简历已上传，resume_id={duplicate}")
        storage_key, _ = self.storage.save(content, filename)
        skills = self.extractor.extract(jd_text=parsed_text).skills
        parsed_name = (name or profile["name"] or "").strip()
        resume = Resume(
            # The generated nickname needs the database id, so use a temporary
            # non-empty value until the first flush assigns that id.
            name=parsed_name[:100] or "候选人",
            current_position=current_position or profile["current_position"],
            experience=experience or profile["experience"],
            education=education or profile["education"], department=department,
            company=company, location=location,
            original_filename=filename[:255], storage_key=storage_key, content_type=content_type,
            file_size=len(content), content_hash=digest, created_by=user_id,
        )
        resume.parse_result = ResumeParseResult(parsed_text=parsed_text, profile=profile, warnings=warnings, parser_version=self.parser.version)
        resume.skills = [ResumeSkill(name=s.name, canonical_key=canonical_key(s.name), category=s.category, confidence=s.confidence, evidence_text=s.evidence, extraction_method="rule") for s in skills]
        self.db.add(resume)
        try:
            await self.db.flush()
            resume.name = candidate_display_name(resume.id, resume.name)
            if not parsed_name and resume.parse_result:
                resume.parse_result.profile = {
                    **(resume.parse_result.profile or {}),
                    "name": resume.name,
                }
            matches = await self._calculate_matches(resume, user_id=user_id)
            await self.db.commit()
            await bump_cache_generations("dashboard")
        except Exception:
            await self.db.rollback()
            self.storage.remove(storage_key)
            raise
        return ResumeCreatedResponse(id=resume.id, name=candidate_display_name(resume.id, resume.name), filename=resume.original_filename, skills=[s.name for s in resume.skills], warnings=warnings, matches=[self._match_response(m) for m in matches])

    async def _calculate_matches(self, resume: Resume, *, user_id: int, job_ids: list[int] | None = None) -> list[MatchRecord]:
        query = select(JobPosting).where(JobPosting.deleted_at.is_(None), JobPosting.status == "open").order_by(JobPosting.id)
        if job_ids:
            query = query.where(JobPosting.id.in_(job_ids))
        jobs = list((await self.db.execute(query)).scalars())
        resume_keys = {skill.canonical_key: skill for skill in resume.skills}
        records: list[MatchRecord] = []
        for job in jobs:
            job_skills = list(dict.fromkeys(skill.name for skill in job.skills))
            if not job_skills:
                extracted = self.extractor.extract(jd_text=job.jd_text, responsibilities=" ".join(job.responsibilities), requirements=" ".join(job.requirements))
                job_skills = [skill.name for skill in extracted.skills]
            if not job_skills:
                continue
            score, matched, missing = calculate_skill_coverage(
                list(resume_keys), job_skills
            )
            record = await self.db.scalar(select(MatchRecord).where(MatchRecord.resume_id == resume.id, MatchRecord.job_id == job.id, MatchRecord.algorithm_version == self.algorithm_version))
            if record is None:
                record = MatchRecord(resume_id=resume.id, job_id=job.id, algorithm_version=self.algorithm_version, score=0, matched_skills=[], missing_skills=[], created_by=user_id)
                self.db.add(record)
                await self.db.flush()
            else:
                await self.db.execute(delete(MatchEvidence).where(MatchEvidence.match_id == record.id))
            record.score = score
            record.matched_skills, record.missing_skills = matched, missing
            evidence: list[MatchEvidence] = []
            parsed_text = resume.parse_result.parsed_text if resume.parse_result else ""
            for name in matched:
                skill = resume_keys[canonical_key(name)]
                excerpt = (skill.evidence_text or "").strip()
                locator = self._text_locator(parsed_text, excerpt or name)
                evidence.append(MatchEvidence(
                    match_id=record.id,
                    evidence_type="resume_skill",
                    skill_name=name,
                    evidence_text=(
                        f"匹配技能：{name}；简历原文：{excerpt}"
                        if excerpt
                        else f"简历中识别到匹配技能：{name}"
                    ),
                    source_ref={
                        "resume_skill_id": skill.id,
                        "resume_id": resume.id,
                        "filename": resume.original_filename,
                        "source_kind": "resume",
                        "canonical_key": skill.canonical_key,
                        **locator,
                    },
                ))
            # Keep JD evidence for every required skill. A matched skill then has both
            # resume and job anchors, which allows a richer but still auditable explanation.
            for name in job_skills:
                requirement = next((item for item in job.requirements if name.casefold() in item.casefold()), "")
                jd_excerpt = requirement or f"岗位 {job.title} 要求 {name}"
                evidence.append(MatchEvidence(match_id=record.id, evidence_type="job_requirement", skill_name=name, evidence_text=jd_excerpt, source_ref={"job_id": job.id, "job_title": job.title, "department": job.department, "level": job.level, "source_kind": "job", "section": "岗位要求", **self._text_locator(job.jd_text or "\n".join(job.requirements), requirement or name)}))
            self.db.add_all(evidence)
            record.job = job
            records.append(record)
        await self.db.flush()
        for record in records:
            await self.db.refresh(record, attribute_names=["evidence"])
        return sorted(records, key=lambda item: (-item.score, item.job_id))

    async def recalculate_matches(self, user_id: int) -> dict:
        resumes = list(
            (
                await self.db.execute(
                    select(Resume)
                    .where(
                        Resume.created_by == user_id,
                        Resume.deleted_at.is_(None),
                        Resume.status == "active",
                    )
                    .order_by(Resume.id)
                )
            ).scalars()
        )
        match_count = 0
        for resume in resumes:
            match_count += len(
                await self._calculate_matches(resume, user_id=user_id)
            )
        await self.db.commit()
        await bump_cache_generations("dashboard")
        return {
            "resumes_processed": len(resumes),
            "matches_upserted": match_count,
        }

    async def list_talents(self, user_id: int) -> list[TalentResponse]:
        resumes = list((await self.db.execute(select(Resume).where(Resume.created_by == user_id, Resume.deleted_at.is_(None)).order_by(Resume.created_at.desc()))).scalars())
        return [self._talent(resume) for resume in resumes if resume.matches]

    async def get_talent(self, resume_id: int, user_id: int) -> TalentResponse:
        resume = await self._resume(resume_id, user_id)
        if not resume.matches:
            raise ResourceNotFoundError("该简历尚无岗位匹配记录")
        return self._talent(resume)

    async def get_talent_detail(self, resume_id: int, user_id: int) -> TalentDetailResponse:
        resume = await self._resume(resume_id, user_id)
        if not resume.matches:
            raise ResourceNotFoundError("该简历尚无岗位匹配记录")
        parsed = resume.parse_result
        return TalentDetailResponse(
            **self._talent(resume).model_dump(),
            file_size=resume.file_size,
            content_type=resume.content_type,
            parsed_text=parsed.parsed_text if parsed else "",
            profile=parsed.profile if parsed else {},
            parse_warnings=parsed.warnings if parsed else [],
            skills=[
                ResumeSkillDetailResponse(
                    name=skill.name,
                    category=skill.category,
                    confidence=skill.confidence,
                    evidence_text=skill.evidence_text,
                    extraction_method=skill.extraction_method,
                )
                for skill in resume.skills
            ],
        )

    async def update_talent_detail(self, resume_id: int, user_id: int, payload: TalentUpdateRequest) -> TalentDetailResponse:
        resume = await self._resume(resume_id, user_id)
        resume.name = payload.name
        resume.current_position = payload.current_position or None
        resume.experience = payload.experience or None
        resume.education = payload.education or None
        resume.department = payload.department or None
        resume.company = payload.company or None
        resume.location = payload.location or None
        if resume.parse_result:
            profile = dict(resume.parse_result.profile or {})
            profile.update({
                "name": payload.name,
                "phone": payload.phone or None,
                "email": payload.email or None,
                "current_position": payload.current_position or None,
                "experience": payload.experience or None,
                "education": payload.education or None,
            })
            resume.parse_result.profile = profile
        await self.db.commit()
        await bump_cache_generations("dashboard")
        return await self.get_talent_detail(resume_id, user_id)

    async def match_resume_jobs(self, resume_id: int, job_ids: list[int], user_id: int) -> list[MatchResponse]:
        resume = await self._resume(resume_id, user_id)
        records = await self._calculate_matches(resume, user_id=user_id, job_ids=job_ids)
        await self.db.commit()
        await bump_cache_generations("dashboard")
        return [self._match_response(record) for record in records]

    async def get_resume_file(self, resume_id: int, user_id: int) -> tuple[str, str | None, object]:
        resume = await self._resume(resume_id, user_id)
        return resume.original_filename, resume.content_type, self.storage.path_for(resume.storage_key)

    async def explain(
        self,
        match_id: int,
        user_id: int,
        *,
        agent_run_id: str | None = None,
    ) -> MatchExplanationResponse:
        match = await self.db.scalar(
            select(MatchRecord)
            .options(
                selectinload(MatchRecord.resume),
                selectinload(MatchRecord.job),
                selectinload(MatchRecord.evidence),
            )
            .join(Resume)
            .where(MatchRecord.id == match_id, Resume.created_by == user_id, Resume.deleted_at.is_(None))
        )
        if match is None:
            raise ResourceNotFoundError("匹配记录不存在")
        saved_evidence = list(match.evidence)
        request = MatchExplanationRequest(
            match_id=match.id,
            resume_id=match.resume_id,
            job_id=match.job_id,
            job_title=match.job.title,
            score=match.score,
            matched_skills=match.matched_skills,
            missing_skills=match.missing_skills,
            candidate_context={
                "current_position": match.resume.current_position or "待确认",
                "experience": match.resume.experience or "待确认",
                "education": match.resume.education or "待确认",
                "department": match.resume.department or "待确认",
                "company": match.resume.company or "",
                "location": match.resume.location or "",
            },
            job_context={
                "department": match.job.department,
                "level": match.job.level,
                "responsibilities": match.job.responsibilities,
                "requirements": match.job.requirements,
                "bonus_skills": [],
            },
            evidence=[
                MatchEvidenceInput(
                    evidence_id=f"match_evidence:{item.id}",
                    evidence_type=item.evidence_type,
                    skill_name=item.skill_name,
                    evidence_text=item.evidence_text,
                    source_ref=item.source_ref,
                )
                for item in saved_evidence
            ],
        )
        agent = MatchExplanationAgent(self.llm, timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS)
        run = await self.db.get(AgentRun, agent_run_id) if agent_run_id else None
        if run is None:
            run = AgentRun(
                id=agent_run_id or str(uuid.uuid4()),
                agent_type=agent.agent_type,
                provider=self.llm.provider_name,
                model=self.llm.model_name,
                prompt_version=agent.prompt_version,
                input_summary=(
                    f"match_id={match.id} "
                    f"evidence={len(saved_evidence)}"
                ),
                status=AgentRunStatus.running.value,
                retry_count=0,
                created_by=user_id,
                started_at=utc_now(),
            )
            self.db.add(run)
        else:
            run.status = AgentRunStatus.running.value
            run.started_at = run.started_at or utc_now()
            run.error_code = None
            run.error_message = None
        await self.db.flush()
        started = time.perf_counter()
        raw_output: MatchExplanationOutput | None = None
        report = AgentGroundingReport()
        model_validation: AgentGroundingReport | None = None
        fallback_reason: str | None = None
        try:
            raw_output = await agent.generate(request)
            report = await self.grounding.validate_match_and_persist(
                agent_run_id=run.id,
                claims=self._match_grounding_claims(raw_output),
                evidence=saved_evidence,
            )
            if raw_output.generation_mode == "llm":
                model_validation = report
            output = self._validated_match_output(
                raw_output,
                report,
            )
            if (
                report.accepted_count == 0
                and raw_output.generation_mode == "llm"
            ):
                fallback_reason = "insufficient_grounding"
                template = agent.template_output(request)
                report = (
                    await self.grounding.validate_match_and_persist(
                        agent_run_id=run.id,
                        claims=self._match_grounding_claims(template),
                        evidence=saved_evidence,
                    )
                )
                output = self._validated_match_output(
                    template.model_copy(
                        update={
                            "warnings": [
                                *template.warnings,
                                "模型结果未通过引用校验，已使用确定性模板。",
                            ]
                        }
                    ),
                    report,
                )
            run.status = (
                AgentRunStatus.degraded.value
                if output.generation_mode == "template"
                or report.rejected_count > 0
                or fallback_reason is not None
                else AgentRunStatus.succeeded.value
            )
        except Exception as exc:
            fallback_reason = "llm_failed"
            template = agent.template_output(request).model_copy(
                update={
                    "warnings": [
                        "AI 增强暂未完成，已返回基于已保存证据的确定性匹配解释。"
                    ]
                }
            )
            report = await self.grounding.validate_match_and_persist(
                agent_run_id=run.id,
                claims=self._match_grounding_claims(template),
                evidence=saved_evidence,
            )
            output = self._validated_match_output(template, report)
            run.status, run.error_code, run.error_message = (
                AgentRunStatus.degraded.value,
                type(exc).__name__,
                str(exc)[:2000],
            )
        run.structured_output = {
            "raw_output": (
                raw_output.model_dump(mode="json")
                if raw_output is not None
                else None
            ),
            "validated_output": output.model_dump(mode="json"),
            "evidence": {
                "source_type": "match_evidence",
                "evidence_ids": [
                    f"match_evidence:{item.id}"
                    for item in saved_evidence
                ],
                "match_id": match.id,
                "algorithm_version": match.algorithm_version,
            },
            "validation": report.to_dict(),
            "model_validation": (
                model_validation.to_dict()
                if model_validation is not None
                else None
            ),
            "fallback_reason": fallback_reason,
        }
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        run.finished_at = utc_now()
        match.explanation_agent_run_id = run.id
        await self.db.commit()
        return MatchExplanationResponse(
            **output.model_dump(),
            agent_run_id=run.id,
            evidence=[self._evidence_response(item) for item in saved_evidence],
        )

    @staticmethod
    def _match_grounding_claims(
        output: MatchExplanationOutput,
    ) -> list[GroundedClaim]:
        claims: list[GroundedClaim] = []
        for claim_type, items in (
            ("strength", output.strengths),
            ("gap", output.gaps),
            ("risk", output.risks),
        ):
            for index, item in enumerate(items):
                claims.append(
                    GroundedClaim(
                        claim_id=f"{claim_type}:{index}",
                        claim_type=claim_type,
                        claim_text=(
                            f"{item.title}\n{item.explanation}"
                        ),
                        anchor_text=item.title,
                        evidence_ids=tuple(item.evidence_ids),
                    )
                )
        return claims

    @staticmethod
    def _validated_match_output(
        output: MatchExplanationOutput,
        report: AgentGroundingReport,
    ) -> MatchExplanationOutput:
        accepted = report.accepted_claim_ids
        strengths = [
            item
            for index, item in enumerate(output.strengths)
            if f"strength:{index}" in accepted
        ]
        gaps = [
            item
            for index, item in enumerate(output.gaps)
            if f"gap:{index}" in accepted
        ]
        risks = [
            item
            for index, item in enumerate(output.risks)
            if f"risk:{index}" in accepted
        ]
        if strengths or gaps or risks:
            summary = (
                f"已基于保存证据验证 {len(strengths)} 项匹配优势、"
                f"{len(gaps)} 项能力缺口和 {len(risks)} 项风险；"
                f"匹配快照分数为 {output.score} 分。"
            )
        else:
            summary = "当前没有足够的已保存证据生成匹配解释。"
        warnings = list(output.warnings)
        if report.rejected_count:
            warnings.append(
                f"{report.rejected_count} 条陈述未通过引用校验，已过滤。"
            )
        if not strengths and not gaps and not risks:
            warnings.append("证据不足，未生成无依据陈述。")
        suggestions = [
            f"围绕 {item.title} 准备可验证的项目案例。"
            for item in strengths[:3]
        ]
        return output.model_copy(
            update={
                "summary": summary,
                "strengths": strengths,
                "gaps": gaps,
                "risks": risks,
                "interview_suggestions": suggestions,
                "warnings": list(dict.fromkeys(warnings)),
            }
        )

    async def _resume(self, resume_id: int, user_id: int) -> Resume:
        resume = await self.db.scalar(select(Resume).where(Resume.id == resume_id, Resume.created_by == user_id, Resume.deleted_at.is_(None)))
        if resume is None:
            raise ResourceNotFoundError("简历不存在")
        return resume

    def _talent(self, resume: Resume) -> TalentResponse:
        matches = sorted(resume.matches, key=lambda item: (-item.score, item.job_id))
        best = matches[0]
        profile = resume.parse_result.profile if resume.parse_result else {}
        return TalentResponse(id=resume.id, resume_id=resume.id, match_id=best.id, name=candidate_display_name(resume.id, resume.name), position=resume.current_position or "岗位待补充", score=best.score, isNew=True, experience=resume.experience or "经历待补充", education=resume.education or "学历待补充", department=resume.department or "部门待补充", matched=best.matched_skills, missing=best.missing_skills, targetJobs=[m.job.title for m in matches], targetJobIds=[m.job_id for m in matches], resumeFile=resume.original_filename, uploadDate=resume.created_at.date().isoformat(), urgent=best.job.urgent, company=resume.company or "", location=resume.location or "", phone=str(profile.get("phone") or ""), email=str(profile.get("email") or ""), matches=[self._match_response(match) for match in matches])

    @staticmethod
    def _match_response(match: MatchRecord) -> MatchResponse:
        return MatchResponse(id=match.id, resume_id=match.resume_id, job_id=match.job_id, job_title=match.job.title, job_department=match.job.department, job_level=match.job.level, score=match.score, matched=match.matched_skills, missing=match.missing_skills, algorithm_version=match.algorithm_version, urgent=match.job.urgent, evidence=[MatchingService._evidence_response(e) for e in match.evidence])

    @staticmethod
    def _evidence_response(evidence: MatchEvidence) -> MatchEvidenceResponse:
        return MatchEvidenceResponse(id=evidence.id, evidence_type=evidence.evidence_type, skill_name=evidence.skill_name, evidence_text=evidence.evidence_text, source_ref=evidence.source_ref)

    @staticmethod
    def _text_locator(text: str, needle: str) -> dict:
        if not text or not needle:
            return {}
        index = text.casefold().find(needle.casefold())
        if index < 0:
            return {"excerpt": needle[:240]}
        line_start = text.count("\n", 0, index) + 1
        line_end = line_start + needle.count("\n")
        return {
            "line_start": line_start,
            "line_end": line_end,
            "char_start": index,
            "char_end": index + len(needle),
            "excerpt": needle[:240],
        }
