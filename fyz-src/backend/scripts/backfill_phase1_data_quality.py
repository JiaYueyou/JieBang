"""Backfill Phase 1 quality fields and standard-job scoped verification."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import async_session, engine
from app.core.time import utc_now
from app.domain.data_quality import evaluate_job_quality
from app.models import (
    GraphSnapshot,
    GraphSyncBatch,
    JobSkillFact,
    RawJobRecord,
    SourceDocument,
)
from app.services.import_service import ImportService


async def backfill(*, apply: bool) -> dict:
    async with async_session() as session:
        service = ImportService(session)
        rows = (
            await session.execute(
                select(RawJobRecord, SourceDocument)
                .join(
                    SourceDocument,
                    SourceDocument.id == RawJobRecord.source_document_id,
                )
                .order_by(RawJobRecord.id)
            )
        ).all()
        status_counts: Counter[str] = Counter()
        flag_counts: Counter[str] = Counter()
        near_duplicates = 0
        for raw, source in rows:
            policy = await service._quality_policy(source.source)
            evaluation = evaluate_job_quality(
                {
                    "title": raw.title,
                    "company": raw.company,
                    "source": source.source,
                    "url": source.url,
                    "jd_text": raw.jd_text,
                    "responsibilities": raw.responsibilities,
                    "requirements": raw.requirements,
                    "posted_at": raw.posted_at_text,
                    "crawled_at": raw.crawled_at_text,
                },
                policy=policy,
                evaluated_at=utc_now(),
            )
            raw.posted_at = evaluation.posted_at
            raw.crawled_at = evaluation.crawled_at
            raw.quality_score = evaluation.quality_score
            raw.freshness_score = evaluation.freshness_score
            raw.source_trust_score = evaluation.source_trust_score
            raw.quality_status = evaluation.quality_status
            raw.quality_flags = list(evaluation.quality_flags)
            raw.content_simhash = evaluation.content_simhash
            raw.quality_policy_version = evaluation.policy_version
            raw.quality_evaluated_at = evaluation.evaluated_at
            await service._ensure_standard_job(raw)
            if await service._mark_near_duplicate(
                raw,
                fingerprint=source.content_fingerprint,
                threshold=policy.near_duplicate_threshold,
            ):
                near_duplicates += 1
            status_counts[raw.quality_status] += 1
            flag_counts.update(raw.quality_flags or [])

        await service._cross_validate_facts([])
        repaired_graph_timestamps = 0
        snapshots = list(
            (await session.execute(select(GraphSnapshot))).scalars()
        )
        for snapshot in snapshots:
            if (
                snapshot.completed_at
                and snapshot.created_at > snapshot.completed_at
                and snapshot.created_at - snapshot.completed_at
                <= timedelta(hours=12)
            ):
                snapshot.created_at -= timedelta(hours=8)
                repaired_graph_timestamps += 1
        batches = list(
            (await session.execute(select(GraphSyncBatch))).scalars()
        )
        for batch in batches:
            reference = batch.started_at or batch.finished_at
            if (
                reference
                and batch.created_at > reference
                and batch.created_at - reference <= timedelta(hours=12)
            ):
                batch.created_at -= timedelta(hours=8)
                repaired_graph_timestamps += 1
        verified_facts = int(
            await session.scalar(
                select(func.count(JobSkillFact.id)).where(
                    JobSkillFact.raw_job_record_id.is_not(None),
                    JobSkillFact.verification_status == "verified",
                )
            )
            or 0
        )
        unverified_facts = int(
            await session.scalar(
                select(func.count(JobSkillFact.id)).where(
                    JobSkillFact.raw_job_record_id.is_not(None),
                    JobSkillFact.verification_status == "unverified",
                )
            )
            or 0
        )
        report = {
            "mode": "apply" if apply else "dry-run",
            "records": len(rows),
            "quality_status_counts": dict(status_counts),
            "quality_flag_counts": dict(flag_counts),
            "near_duplicate_matches": near_duplicates,
            "verified_skill_facts": verified_facts,
            "unverified_skill_facts": unverified_facts,
            "repaired_graph_timestamps": repaired_graph_timestamps,
        }
        if apply:
            await session.commit()
        else:
            await session.rollback()
        return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes. Without this flag the transaction is rolled back.",
    )
    args = parser.parse_args()
    async def run() -> dict:
        try:
            return await backfill(apply=args.apply)
        finally:
            await engine.dispose()

    report = asyncio.run(run())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
