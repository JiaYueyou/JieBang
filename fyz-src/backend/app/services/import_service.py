"""爬取 JD 的幂等导入与技能抽取。"""

from __future__ import annotations

import json
import hashlib
import logging
import re
import uuid
from pathlib import Path

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DATA_DIR, JOB_MISSING_CLOSE_THRESHOLD
from app.core.exceptions import InvalidParameterError
from app.core.time import utc_now
from app.domain.data_quality import (
    QualityPolicy,
    apply_near_duplicate_penalty,
    evaluate_job_quality,
    near_duplicate_group_id,
    parse_source_datetime,
    simhash_similarity,
)
from app.domain.job_standardizer import normalize_job_title
from app.domain.job_lifecycle import current_external_job_condition
from app.models import (
    ExternalJobIdentity,
    ExternalJobVersion,
    JobImportQuarantine,
    JobDuplicateCluster,
    JobSourceObservation,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    SourceSnapshot,
    SourceTrustPolicy,
    StandardJob,
    StandardJobAlias,
    StandardJobSource,
)
from app.repositories import SkillRepository
from app.services.job_import_schema import normalize_and_validate_records
from app.services.skill_extractor import content_fingerprint, normalize_text
from app.services.skill_service import SkillService

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
            if Path(name).suffix.casefold() != ".json":
                raise InvalidParameterError(f"仅支持导入 JSON 文件：{name}")
            path = (root / name).resolve()
            if (path != root and root not in path.parents) or not path.is_file():
                raise InvalidParameterError(f"数据文件不存在：{name}")
            paths.append(path)
        return paths

    async def import_files(self, files: list[str], *, progress_callback=None) -> dict:
        paths = self.resolve_files(files)
        logger.info("job_import_started files=%s", ",".join(path.name for path in paths))
        records: list[dict] = []
        validation: list[dict] = []
        snapshot_manifests: list[dict] = []
        quarantined_records = 0
        input_records = 0
        for path in paths:
            manifest: dict | None = None
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise InvalidParameterError(f"无法解析数据文件：{path.name}") from exc
            if not isinstance(payload, list):
                raise InvalidParameterError(f"数据文件必须是数组：{path.name}")
            input_records += len(payload)
            manifest_path = path.with_name(path.name + ".manifest")
            if manifest_path.is_file():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise InvalidParameterError(
                        f"无法解析快照 manifest：{manifest_path.name}"
                    ) from exc
                if (
                    not isinstance(manifest, dict)
                    or manifest.get("schema_version") != "crawler-snapshot-manifest-v1"
                ):
                    raise InvalidParameterError(
                        f"快照 manifest 版本无效：{manifest_path.name}"
                    )
                payload_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
                if manifest.get("payload_sha256") != payload_sha256:
                    raise InvalidParameterError(
                        f"快照与 manifest 校验和不一致：{path.name}"
                    )
                if int(manifest.get("record_count", -1)) != len(payload):
                    raise InvalidParameterError(
                        f"快照与 manifest 记录数不一致：{path.name}"
                    )
            normalized, report = normalize_and_validate_records(
                payload, filename=path.name
            )
            if manifest is not None and normalized:
                record_sources = {
                    normalize_text(record.get("source")) or "unknown"
                    for record in normalized
                }
                declared_source = normalize_text(manifest.get("source")) or "unknown"
                if record_sources != {declared_source}:
                    raise InvalidParameterError(
                        f"快照记录来源与 manifest 不一致：{path.name}"
                    )
            if report["failed"]:
                quarantined_records += await self._quarantine_invalid_records(
                    source_file=path.name,
                    payload=payload,
                    errors=report["errors"],
                )
            validation.append({
                **report,
                "errors": report["errors"][:20],
                "quarantined": report["failed"],
            })
            if manifest is not None:
                manifest_for_import = {**manifest, "_source_file": path.name}
                if report["failed"]:
                    # A malformed row may represent an otherwise visible job.
                    # Valid rows can still be imported, but absence is unsafe.
                    manifest_for_import.update({
                        "snapshot_complete": False,
                        "snapshot_type": "delta",
                        "quarantined_records": report["failed"],
                    })
                snapshot_manifests.append(manifest_for_import)
            for record in normalized:
                record["_source_file"] = path.name
            records.extend(normalized)
        total = input_records
        valid_total = len(records)
        logger.info(
            "job_import_validated files=%d records=%d quarantined=%d",
            len(paths), valid_total, quarantined_records,
        )
        snapshot_context = await self._prepare_source_snapshots(
            records, snapshot_manifests
        )
        imported = duplicates = facts = observations = 0
        versions_created = reopened_jobs = missing_observations = closed_jobs = 0
        near_duplicates = low_quality = time_anomalies = 0
        quality_status_counts = {"accepted": 0, "warning": 0, "rejected": 0}
        imported_raw_ids: list[int] = []
        affected_standard_job_ids: set[int] = set()
        for index, record in enumerate(records, start=1):
            fingerprint = content_fingerprint(record)
            source_name = normalize_text(record.get("source"))
            if source_name and set(source_name) == {"?"}:
                raise InvalidParameterError(
                    f"数据来源名称异常（仅包含问号）：第 {index} 条记录"
                )
            source_name = source_name or "unknown"
            external_id = normalize_text(record.get("external_id")) or None
            snapshot = snapshot_context.get((record.get("_source_file"), source_name))
            observed_at = parse_source_datetime(
                record.get("crawled_at"), observed_at=utc_now()
            ) or utc_now()
            identity, was_closed, is_stale = await self._ensure_external_identity(
                source=source_name,
                external_id=external_id,
                url=normalize_text(record.get("url")) or None,
                title=normalize_text(record.get("title")),
                observed_at=observed_at,
            )
            reopened_jobs += int(was_closed and not is_stale)
            identity_match = (
                await self.repository.get_source_by_identity(
                    source=source_name,
                    external_id=external_id,
                )
                if external_id
                else None
            )
            fingerprint_match = await self.repository.get_source_by_fingerprint(fingerprint)
            existing_document = (
                identity_match
                if identity_match and identity_match.content_fingerprint == fingerprint
                else fingerprint_match
            )
            policy = await self._quality_policy(source_name)
            evaluation = evaluate_job_quality(
                record,
                policy=policy,
                evaluated_at=utc_now(),
            )
            if existing_document:
                if existing_document.external_job_identity_id is None:
                    existing_document.external_job_identity_id = identity.id
                version_created = await self._ensure_external_version(
                    identity=identity,
                    source_document=existing_document,
                    fingerprint=fingerprint,
                    observed_at=observed_at,
                    was_closed=was_closed,
                    is_stale=is_stale,
                )
                versions_created += int(version_created)
                if version_created and not is_stale:
                    standard_job_id = await self.db.scalar(
                        select(RawJobRecord.standard_job_id).where(
                            RawJobRecord.source_document_id == existing_document.id
                        )
                    )
                    if standard_job_id is not None:
                        affected_standard_job_ids.add(int(standard_job_id))
                duplicates += 1
                observations += await self._record_observation(
                    source_document=existing_document,
                    identity=identity,
                    snapshot=snapshot,
                    record=record,
                    fingerprint=fingerprint,
                    evaluation=evaluation,
                    event_type=(
                        "stale" if is_stale else "changed" if version_created else "seen"
                    ),
                )
            else:
                incoming_source_meta = record.get("source_meta")
                if not isinstance(incoming_source_meta, dict):
                    incoming_source_meta = {}
                source = SourceDocument(
                    external_job_identity_id=identity.id,
                    source=source_name,
                    external_id=external_id,
                    url=normalize_text(record.get("url")) or None,
                    title=normalize_text(record.get("title"))[:255],
                    company=normalize_text(record.get("company"))[:255] or None,
                    content_fingerprint=fingerprint,
                    content_summary=normalize_text(record.get("jd_text"))[:1000],
                    source_meta={
                        **incoming_source_meta,
                        "posted_at": record.get("posted_at"),
                        "crawled_at": record.get("crawled_at"),
                        "archived_at": record.get("archived_at"),
                        "archive_url": normalize_text(record.get("archive_url")) or None,
                        "source_type": normalize_text(
                            record.get("source_type")
                            or incoming_source_meta.get("source_type")
                        ) or None,
                        "license_note": normalize_text(record.get("license_note")) or None,
                        "supersedes_source_document_id": (
                            identity_match.id if identity_match is not None else None
                        ),
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
                new_version_created = await self._ensure_external_version(
                    identity=identity,
                    source_document=source,
                    fingerprint=fingerprint,
                    observed_at=observed_at,
                    was_closed=was_closed,
                    is_stale=is_stale,
                )
                versions_created += int(new_version_created)
                observations += await self._record_observation(
                    source_document=source,
                    identity=identity,
                    snapshot=snapshot,
                    record=record,
                    fingerprint=fingerprint,
                    evaluation=evaluation,
                    event_type="stale" if is_stale else "seen",
                )
                standard_job = await self._ensure_standard_job(raw)
                affected_standard_job_ids.add(int(standard_job.id))
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
                await progress_callback(int(index * 100 / max(valid_total, 1)))
        lifecycle = await self._reconcile_full_snapshots(snapshot_context, records)
        missing_observations += lifecycle["missing_observations"]
        closed_jobs += lifecycle["closed_jobs"]
        affected_standard_job_ids.update(lifecycle["affected_standard_job_ids"])
        await self.db.commit()
        verification = await self._cross_validate_facts(imported_raw_ids)
        await self.db.commit()
        result = {
            "files": files, "total": total, "imported": imported,
            "valid_records": valid_total,
            "quarantined_records": quarantined_records,
            "duplicates": duplicates, "skill_facts": facts,
            "near_duplicates": near_duplicates,
            "low_quality": low_quality,
            "time_anomalies": time_anomalies,
            "quality_status_counts": quality_status_counts,
            "cross_source_verified": verification["verified_skill_facts"],
            "observations": observations,
            "versions_created": versions_created,
            "reopened_jobs": reopened_jobs,
            "missing_observations": missing_observations,
            "closed_jobs": closed_jobs,
            "source_snapshots": len({snapshot.id for snapshot in snapshot_context.values()}),
            "affected_standard_job_ids": sorted(affected_standard_job_ids),
            "validation": validation,
            **verification,
        }
        logger.info(
            "job_import_completed total=%d imported=%d duplicates=%d skill_facts=%d verified_facts=%d",
            total, imported, duplicates, facts, verification["verified_skill_facts"],
        )
        return result

    async def _record_observation(
        self,
        *,
        source_document: SourceDocument,
        identity: ExternalJobIdentity | None,
        snapshot: SourceSnapshot | None,
        record: dict,
        fingerprint: str,
        evaluation,
        event_type: str = "seen",
    ) -> int:
        observed_at = evaluation.crawled_at or utc_now()
        observed_on = observed_at.date()
        existing = await self.db.scalar(
            select(JobSourceObservation.id).where(
                JobSourceObservation.source_document_id == source_document.id,
                JobSourceObservation.observed_on == observed_on,
            )
        )
        if existing is not None:
            return 0

        source_meta = record.get("source_meta")
        if not isinstance(source_meta, dict):
            source_meta = {}
        if evaluation.posted_at is not None:
            source_event_at = evaluation.posted_at
            source_event_type = "published_at"
        else:
            source_event_at = None
            source_event_type = "observed_at"
            for field, event_type in (
                ("source_updated_at", "updated_at"),
                ("snapshot_observed_at", "snapshot_at"),
            ):
                value = source_meta.get(field)
                parsed = parse_source_datetime(value, observed_at=observed_at)
                if parsed is not None:
                    source_event_at = parsed
                    source_event_type = event_type
                    break
        self.db.add(
            JobSourceObservation(
                external_job_identity_id=identity.id if identity else None,
                source_snapshot_id=snapshot.id if snapshot else None,
                source_document_id=source_document.id,
                source=source_document.source,
                external_id=source_document.external_id,
                observed_on=observed_on,
                observed_at=observed_at,
                source_event_at=source_event_at,
                source_event_type=source_event_type,
                content_fingerprint=fingerprint,
                snapshot_key=normalize_text(record.get("_source_file"))[:255] or None,
                status="active",
                event_type=event_type,
            )
        )
        await self.db.flush()
        return 1

    @staticmethod
    def _identity_key(*, source: str, external_id: str | None, url: str | None, title: str) -> str:
        stable = external_id or url or title
        return hashlib.sha256(f"{source.casefold()}|{stable}".encode("utf-8")).hexdigest()

    async def _ensure_external_identity(
        self,
        *,
        source: str,
        external_id: str | None,
        url: str | None,
        title: str,
        observed_at,
    ) -> tuple[ExternalJobIdentity, bool, bool]:
        identity_key = self._identity_key(
            source=source, external_id=external_id, url=url, title=title
        )
        identity = await self.db.scalar(
            select(ExternalJobIdentity).where(
                ExternalJobIdentity.source == source,
                ExternalJobIdentity.identity_key == identity_key,
            )
        )
        if identity is None:
            identity = ExternalJobIdentity(
                id=str(uuid.uuid4()), source=source, identity_key=identity_key,
                external_id=external_id, canonical_url=url,
                lifecycle_status="active", missing_streak=0,
                first_seen_at=observed_at, last_seen_at=observed_at,
            )
            self.db.add(identity)
            await self.db.flush()
            return identity, False, False
        was_closed = identity.lifecycle_status == "closed"
        previous_seen = identity.last_seen_at.replace(tzinfo=None)
        incoming_seen = observed_at.replace(tzinfo=None)
        is_stale = incoming_seen < previous_seen
        identity.external_id = identity.external_id or external_id
        identity.canonical_url = url or identity.canonical_url
        if not is_stale:
            identity.lifecycle_status = "active"
            identity.missing_streak = 0
            identity.last_seen_at = observed_at
            identity.closed_at = None
        return identity, was_closed, is_stale

    async def _ensure_external_version(
        self,
        *,
        identity: ExternalJobIdentity,
        source_document: SourceDocument,
        fingerprint: str,
        observed_at,
        was_closed: bool,
        is_stale: bool,
    ) -> bool:
        current = None
        if identity.current_version_id:
            current = await self.db.get(ExternalJobVersion, identity.current_version_id)
        if current is not None and current.content_fingerprint == fingerprint:
            if was_closed and not is_stale:
                current.is_current = True
                current.valid_to = None
                current.change_type = "reopened"
            return False
        if current is not None and not is_stale:
            current.is_current = False
            current.valid_to = observed_at
        existing = await self.db.scalar(
            select(ExternalJobVersion).where(
                ExternalJobVersion.identity_id == identity.id,
                ExternalJobVersion.content_fingerprint == fingerprint,
            )
        )
        if existing is not None:
            if not is_stale:
                existing.is_current = True
                existing.valid_to = None
                existing.change_type = "reopened"
                identity.current_version_id = existing.id
            return False
        max_version = int(await self.db.scalar(
            select(func.max(ExternalJobVersion.version_no)).where(
                ExternalJobVersion.identity_id == identity.id
            )
        ) or 0)
        version = ExternalJobVersion(
            id=str(uuid.uuid4()), identity_id=identity.id,
            source_document_id=source_document.id, version_no=max_version + 1,
            content_fingerprint=fingerprint,
            change_type=(
                "stale" if is_stale else "reopened" if was_closed
                else ("created" if max_version == 0 else "updated")
            ),
            valid_from=observed_at,
            valid_to=observed_at if is_stale else None,
            is_current=not is_stale,
        )
        self.db.add(version)
        await self.db.flush()
        if not is_stale:
            identity.current_version_id = version.id
        return True

    async def _prepare_source_snapshots(
        self, records: list[dict], manifests: list[dict] | None = None
    ) -> dict[tuple[str, str], SourceSnapshot]:
        grouped: dict[tuple[str, str], list[dict]] = {}
        for record in records:
            source = normalize_text(record.get("source")) or "unknown"
            grouped.setdefault((record.get("_source_file"), source), []).append(record)
        manifest_map: dict[tuple[str, str], dict] = {}
        for manifest in manifests or []:
            source = normalize_text(manifest.get("source")) or "unknown"
            manifest_map[(manifest.get("_source_file"), source)] = manifest
            grouped.setdefault((manifest.get("_source_file"), source), [])
        result: dict[tuple[str, str], SourceSnapshot] = {}
        for (filename, source), rows in grouped.items():
            snapshot_key = normalize_text(filename)[:255]
            manifest = manifest_map.get((filename, source), {})
            meta = rows[0].get("source_meta") if rows else {}
            meta = meta if isinstance(meta, dict) else {}
            snapshot_complete = bool(
                manifest.get("snapshot_complete", meta.get("snapshot_complete"))
            )
            snapshot_type = "full" if snapshot_complete else normalize_text(
                manifest.get("snapshot_type") or meta.get("snapshot_type")
            ).casefold() or "delta"
            observed_at = parse_source_datetime(
                manifest.get("observed_at")
                or meta.get("snapshot_observed_at")
                or (rows[0].get("crawled_at") if rows else None),
                observed_at=utc_now(),
            ) or utc_now()
            scope = manifest.get("scope")
            if not isinstance(scope, dict):
                scope = {"source": source}
            scope_payload = json.dumps(
                scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            scope_hash = hashlib.sha256(scope_payload.encode("utf-8")).hexdigest()
            declared_scope_hash = normalize_text(manifest.get("scope_hash"))
            if declared_scope_hash and declared_scope_hash != scope_hash:
                raise InvalidParameterError(
                    f"快照 scope_hash 无效：{source}/{snapshot_key}"
                )
            checksum = hashlib.sha256("|".join(sorted(
                content_fingerprint(row) for row in rows
            )).encode("utf-8")).hexdigest()
            existing = await self.db.scalar(select(SourceSnapshot).where(
                SourceSnapshot.source == source,
                SourceSnapshot.snapshot_key == snapshot_key,
            ))
            if existing is not None:
                same_observed_at = (
                    existing.observed_at.replace(tzinfo=None)
                    == observed_at.replace(tzinfo=None)
                )
                if (
                    existing.checksum != checksum
                    or existing.record_count != len(rows)
                    or existing.snapshot_type != snapshot_type
                    or existing.scope_hash != scope_hash
                    or not same_observed_at
                ):
                    raise InvalidParameterError(
                        f"快照键冲突且内容或 manifest 不一致：{source}/{snapshot_key}"
                    )
                result[(filename, source)] = existing
                continue
            latest_completed = await self.db.scalar(
                select(func.max(SourceSnapshot.observed_at)).where(
                    SourceSnapshot.source == source,
                    SourceSnapshot.scope_hash == scope_hash,
                    SourceSnapshot.status == "completed",
                )
            )
            if latest_completed is not None and (
                observed_at.replace(tzinfo=None) <= latest_completed.replace(tzinfo=None)
            ):
                raise InvalidParameterError(
                    f"拒绝乱序快照：{source}/{snapshot_key}"
                )
            snapshot = SourceSnapshot(
                id=str(uuid.uuid4()), source=source, snapshot_key=snapshot_key,
                snapshot_type=snapshot_type, observed_at=observed_at,
                scope_hash=scope_hash, scope_json=scope,
                record_count=len(rows), checksum=checksum, status="processing",
            )
            self.db.add(snapshot)
            await self.db.flush()
            result[(filename, source)] = snapshot
        return result

    async def _quarantine_invalid_records(
        self, *, source_file: str, payload: list, errors: list[dict]
    ) -> int:
        created = 0
        for error in errors:
            index = error.get("index")
            if not isinstance(index, int) or not 0 <= index < len(payload):
                continue
            raw = payload[index]
            rendered = json.dumps(
                raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            payload_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
            existing = await self.db.scalar(select(JobImportQuarantine.id).where(
                JobImportQuarantine.source_file == source_file,
                JobImportQuarantine.record_index == index,
                JobImportQuarantine.payload_hash == payload_hash,
            ))
            if existing is not None:
                continue
            raw_dict = raw if isinstance(raw, dict) else {}
            error_codes = [str(value) for value in error.get("errors") or []]
            self.db.add(JobImportQuarantine(
                id=str(uuid.uuid4()),
                source_file=source_file,
                record_index=index,
                payload_hash=payload_hash,
                source=normalize_text(raw_dict.get("source")) or None,
                external_id=normalize_text(raw_dict.get("external_id")) or None,
                raw_payload=raw,
                error_codes=error_codes,
                error_message="；".join(error_codes)[:4000],
                status="pending",
            ))
            created += 1
        if created:
            await self.db.flush()
        return created

    async def _reconcile_full_snapshots(
        self,
        snapshots: dict[tuple[str, str], SourceSnapshot],
        records: list[dict],
    ) -> dict[str, int]:
        missing_observations = closed_jobs = 0
        affected_standard_job_ids: set[int] = set()
        for key, snapshot in snapshots.items():
            if snapshot.status == "completed":
                continue
            filename, source = key
            source_records = [
                row for row in records
                if row.get("_source_file") == filename
                and (normalize_text(row.get("source")) or "unknown") == source
            ]
            seen_keys = {
                self._identity_key(
                    source=source,
                    external_id=normalize_text(row.get("external_id")) or None,
                    url=normalize_text(row.get("url")) or None,
                    title=normalize_text(row.get("title")),
                )
                for row in source_records
            }
            latest_completed = await self.db.scalar(
                select(func.max(SourceSnapshot.observed_at)).where(
                    SourceSnapshot.source == source,
                    SourceSnapshot.scope_hash == snapshot.scope_hash,
                    SourceSnapshot.status == "completed",
                    SourceSnapshot.id != snapshot.id,
                )
            )
            if latest_completed is not None and (
                snapshot.observed_at.replace(tzinfo=None)
                <= latest_completed.replace(tzinfo=None)
            ):
                snapshot.status = "ignored_stale"
                snapshot.completed_at = utc_now()
                continue
            if snapshot.snapshot_type == "full":
                identities = list((await self.db.execute(
                    select(ExternalJobIdentity)
                    .join(
                        JobSourceObservation,
                        JobSourceObservation.external_job_identity_id
                        == ExternalJobIdentity.id,
                    )
                    .join(
                        SourceSnapshot,
                        JobSourceObservation.source_snapshot_id == SourceSnapshot.id,
                    )
                    .where(
                        ExternalJobIdentity.source == source,
                        ExternalJobIdentity.lifecycle_status == "active",
                        SourceSnapshot.scope_hash == snapshot.scope_hash,
                        SourceSnapshot.id != snapshot.id,
                    )
                    .distinct()
                )).scalars())
                for identity in identities:
                    if identity.identity_key in seen_keys:
                        continue
                    current = await self.db.get(ExternalJobVersion, identity.current_version_id) \
                        if identity.current_version_id else None
                    if current is None:
                        continue
                    already = await self.db.scalar(select(JobSourceObservation.id).where(
                        JobSourceObservation.source_document_id == current.source_document_id,
                        JobSourceObservation.observed_on == snapshot.observed_at.date(),
                    ))
                    if already is None:
                        identity.missing_streak += 1
                        is_closed = identity.missing_streak >= JOB_MISSING_CLOSE_THRESHOLD
                        self.db.add(JobSourceObservation(
                            external_job_identity_id=identity.id,
                            source_snapshot_id=snapshot.id,
                            source_document_id=current.source_document_id,
                            source=source, external_id=identity.external_id,
                            observed_on=snapshot.observed_at.date(),
                            observed_at=snapshot.observed_at,
                            source_event_at=None, source_event_type="observed_at",
                            content_fingerprint=current.content_fingerprint,
                            snapshot_key=snapshot.snapshot_key,
                            status="closed" if is_closed else "missing",
                            event_type="closed" if is_closed else "missing",
                        ))
                        missing_observations += 1
                    if already is None and identity.missing_streak >= JOB_MISSING_CLOSE_THRESHOLD:
                        identity.lifecycle_status = "closed"
                        identity.closed_at = snapshot.observed_at
                        current.is_current = False
                        current.valid_to = snapshot.observed_at
                        closed_jobs += 1
                        standard_job_id = await self.db.scalar(
                            select(RawJobRecord.standard_job_id).where(
                                RawJobRecord.source_document_id == current.source_document_id
                            )
                        )
                        if standard_job_id is not None:
                            affected_standard_job_ids.add(int(standard_job_id))
            snapshot.status = "completed"
            snapshot.completed_at = utc_now()
        await self.db.flush()
        return {
            "missing_observations": missing_observations,
            "closed_jobs": closed_jobs,
            "affected_standard_job_ids": sorted(affected_standard_job_ids),
        }

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
        is_official_portal = "官方" in source or "招聘门户" in source
        trust = (
            0.95
            if is_official_portal or "讯飞" in source or "ifly" in lowered
            else 0.85
            if "智联" in source or "zhaopin" in lowered
            else 0.7
        )
        row = SourceTrustPolicy(
            source=source,
            trust_score=trust,
            # 当前公开官网列表本身证明岗位在抓取时仍在架；允许使用最多
            # 两年的真实首发历史作为基线种子，观察表继续记录后续在架性。
            freshness_window_days=730 if is_official_portal else 90,
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
        if raw.title != standard.name:
            aliases.add(raw.title)
        standard.aliases = sorted(aliases)
        standard.name = normalized.name
        standard.level = normalized.level
        standard.role_family = normalized.role_family
        standard.specialization_key = normalized.specialization_key
        standard.occupation_code = normalized.occupation_code
        standard.normalization_version = normalized.version
        standard.status = "active"
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
        elif link.standard_job_id != standard.id:
            link.standard_job_id = standard.id
            link.original_title = raw.title
            link.confidence = normalized.confidence
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
                current_external_job_condition(),
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
                .join(SourceDocument, RawJobRecord.source_document_id == SourceDocument.id)
                .join(Skill, Skill.id == JobSkillFact.skill_id)
                .where(
                    JobSkillFact.raw_job_record_id.is_not(None),
                    current_external_job_condition(),
                )
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
