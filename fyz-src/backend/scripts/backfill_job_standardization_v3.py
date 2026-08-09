"""Preview or apply V3 company/business-suffix-safe job aggregation.

The script reassigns raw-job mappings to V3 canonical identities.  It never
deletes a standard job: obsolete identities are archived once they have no
source mappings, preserving audit, favorites and historical references.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select

from app.core.database import async_session, engine
from app.domain.job_standardizer import normalize_job_title
from app.models import RawJobRecord, StandardJob, StandardJobAlias, StandardJobSource


def apply_normalized_fields(raw: RawJobRecord, normalized) -> None:
    raw.standardized_title = normalized.name
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


async def run(*, apply: bool) -> dict[str, int]:
    summary: Counter[str] = Counter()
    try:
        async with async_session() as db:
            standards = list((await db.execute(
                select(StandardJob).order_by(StandardJob.source_count.desc(), StandardJob.id)
            )).scalars())
            by_key: dict[str, StandardJob] = {}
            for standard in standards:
                # Reuse an already-created canonical key even if its display
                # name was previously polluted by an older title variant.
                by_key.setdefault(standard.canonical_key, standard)
                normalized = normalize_job_title(standard.name)
                by_key.setdefault(normalized.canonical_key, standard)

            links = {
                row.source_id: row
                for row in (await db.execute(
                    select(StandardJobSource).where(StandardJobSource.source_type == "raw")
                )).scalars()
            }
            alias_keys = {
                (row.standard_job_id, row.alias_key)
                for row in (await db.execute(select(StandardJobAlias))).scalars()
            }
            raws = list((await db.execute(select(RawJobRecord).order_by(RawJobRecord.id))).scalars())

            for raw in raws:
                normalized = normalize_job_title(
                    raw.title, city=raw.city, company=raw.company, jd_text=raw.jd_text
                )
                target = by_key.get(normalized.canonical_key)
                if target is None:
                    summary["created_standard_jobs"] += 1
                    if apply:
                        target = StandardJob(
                            name=normalized.name,
                            canonical_key=normalized.canonical_key,
                            aliases=[],
                            stack={
                                "algorithm": "ai", "data": "data", "devops": "devops",
                                "operations": "business", "sales": "business", "product": "product",
                            }.get(normalized.role_family, "backend"),
                            level=normalized.level,
                            role_family=normalized.role_family,
                            specialization_key=normalized.specialization_key,
                            occupation_code=normalized.occupation_code,
                            normalization_version=normalized.version,
                            description=f"由多来源岗位数据聚合形成的{normalized.name}能力模型。",
                            source_count=0,
                            status="active",
                        )
                        db.add(target)
                        await db.flush()
                        by_key[normalized.canonical_key] = target
                if target is None:
                    continue

                link = links.get(raw.id)
                if raw.standard_job_id != target.id:
                    summary["remapped_raw_jobs"] += 1
                if normalized.name != (raw.standardized_title or raw.title):
                    summary["renamed_standardized_titles"] += 1
                if not apply:
                    continue

                # 旧标准岗位可能已经占用了另一个 V2 canonical key。原始岗位
                # 映射以 V3 key 选择 target 即可；不改写历史唯一键，避免把
                # 两个遗留 identity 同时改成同一 key 而破坏审计关联。
                target.name = normalized.name
                target.level = normalized.level
                target.role_family = normalized.role_family
                target.specialization_key = normalized.specialization_key
                target.occupation_code = normalized.occupation_code
                target.normalization_version = normalized.version
                target.status = "active"
                aliases = set(target.aliases or [])
                if raw.title != target.name:
                    aliases.add(raw.title)
                target.aliases = sorted(aliases)
                apply_normalized_fields(raw, normalized)
                raw.standard_job_id = target.id
                alias_key = "".join(ch for ch in raw.title.casefold() if ch.isalnum())
                if (target.id, alias_key) not in alias_keys:
                    db.add(StandardJobAlias(
                        standard_job_id=target.id,
                        alias=raw.title,
                        alias_key=alias_key,
                        source_type="raw",
                        confidence=normalized.confidence,
                        normalization_version=normalized.version,
                    ))
                    alias_keys.add((target.id, alias_key))
                if link is None:
                    link = StandardJobSource(
                        standard_job_id=target.id,
                        source_type="raw",
                        source_id=raw.id,
                        original_title=raw.title,
                        confidence=normalized.confidence,
                    )
                    db.add(link)
                    links[raw.id] = link
                else:
                    link.standard_job_id = target.id
                    link.original_title = raw.title
                    link.confidence = normalized.confidence

            if apply:
                await db.flush()
                source_counts = dict((await db.execute(
                    select(StandardJobSource.standard_job_id, func.count(StandardJobSource.id))
                    .group_by(StandardJobSource.standard_job_id)
                )).all())
                for standard in standards + [
                    item for item in by_key.values() if item not in standards
                ]:
                    count = int(source_counts.get(standard.id, 0))
                    standard.source_count = count
                    if count == 0:
                        standard.status = "archived"
                        summary["archived_standard_jobs"] += 1
                await db.commit()
            summary["raw_jobs"] = len(raws)
            summary["target_standard_jobs"] = len(by_key)
    finally:
        await engine.dispose()
    return dict(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill V3 job standardization")
    parser.add_argument("--apply", action="store_true", help="Persist remapped identities")
    args = parser.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] {asyncio.run(run(apply=args.apply))}")


if __name__ == "__main__":
    main()
