"""爬取 JD 的幂等导入与技能抽取。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DATA_DIR
from app.core.exceptions import InvalidParameterError
from app.models import JobSkillFact, RawJobRecord, SourceDocument
from app.repositories import SkillRepository
from app.services.job_import_schema import normalize_and_validate_records
from app.services.skill_extractor import content_fingerprint, normalize_text
from app.services.skill_service import SkillService

ALLOWED_FILES = {
    "jd_crawl_ifly.json", "jd_crawl_zl.json", "jd_crawl2.json",
    "jd_crawl_ifly_full.json", "jd_crawl_ifly_merged.json",
    "jd_crawl_zl_new.json",
}
ALLOWED_FILE_PATTERNS = (
    re.compile(r"iflytek_\d+\.json"),
    re.compile(r"zhaopin_\d+\.json"),
)


def standardize_title(title: str) -> str:
    value = re.sub(r"[（(][^)）]*[)）]", "", title or "")
    value = re.sub(r"(?:校招|实习生?|应届|急聘|高薪)", "", value)
    return re.sub(r"\s+", " ", value).strip(" -—_")


class ImportService:
    def __init__(self, db: AsyncSession, *, skill_service: SkillService | None = None):
        self.db = db
        self.repository = SkillRepository(db)
        self.skill_service = skill_service or SkillService(db, repository=self.repository)

    @staticmethod
    def resolve_files(files: list[str]) -> list[Path]:
        root = Path(DATA_DIR).resolve()
        paths = []
        for name in files:
            is_allowed = name in ALLOWED_FILES or any(
                pattern.fullmatch(name) for pattern in ALLOWED_FILE_PATTERNS
            )
            if Path(name).name != name or not is_allowed:
                raise InvalidParameterError(f"不允许导入文件：{name}")
            path = (root / name).resolve()
            if root not in path.parents or not path.is_file():
                raise InvalidParameterError(f"数据文件不存在：{name}")
            paths.append(path)
        return paths

    async def import_files(self, files: list[str], *, progress_callback=None) -> dict:
        paths = self.resolve_files(files)
        records: list[dict] = []
        validation: list[dict] = []
        for path in paths:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise InvalidParameterError(f"无法解析数据文件：{path.name}") from exc
            if not isinstance(payload, list):
                raise InvalidParameterError(f"数据文件必须是数组：{path.name}")
            normalized, report = normalize_and_validate_records(
                payload, filename=path.name
            )
            validation.append(report)
            if report["failed"]:
                first_error = report["errors"][0]
                details = "；".join(first_error["errors"])
                raise InvalidParameterError(
                    f"job-v1 校验失败：{path.name} 第 {first_error['index']} 条，{details}"
                )
            records.extend(normalized)
        total = len(records)
        imported = duplicates = facts = 0
        imported_raw_ids: list[int] = []
        for index, record in enumerate(records, start=1):
            fingerprint = content_fingerprint(record)
            if await self.repository.get_source_by_fingerprint(fingerprint):
                duplicates += 1
            else:
                source = SourceDocument(
                    source=normalize_text(record.get("source")) or "unknown",
                    external_id=None,
                    url=normalize_text(record.get("url")) or None,
                    title=normalize_text(record.get("title"))[:255],
                    company=normalize_text(record.get("company"))[:255] or None,
                    content_fingerprint=fingerprint,
                    content_summary=normalize_text(record.get("jd_text"))[:1000],
                    source_meta={
                        "posted_at": record.get("posted_at"),
                        "crawled_at": record.get("crawled_at"),
                    },
                )
                raw = RawJobRecord(
                    source_document_id=0,
                    title=normalize_text(record.get("title"))[:255],
                    standardized_title=standardize_title(normalize_text(record.get("title")))[:255],
                    company=normalize_text(record.get("company"))[:255] or None,
                    city=normalize_text(record.get("city"))[:100] or None,
                    salary_text=normalize_text(record.get("salary"))[:100] or None,
                    experience_text=normalize_text(record.get("experience"))[:100] or None,
                    education_text=normalize_text(record.get("education"))[:100] or None,
                    jd_text=normalize_text(record.get("jd_text")),
                    responsibilities=normalize_text(record.get("responsibilities")),
                    requirements=normalize_text(record.get("requirements")),
                    keywords=normalize_text(record.get("keywords") or record.get("keyword")),
                    posted_at_text=normalize_text(record.get("posted_at"))[:100] or None,
                    crawled_at_text=normalize_text(record.get("crawled_at"))[:100] or None,
                    dedup_status="unique",
                    normalized_data={"source_file_schema": "job-v1"},
                )
                await self.repository.add_source_and_raw(source=source, raw=raw)
                output = await self.skill_service.extract_text(
                    jd_text=raw.jd_text,
                    responsibilities=raw.responsibilities,
                    requirements=raw.requirements,
                )
                facts += await self.skill_service.persist_raw_facts(
                    raw_job_record_id=raw.id, output=output
                )
                imported_raw_ids.append(raw.id)
                imported += 1
            if index % 10 == 0:
                await self.db.commit()
            if progress_callback:
                await progress_callback(int(index * 100 / max(total, 1)))
        await self.db.commit()
        verification = await self._cross_validate_facts(imported_raw_ids)
        await self.db.commit()
        return {
            "files": files, "total": total, "imported": imported,
            "duplicates": duplicates, "skill_facts": facts,
            "validation": validation,
            **verification,
        }

    async def _cross_validate_facts(self, imported_raw_ids: list[int]) -> dict[str, int]:
        rows = await self.db.execute(
            select(
                JobSkillFact.skill_id,
                func.count(distinct(SourceDocument.source)),
            )
            .join(RawJobRecord, JobSkillFact.raw_job_record_id == RawJobRecord.id)
            .join(SourceDocument, RawJobRecord.source_document_id == SourceDocument.id)
            .where(JobSkillFact.raw_job_record_id.is_not(None))
            .group_by(JobSkillFact.skill_id)
        )
        source_counts = dict(rows.all())
        facts = (
            await self.db.execute(
                select(JobSkillFact).where(JobSkillFact.raw_job_record_id.is_not(None))
            )
        ).scalars()
        for fact in facts:
            fact.source_count = int(source_counts.get(fact.skill_id, 1))
            fact.verification_status = (
                "verified"
                if fact.source_count >= 2 and fact.confidence >= 0.75
                else "unverified"
            )
        await self.db.flush()
        if not imported_raw_ids:
            return {"verified_skill_facts": 0, "unverified_skill_facts": 0}
        verified = await self.db.scalar(
            select(func.count(JobSkillFact.id)).where(
                JobSkillFact.raw_job_record_id.in_(imported_raw_ids),
                JobSkillFact.verification_status == "verified",
            )
        )
        unverified = await self.db.scalar(
            select(func.count(JobSkillFact.id)).where(
                JobSkillFact.raw_job_record_id.in_(imported_raw_ids),
                JobSkillFact.verification_status == "unverified",
            )
        )
        return {
            "verified_skill_facts": int(verified or 0),
            "unverified_skill_facts": int(unverified or 0),
        }
