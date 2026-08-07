"""爬取 JD 的幂等导入与技能抽取。"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DATA_DIR
from app.core.exceptions import InvalidParameterError
from app.core.time import utc_now
from app.domain.data_quality import (
    QualityPolicy,
    apply_near_duplicate_penalty,
    evaluate_job_quality,
    near_duplicate_group_id,
    simhash_similarity,
)
from app.domain.job_standardizer import normalize_job_title
from app.models import (
    JobDuplicateCluster,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    SourceTrustPolicy,
    StandardJob,
    StandardJobAlias,
    StandardJobSource,
)
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
logger = logging.getLogger(__name__)


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
        logger.info("job_import_started files=%s", ",".join(path.name for path in paths))
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
        logger.info("job_import_validated files=%d records=%d", len(paths), total)
        imported = duplicates = facts = 0
        near_duplicates = low_quality = time_anomalies = 0
        quality_status_counts = {"accepted": 0, "warning": 0, "rejected": 0}
        imported_raw_ids: list[int] = []
        for index, record in enumerate(records, start=1):
            fingerprint = content_fingerprint(record)
            source_name = normalize_text(record.get("source")) or "unknown"
            external_id = normalize_text(record.get("external_id")) or None
            identity_match = (
                await self.repository.get_source_by_identity(
                    source=source_name,
                    external_id=external_id,
                )
                if external_id
                else None
            )
            if identity_match or await self.repository.get_source_by_fingerprint(fingerprint):
                duplicates += 1
            else:
                policy = await self._quality_policy(source_name)
                evaluation = evaluate_job_quality(
                    record,
                    policy=policy,
                    evaluated_at=utc_now(),
                )
                source = SourceDocument(
                    source=source_name,
                    external_id=external_id,
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
                    posted_at=evaluation.posted_at,
                    crawled_at=evaluation.crawled_at,
                    dedup_status="unique",
                    quality_score=evaluation.quality_score,
                    freshness_score=evaluation.freshness_score,
                    source_trust_score=evaluation.source_trust_score,
                    quality_status=evaluation.quality_status,
                    quality_flags=list(evaluation.quality_flags),
                    content_simhash=evaluation.content_simhash,
                    quality_policy_version=evaluation.policy_version,
                    quality_evaluated_at=evaluation.evaluated_at,
                    normalized_data={
                        "source_file_schema": "job-v1",
                        "quality_policy_version": evaluation.policy_version,
                    },
                )
                await self.repository.add_source_and_raw(source=source, raw=raw)
                await self._ensure_standard_job(raw)
                if await self._mark_near_duplicate(
                    raw,
                    fingerprint=fingerprint,
                    threshold=policy.near_duplicate_threshold,
                ):
                    near_duplicates += 1
                quality_status_counts[raw.quality_status] += 1
                if raw.quality_status == "rejected":
                    low_quality += 1
                if {
                    "missing_posted_at",
                    "invalid_posted_at",
                    "future_posted_at",
                    "missing_or_invalid_crawled_at",
                }.intersection(raw.quality_flags or []):
                    time_anomalies += 1
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
        result = {
            "files": files, "total": total, "imported": imported,
            "duplicates": duplicates, "skill_facts": facts,
            "near_duplicates": near_duplicates,
            "low_quality": low_quality,
            "time_anomalies": time_anomalies,
            "quality_status_counts": quality_status_counts,
            "cross_source_verified": verification["verified_skill_facts"],
            "validation": validation,
            **verification,
        }
        logger.info(
            "job_import_completed total=%d imported=%d duplicates=%d skill_facts=%d verified_facts=%d",
            total, imported, duplicates, facts, verification["verified_skill_facts"],
        )
        return result

    async def _quality_policy(self, source: str) -> QualityPolicy:
        row = await self.db.scalar(
            select(SourceTrustPolicy).where(
                SourceTrustPolicy.source == source,
                SourceTrustPolicy.enabled.is_(True),
            )
        )
        if row is not None:
            return QualityPolicy(
                source_trust_score=row.trust_score,
                freshness_window_days=row.freshness_window_days,
                policy_version=row.policy_version,
            )
        lowered = source.casefold()
        trust = 0.95 if "讯飞" in source or "ifly" in lowered else 0.85 if "智联" in source or "zhaopin" in lowered else 0.7
        row = SourceTrustPolicy(
            source=source,
            trust_score=trust,
            freshness_window_days=90,
            enabled=True,
            policy_version="phase1-v1",
        )
        self.db.add(row)
        await self.db.flush()
        return QualityPolicy(
            source_trust_score=row.trust_score,
            freshness_window_days=row.freshness_window_days,
            policy_version=row.policy_version,
        )

    async def _ensure_standard_job(self, raw: RawJobRecord) -> StandardJob:
        normalized = normalize_job_title(
            raw.title,
            city=raw.city,
            company=raw.company,
            jd_text=raw.jd_text,
        )
        standard = await self.db.scalar(
            select(StandardJob).where(StandardJob.canonical_key == normalized.canonical_key)
        )
        if standard is None:
            standard = StandardJob(
                name=normalized.name,
                canonical_key=normalized.canonical_key,
                aliases=[],
                stack={"algorithm": "ai", "data": "data", "devops": "devops"}.get(
                    normalized.role_family, "backend"
                ),
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
        if raw.title != standard.name:
            aliases.add(raw.title)
        standard.aliases = sorted(aliases)
        alias_key = "".join(ch for ch in raw.title.casefold() if ch.isalnum())
        alias = await self.db.scalar(
            select(StandardJobAlias).where(
                StandardJobAlias.standard_job_id == standard.id,
                StandardJobAlias.alias_key == alias_key,
            )
        )
        if alias is None:
            self.db.add(StandardJobAlias(
                standard_job_id=standard.id,
                alias=raw.title,
                alias_key=alias_key,
                source_type="raw",
                confidence=normalized.confidence,
                normalization_version=normalized.version,
            ))
        raw.standardized_title = standard.name
        raw.standard_job_id = standard.id
        raw.city_code = normalized.city_code
        raw.company_key = normalized.company_key
        raw.work_mode = normalized.work_mode
        raw.employment_type = normalized.employment_type
        raw.normalization_version = normalized.version
        raw.normalization_status = normalized.status
        raw.normalization_confidence = normalized.confidence
        raw.normalized_data = {
            **(raw.normalized_data or {}),
            "job_title": {
                "role_family": normalized.role_family,
                "specialization_key": normalized.specialization_key,
                "occupation_code": normalized.occupation_code,
                "level": normalized.level,
                "city_code": normalized.city_code,
                "work_mode": normalized.work_mode,
                "employment_type": normalized.employment_type,
                "version": normalized.version,
            },
        }
        link = await self.db.scalar(
            select(StandardJobSource).where(
                StandardJobSource.source_type == "raw",
                StandardJobSource.source_id == raw.id,
            )
        )
        if link is None:
            self.db.add(
                StandardJobSource(
                    standard_job_id=standard.id,
                    source_type="raw",
                    source_id=raw.id,
                    original_title=raw.title,
                    confidence=normalized.confidence,
                )
            )
            standard.source_count += 1
        await self.db.flush()
        return standard

    async def _mark_near_duplicate(
        self,
        raw: RawJobRecord,
        *,
        fingerprint: str,
        threshold: float,
    ) -> bool:
        if raw.standard_job_id is None or not raw.content_simhash:
            return False
        rows = (
            await self.db.execute(
                select(RawJobRecord, SourceDocument.content_fingerprint)
                .join(
                    SourceDocument,
                    SourceDocument.id == RawJobRecord.source_document_id,
                )
                .where(
                    RawJobRecord.id != raw.id,
                    RawJobRecord.standard_job_id == raw.standard_job_id,
                    RawJobRecord.content_simhash.is_not(None),
                )
            )
        ).all()
        best: tuple[RawJobRecord, str, float] | None = None
        for candidate, candidate_fingerprint in rows:
            similarity = simhash_similarity(
                raw.content_simhash,
                candidate.content_simhash,
            )
            if best is None or similarity > best[2]:
                best = (candidate, candidate_fingerprint, similarity)
        if best is None or best[2] < threshold:
            return False
        candidate, candidate_fingerprint, similarity = best
        group_id = (
            candidate.near_duplicate_group_id
            or near_duplicate_group_id(fingerprint, candidate_fingerprint)
        )
        # 先确保 cluster 存在，再给 raw 赋值 duplicate_cluster_id。
        # db.get 会触发 autoflush：若先赋值 FK 再 get，autoflush 会把引用
        # 尚不存在 cluster 的 UPDATE 抢先刷出 → MySQL 1452 外键失败。
        # （此处 get 只 flush 无外键依赖的改动，安全。）
        cluster = await self.db.get(JobDuplicateCluster, group_id)
        if cluster is None:
            cluster = JobDuplicateCluster(
                id=group_id,
                standard_job_id=raw.standard_job_id,
                representative_raw_job_id=candidate.id,
                company_key=raw.company_key if raw.company_key == candidate.company_key else None,
                city_code=raw.city_code if raw.city_code == candidate.city_code else None,
                member_count=2,
            )
            self.db.add(cluster)
            cluster_exists = False
        else:
            cluster_exists = True
        for item in (candidate, raw):
            item.dedup_status = "near_duplicate"
            item.near_duplicate_group_id = group_id
            item.near_duplicate_score = max(
                float(item.near_duplicate_score or 0),
                similarity,
            )
            flags = set(item.quality_flags or [])
            flags.add("near_duplicate")
            item.quality_flags = sorted(flags)
            item.quality_score = apply_near_duplicate_penalty(
                float(item.quality_score or 0),
                similarity,
            )
            item.duplicate_cluster_id = group_id
        if cluster_exists:
            # 重新统计 member_count：必须在 duplicate_cluster_id 赋值之后，
            # 计数才包含当前 candidate 与 raw 两条。
            cluster.member_count = int(await self.db.scalar(
                select(func.count(RawJobRecord.id)).where(
                    RawJobRecord.duplicate_cluster_id == group_id
                )
            ) or 0)
        await self.db.flush()
        return True

    async def _cross_validate_facts(self, imported_raw_ids: list[int]) -> dict[str, int]:
        rows = await self.db.execute(
            select(
                RawJobRecord.standard_job_id,
                JobSkillFact.skill_id,
                func.count(distinct(SourceDocument.source)),
            )
            .join(RawJobRecord, JobSkillFact.raw_job_record_id == RawJobRecord.id)
            .join(SourceDocument, RawJobRecord.source_document_id == SourceDocument.id)
            .join(Skill, Skill.id == JobSkillFact.skill_id)
            .where(
                JobSkillFact.raw_job_record_id.is_not(None),
                RawJobRecord.standard_job_id.is_not(None),
                RawJobRecord.quality_status.in_(("accepted", "warning")),
                RawJobRecord.is_excluded.is_(False),
                Skill.validation_status == "approved",
            )
            .group_by(RawJobRecord.standard_job_id, JobSkillFact.skill_id)
        )
        source_counts = {
            (standard_job_id, skill_id): int(count)
            for standard_job_id, skill_id, count in rows
        }
        facts = (
            await self.db.execute(
                select(
                    JobSkillFact,
                    RawJobRecord.standard_job_id,
                    RawJobRecord.quality_status,
                    RawJobRecord.is_excluded,
                    Skill.validation_status,
                )
                .join(RawJobRecord, JobSkillFact.raw_job_record_id == RawJobRecord.id)
                .join(Skill, Skill.id == JobSkillFact.skill_id)
                .where(JobSkillFact.raw_job_record_id.is_not(None))
            )
        ).all()
        for fact, standard_job_id, quality_status, is_excluded, skill_status in facts:
            if fact.verification_status == "rejected":
                continue
            fact.source_count = source_counts.get(
                (standard_job_id, fact.skill_id),
                1,
            )
            fact.verification_status = (
                "verified"
                if (
                    fact.source_count >= 2
                    and fact.confidence >= 0.75
                    and quality_status in {"accepted", "warning"}
                    and not is_excluded
                    and skill_status == "approved"
                )
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
