from __future__ import annotations

import time
import uuid
from datetime import datetime
from hashlib import sha256

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_runtime import MatchEvidenceInput, MatchExplanationAgent, MatchExplanationRequest
from app.core.config import DEEPSEEK_TIMEOUT_SECONDS
from app.core.exceptions import InvalidParameterError, ResourceNotFoundError
from app.domain.skill_dictionary import canonical_key
from app.models import AgentRun, JobPosting, MatchEvidence, MatchRecord, Resume, ResumeParseResult, ResumeSkill
from app.providers import DeepSeekProvider, LLMProvider
from app.schemas.matching import MatchEvidenceResponse, MatchExplanationResponse, MatchResponse, ResumeCreatedResponse, TalentResponse
from app.services.resume_parser import ResumeParser
from app.services.resume_storage import ResumeStorage
from app.services.skill_extractor import RuleSkillExtractor


class MatchingService:
    algorithm_version = "skill-coverage-v1"

    def __init__(self, db: AsyncSession, *, llm_provider: LLMProvider | None = None) -> None:
        self.db = db
        self.llm = llm_provider or DeepSeekProvider()
        self.parser = ResumeParser()
        self.storage = ResumeStorage()
        self.extractor = RuleSkillExtractor()

    async def create_resume(self, *, content: bytes, filename: str, content_type: str | None, user_id: int, name: str | None = None, current_position: str | None = None, experience: str | None = None, education: str | None = None, department: str | None = None, company: str | None = None, location: str | None = None) -> ResumeCreatedResponse:
        parsed_text, warnings = self.parser.parse(content, filename)
        digest = sha256(content).hexdigest()
        duplicate = await self.db.scalar(select(Resume.id).where(Resume.created_by == user_id, Resume.content_hash == digest, Resume.deleted_at.is_(None)))
        if duplicate:
            raise InvalidParameterError(f"该简历已上传，resume_id={duplicate}")
        storage_key, _ = self.storage.save(content, filename)
        skills = self.extractor.extract(jd_text=parsed_text).skills
        resume = Resume(
            name=(name or filename.rsplit(".", 1)[0])[:100], current_position=current_position,
            experience=experience, education=education, department=department, company=company, location=location,
            original_filename=filename[:255], storage_key=storage_key, content_type=content_type,
            file_size=len(content), content_hash=digest, created_by=user_id,
        )
        resume.parse_result = ResumeParseResult(parsed_text=parsed_text, profile={}, warnings=warnings, parser_version=self.parser.version)
        resume.skills = [ResumeSkill(name=s.name, canonical_key=canonical_key(s.name), category=s.category, confidence=s.confidence, evidence_text=s.evidence, extraction_method="rule") for s in skills]
        self.db.add(resume)
        try:
            await self.db.flush()
            matches = await self._calculate_matches(resume, user_id=user_id)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            self.storage.remove(storage_key)
            raise
        return ResumeCreatedResponse(id=resume.id, name=resume.name, filename=resume.original_filename, skills=[s.name for s in resume.skills], warnings=warnings, matches=[self._match_response(m) for m in matches])

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
            matched = [name for name in job_skills if canonical_key(name) in resume_keys]
            missing = [name for name in job_skills if canonical_key(name) not in resume_keys]
            record = await self.db.scalar(select(MatchRecord).where(MatchRecord.resume_id == resume.id, MatchRecord.job_id == job.id, MatchRecord.algorithm_version == self.algorithm_version))
            if record is None:
                record = MatchRecord(resume_id=resume.id, job_id=job.id, algorithm_version=self.algorithm_version, score=0, matched_skills=[], missing_skills=[], created_by=user_id)
                self.db.add(record)
                await self.db.flush()
            else:
                await self.db.execute(delete(MatchEvidence).where(MatchEvidence.match_id == record.id))
            record.score = round(len(matched) / len(job_skills) * 100)
            record.matched_skills, record.missing_skills = matched, missing
            evidence: list[MatchEvidence] = []
            for name in matched:
                skill = resume_keys[canonical_key(name)]
                evidence.append(MatchEvidence(match_id=record.id, evidence_type="resume_skill", skill_name=name, evidence_text=skill.evidence_text or f"简历中识别到 {name}", source_ref={"resume_skill_id": skill.id}))
            for name in missing:
                evidence.append(MatchEvidence(match_id=record.id, evidence_type="job_requirement", skill_name=name, evidence_text=f"岗位 {job.title} 要求 {name}", source_ref={"job_id": job.id}))
            self.db.add_all(evidence)
            record.job = job
            records.append(record)
        await self.db.flush()
        for record in records:
            await self.db.refresh(record, attribute_names=["evidence"])
        return sorted(records, key=lambda item: (-item.score, item.job_id))

    async def list_talents(self, user_id: int) -> list[TalentResponse]:
        resumes = list((await self.db.execute(select(Resume).where(Resume.created_by == user_id, Resume.deleted_at.is_(None)).order_by(Resume.created_at.desc()))).scalars())
        return [self._talent(resume) for resume in resumes if resume.matches]

    async def get_talent(self, resume_id: int, user_id: int) -> TalentResponse:
        resume = await self._resume(resume_id, user_id)
        if not resume.matches:
            raise ResourceNotFoundError("该简历尚无岗位匹配记录")
        return self._talent(resume)

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
        match = await self.db.scalar(select(MatchRecord).join(Resume).where(MatchRecord.id == match_id, Resume.created_by == user_id, Resume.deleted_at.is_(None)))
        if match is None:
            raise ResourceNotFoundError("匹配记录不存在")
        request = MatchExplanationRequest(match_id=match.id, resume_id=match.resume_id, job_id=match.job_id, job_title=match.job.title, score=match.score, matched_skills=match.matched_skills, missing_skills=match.missing_skills, evidence=[MatchEvidenceInput(evidence_id=e.id, evidence_type=e.evidence_type, skill_name=e.skill_name, evidence_text=e.evidence_text, source_ref=e.source_ref) for e in match.evidence])
        agent = MatchExplanationAgent(self.llm, timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS)
        run = await self.db.get(AgentRun, agent_run_id) if agent_run_id else None
        if run is None:
            run = AgentRun(id=agent_run_id or str(uuid.uuid4()), agent_type=agent.agent_type, provider=self.llm.provider_name, model=self.llm.model_name, prompt_version=agent.prompt_version, input_summary=f"match_id={match.id} evidence={len(match.evidence)}", status="running", retry_count=0, created_by=user_id)
            self.db.add(run)
        else:
            run.status = "running"
        await self.db.flush()
        started = time.perf_counter()
        try:
            output = await agent.generate(request)
            run.status = "degraded" if output.generation_mode == "template" else "succeeded"
        except Exception as exc:
            output = agent.template_output(request)
            run.status, run.error_code, run.error_message = "degraded", type(exc).__name__, str(exc)[:2000]
        run.structured_output = output.model_dump(mode="json")
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        run.finished_at = datetime.utcnow()
        match.explanation_agent_run_id = run.id
        await self.db.commit()
        return MatchExplanationResponse(**output.model_dump(), agent_run_id=run.id)

    async def _resume(self, resume_id: int, user_id: int) -> Resume:
        resume = await self.db.scalar(select(Resume).where(Resume.id == resume_id, Resume.created_by == user_id, Resume.deleted_at.is_(None)))
        if resume is None:
            raise ResourceNotFoundError("简历不存在")
        return resume

    def _talent(self, resume: Resume) -> TalentResponse:
        matches = sorted(resume.matches, key=lambda item: (-item.score, item.job_id))
        best = matches[0]
        return TalentResponse(id=resume.id, resume_id=resume.id, match_id=best.id, name=resume.name, position=resume.current_position or "待确认", score=best.score, isNew=True, experience=resume.experience or "待确认", education=resume.education or "待确认", department=resume.department or "待确认", matched=best.matched_skills, missing=best.missing_skills, targetJobs=[m.job.title for m in matches], targetJobIds=[m.job_id for m in matches], resumeFile=resume.original_filename, uploadDate=resume.created_at.date().isoformat(), urgent=best.job.urgent, company=resume.company or "", location=resume.location or "")

    @staticmethod
    def _match_response(match: MatchRecord) -> MatchResponse:
        return MatchResponse(id=match.id, resume_id=match.resume_id, job_id=match.job_id, job_title=match.job.title, score=match.score, matched=match.matched_skills, missing=match.missing_skills, algorithm_version=match.algorithm_version, evidence=[MatchEvidenceResponse(id=e.id, evidence_type=e.evidence_type, skill_name=e.skill_name, evidence_text=e.evidence_text, source_ref=e.source_ref) for e in match.evidence])
