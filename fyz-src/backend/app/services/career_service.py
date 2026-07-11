from __future__ import annotations

import io
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_runtime import CareerPlanCandidate, CareerPlanningAgent
from app.core.config import DEEPSEEK_TIMEOUT_SECONDS
from app.core.exceptions import InvalidParameterError
from app.domain.skill_dictionary import canonical_key
from app.models import AgentRun, JobPosting
from app.providers import DeepSeekProvider, LLMProvider
from app.schemas.career import CareerAnalysisRequest, CareerAnalysisResponse, ResumeExtractionResponse
from app.services.skill_extractor import RuleSkillExtractor


class CareerService:
    def __init__(self, db: AsyncSession, *, llm_provider: LLMProvider | None = None) -> None:
        self.db = db
        self.llm = llm_provider or DeepSeekProvider()
        self.agent = CareerPlanningAgent(self.llm, timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS)
        self.extractor = RuleSkillExtractor()

    async def extract_resume(self, file: UploadFile) -> ResumeExtractionResponse:
        content = await file.read()
        if not content:
            raise InvalidParameterError("简历文件为空")
        if len(content) > 20 * 1024 * 1024:
            raise InvalidParameterError("简历文件不能超过 20MB")
        suffix = Path(file.filename or "resume.txt").suffix.lower()
        warnings: list[str] = []
        if suffix in {".txt", ".md"}:
            text = self._decode_text(content)
        elif suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:
                raise InvalidParameterError("服务端未安装 PDF 解析依赖 pypdf") from exc
            text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
        elif suffix == ".docx":
            try:
                from docx import Document
            except ImportError as exc:
                raise InvalidParameterError("服务端未安装 Word 解析依赖 python-docx") from exc
            text = "\n".join(paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs)
        else:
            raise InvalidParameterError("仅支持 TXT、Markdown、PDF 和 DOCX 简历")
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())[:20000]
        if not text:
            raise InvalidParameterError("未能从简历中解析出文本")
        if suffix == ".pdf" and len(text) < 30:
            warnings.append("PDF 可能是扫描件，建议补充文本技能描述。")
        return ResumeExtractionResponse(
            filename=file.filename or "resume",
            text=text,
            character_count=len(text),
            warnings=warnings,
        )

    async def analyze(self, request: CareerAnalysisRequest, *, user_id: int) -> CareerAnalysisResponse:
        combined_text = " ".join(filter(None, [request.skill_text, request.resume_text]))
        if not combined_text.strip():
            raise InvalidParameterError("员工技能或简历文本至少填写一项")
        skills = self._extract_skills(combined_text)
        candidates = await self._build_candidates(request, skills)
        run_id = str(uuid.uuid4())
        run = AgentRun(
            id=run_id,
            agent_type=self.agent.agent_type,
            provider=self.llm.provider_name,
            model=self.llm.model_name,
            prompt_version=self.agent.prompt_version,
            input_summary=f"skills={len(skills)} candidates={len(candidates)}",
            status="running",
            retry_count=0,
            created_by=user_id,
        )
        self.db.add(run)
        await self.db.flush()
        started = time.perf_counter()
        try:
            output = await self.agent.generate(
                resume_text=combined_text,
                skills=skills,
                enterprise_tech=request.enterprise_tech,
                candidates=candidates,
                time_budget_weeks=request.time_budget_weeks,
            )
            run.status = "degraded" if not bool(getattr(self.llm, "enabled", True)) else "succeeded"
        except Exception as exc:
            output = self.agent.template_output(skills, candidates, request.time_budget_weeks)
            run.status = "degraded"
            run.error_code = type(exc).__name__
            run.error_message = str(exc)[:2000]
        run.structured_output = output.model_dump(mode="json")
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        run.finished_at = datetime.utcnow()
        await self.db.commit()
        return CareerAnalysisResponse(**output.model_dump(), agent_run_id=run_id)

    async def _build_candidates(self, request: CareerAnalysisRequest, skills: list[str]) -> list[CareerPlanCandidate]:
        rows = list((await self.db.execute(
            select(JobPosting).where(
                JobPosting.deleted_at.is_(None),
                JobPosting.status == "open",
            ).order_by(JobPosting.id)
        )).scalars())
        if request.target_job_ids:
            allowed = set(request.target_job_ids)
            rows = [row for row in rows if row.id in allowed]
        internal_names = {item.casefold() for item in request.internal_jobs}
        enterprise_skills = self._extract_skills(request.enterprise_tech) if request.enterprise_tech else []
        user_keys = {canonical_key(item): item for item in skills}
        candidates: list[CareerPlanCandidate] = []
        for job in rows:
            job_skills = list(dict.fromkeys(item.name for item in job.skills))
            if not job_skills:
                extracted = self.extractor.extract(jd_text=job.jd_text, responsibilities=" ".join(job.responsibilities), requirements=" ".join(job.requirements))
                job_skills = [item.name for item in extracted.skills]
            if not job_skills:
                continue
            internal = any(name in job.title.casefold() or job.title.casefold() in name for name in internal_names)
            if internal:
                job_skills = list(dict.fromkeys([*job_skills, *enterprise_skills]))
            existing = [item for item in job_skills if canonical_key(item) in user_keys]
            gaps = [item for item in job_skills if canonical_key(item) not in user_keys]
            current = round(len(existing) / len(job_skills) * 100)
            recommend = min(100, current + (8 if internal else 0))
            after = min(100, current + min(40, len(gaps) * 10))
            candidates.append(CareerPlanCandidate(
                job_id=job.id,
                job=job.title,
                current_match=current,
                after_match=after,
                recommend_score=recommend,
                existing=existing,
                gaps=gaps,
                internal=internal,
            ))
        return sorted(candidates, key=lambda item: (-item.recommend_score, len(item.gaps), item.job_id))[:5]

    def _extract_skills(self, text: str) -> list[str]:
        output = self.extractor.extract(jd_text=text)
        skills = [item.name for item in output.skills]
        if not skills:
            skills = [part.strip() for part in text.replace("，", ",").split(",") if 1 < len(part.strip()) <= 100]
        return list(dict.fromkeys(skills))[:50]

    @staticmethod
    def _decode_text(content: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise InvalidParameterError("无法识别文本文件编码")
