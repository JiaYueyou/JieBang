from __future__ import annotations

import re
import time
import uuid
from difflib import SequenceMatcher

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_runtime import CareerPlanCandidate, CareerPlanningAgent
from app.core.config import DEEPSEEK_TIMEOUT_SECONDS
from app.core.exceptions import InvalidParameterError
from app.core.time import utc_now
from app.domain.agent_status import AgentRunStatus
from app.domain.skill_dictionary import canonical_key
from app.models import AgentRun, InternalPosition
from app.providers import DeepSeekProvider, LLMProvider
from app.schemas.career import CareerAnalysisRequest, CareerAnalysisResponse, ResumeExtractionResponse
from app.services.skill_extractor import RuleSkillExtractor
from app.services.resume_parser import ResumeParser


class CareerService:
    def __init__(self, db: AsyncSession, *, llm_provider: LLMProvider | None = None) -> None:
        self.db = db
        self.llm = llm_provider or DeepSeekProvider()
        self.agent = CareerPlanningAgent(self.llm, timeout_seconds=DEEPSEEK_TIMEOUT_SECONDS)
        self.extractor = RuleSkillExtractor()
        self.resume_parser = ResumeParser()

    async def extract_resume(self, file: UploadFile) -> ResumeExtractionResponse:
        content = await file.read()
        text, warnings = self.resume_parser.parse(
            content, file.filename or "resume.txt"
        )
        return ResumeExtractionResponse(
            filename=file.filename or "resume",
            text=text,
            character_count=len(text),
            warnings=warnings,
        )

    async def analyze(
        self,
        request: CareerAnalysisRequest,
        *,
        user_id: int,
        agent_run_id: str | None = None,
    ) -> CareerAnalysisResponse:
        combined_text = " ".join(filter(None, [request.skill_text, request.resume_text]))
        if not combined_text.strip():
            raise InvalidParameterError("员工技能或简历文本至少填写一项")
        skills = list(dict.fromkeys([
            *self._extract_declared_skills(request.skill_text),
            *self._extract_skills(request.resume_text),
        ]))[:50]
        candidates = await self._build_candidates(request, skills)
        run_id = agent_run_id or str(uuid.uuid4())
        run = await self.db.get(AgentRun, run_id) if agent_run_id else None
        if run is None:
            run = AgentRun(
                id=run_id,
                agent_type=self.agent.agent_type,
                provider=self.llm.provider_name,
                model=self.llm.model_name,
                prompt_version=self.agent.prompt_version,
                input_summary=f"skills={len(skills)} candidates={len(candidates)}",
                status=AgentRunStatus.running,
                started_at=utc_now(),
                retry_count=0,
                created_by=user_id,
            )
            self.db.add(run)
        else:
            run.status = AgentRunStatus.running
            run.started_at = run.started_at or utc_now()
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
            run.status = (
                AgentRunStatus.degraded
                if not bool(getattr(self.llm, "enabled", True))
                else AgentRunStatus.succeeded
            )
        except Exception as exc:
            output = self.agent.template_output(skills, candidates, request.time_budget_weeks)
            output = output.model_copy(update={
                "warnings": ["AI 增强暂未完成，已返回可继续使用的确定性学习路径。"]
            })
            run.status = AgentRunStatus.degraded
            run.error_code = type(exc).__name__
            run.error_message = str(exc)[:2000]
        run.structured_output = output.model_dump(mode="json")
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        run.finished_at = utc_now()
        await self.db.commit()
        return CareerAnalysisResponse(
            **output.model_dump(), agent_run_id=run_id, agent_status=run.status
        )

    async def _build_candidates(self, request: CareerAnalysisRequest, skills: list[str]) -> list[CareerPlanCandidate]:
        rows = list((await self.db.execute(
            select(InternalPosition).where(
                InternalPosition.status == "open",
            ).order_by(InternalPosition.id)
        )).scalars())
        if request.target_job_ids:
            allowed = set(request.target_job_ids)
            rows = [row for row in rows if row.id in allowed]
        candidates: list[CareerPlanCandidate] = []
        for job in rows:
            job_skills = list(dict.fromkeys([
                *(job.required_skills or []),
                *(job.trainable_skills or []),
            ]))
            if not job_skills:
                continue
            existing = [item for item in job_skills if self._skill_is_covered(item, skills)]
            gaps = [item for item in job_skills if not self._skill_is_covered(item, skills)]
            current = round(len(existing) / len(job_skills) * 100)
            recommend = min(100, current + 8)
            after = min(100, current + min(40, len(gaps) * 10))
            candidates.append(CareerPlanCandidate(
                job_id=job.id,
                job=job.title,
                current_match=current,
                after_match=after,
                recommend_score=recommend,
                existing=existing,
                gaps=gaps,
                internal=True,
            ))
        return sorted(candidates, key=lambda item: (-item.recommend_score, len(item.gaps), item.job_id))[:5]

    def _extract_skills(self, text: str) -> list[str]:
        if not text.strip():
            return []
        output = self.extractor.extract(jd_text=text)
        return list(dict.fromkeys(item.name for item in output.skills))[:50]

    def _extract_declared_skills(self, text: str) -> list[str]:
        """保留用户在技能输入框中显式填写、但尚未进入词典的技术。"""
        if not text.strip():
            return []
        recognized = self._extract_skills(text)
        declared = list(recognized)
        for raw_part in re.split(r"[,，;；、\r\n]+", text):
            part = re.sub(r"\s+", " ", raw_part).strip(" .。")
            part = re.sub(r"^(熟悉|掌握|了解|精通|略懂|使用过)", "", part).strip()
            part = re.sub(r"\b\d+(?:\.\d+)?\s*年(?:经验)?\b", "", part).strip()
            if not 1 < len(part) <= 100:
                continue
            if any(marker in part for marker in ("带过", "团队", "负责", "毕业", "在读")):
                continue
            if any(self._normalized_skill(part) == self._normalized_skill(item) for item in recognized):
                continue
            declared.append(part)
        deduplicated: list[str] = []
        seen: set[str] = set()
        for skill in declared:
            key = self._normalized_skill(skill)
            if key and key not in seen:
                seen.add(key)
                deduplicated.append(skill)
        return deduplicated[:50]

    @classmethod
    def _skill_is_covered(cls, required: str, owned_skills: list[str]) -> bool:
        required_key = cls._normalized_skill(required)
        if not required_key:
            return False
        for owned in owned_skills:
            owned_key = cls._normalized_skill(owned)
            if not owned_key:
                continue
            if required_key == owned_key:
                return True
            if min(len(required_key), len(owned_key)) >= 3 and (
                required_key in owned_key or owned_key in required_key
            ):
                shorter = min((required_key, owned_key), key=len)
                if shorter not in {"大模型"}:
                    return True
            if min(len(required_key), len(owned_key)) >= 4 and SequenceMatcher(
                None, required_key, owned_key
            ).ratio() >= 0.66:
                return True
            if len(cls._technical_topics(required_key) & cls._technical_topics(owned_key)) >= 2:
                return True
        return False

    @staticmethod
    def _technical_topics(value: str) -> set[str]:
        topics = (
            "分布式", "训练", "部署", "微调", "向量数据库", "数据分析",
            "自然语言处理", "计算机视觉", "claudecode", "transformer", "rag",
        )
        return {topic for topic in topics if topic in value}

    @staticmethod
    def _normalized_skill(value: str) -> str:
        normalized = canonical_key(value)
        aliases = {
            "nlp": "自然语言处理",
            "cv": "计算机视觉",
            "llm": "大模型",
        }
        normalized = canonical_key(aliases.get(normalized, normalized))
        for marker in (
            "有", "熟悉", "掌握", "了解", "具备", "使用经验", "相关经验", "经验",
            "基础", "高级应用", "深入", "实践", "等", "或", "与", "和",
        ):
            normalized = normalized.replace(marker, "")
        return normalized
