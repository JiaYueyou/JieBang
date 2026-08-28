"""merge Java engineer aliases and repair standard-job projections

Revision ID: 20260820_0025
Revises: 20260820_0024
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "20260820_0025"
down_revision = "20260820_0024"
branch_labels = None
depends_on = None


def _aliases(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str) and value:
        return [str(item) for item in json.loads(value) if item]
    return []


def upgrade() -> None:
    bind = op.get_bind()
    jobs = sa.table(
        "standard_job",
        sa.column("id", sa.Integer), sa.column("name", sa.String),
        sa.column("canonical_key", sa.String), sa.column("aliases", sa.JSON),
        sa.column("level", sa.String), sa.column("source_count", sa.Integer),
        sa.column("status", sa.String), sa.column("stack", sa.String),
        sa.column("role_family", sa.String), sa.column("specialization_key", sa.String),
        sa.column("occupation_code", sa.String), sa.column("first_seen_at", sa.DateTime),
        sa.column("last_seen_at", sa.DateTime), sa.column("normalization_version", sa.String),
    )
    rows = bind.execute(sa.select(jobs).where(jobs.c.canonical_key.in_([
        "java工程师:junior", "java工程师:middle", "java工程师:senior",
        "java开发工程师:junior", "java开发工程师:middle", "java开发工程师:senior",
        "java工程师", "java开发工程师",
    ]))).mappings().all()
    by_key = {str(row["canonical_key"]): row for row in rows}

    for level in ("junior", "middle", "senior"):
        target = by_key.get(f"java开发工程师:{level}")
        duplicate = by_key.get(f"java工程师:{level}")
        if target is None and duplicate is not None:
            bind.execute(jobs.update().where(jobs.c.id == duplicate["id"]).values(
                name="Java开发工程师", canonical_key=f"java开发工程师:{level}",
                normalization_version="job-title-v5",
            ))
            target, duplicate = duplicate, None
        if target is None:
            continue

        merged_aliases = list(dict.fromkeys([
            *_aliases(target["aliases"]),
            *(_aliases(duplicate["aliases"]) if duplicate else []),
            "Java工程师",
        ]))
        first_seen, last_seen = target["first_seen_at"], target["last_seen_at"]

        if duplicate is not None:
            target_id, duplicate_id = int(target["id"]), int(duplicate["id"])
            first_seen = min(filter(None, (first_seen, duplicate["first_seen_at"])), default=None)
            last_seen = max(filter(None, (last_seen, duplicate["last_seen_at"])), default=None)
            conflicts = int(bind.execute(sa.text("""
                SELECT COUNT(*) FROM analysis_insight_decision source_decision
                JOIN analysis_insight_decision target_decision
                  ON target_decision.insight_type=source_decision.insight_type
                 AND target_decision.created_by=source_decision.created_by
                 AND target_decision.target_id=:target_id
                WHERE source_decision.target_id=:duplicate_id
                  AND source_decision.insight_type='emerging_job'
            """), {"target_id": target_id, "duplicate_id": duplicate_id}).scalar_one())
            if conflicts:
                raise RuntimeError(
                    f"Cannot merge StandardJob {duplicate_id} into {target_id}: "
                    "conflicting emerging-job review decisions exist."
                )
            bind.execute(sa.text("""
                UPDATE analysis_insight_decision SET target_id=:target_id
                WHERE target_id=:duplicate_id AND insight_type='emerging_job'
            """), {"target_id": target_id, "duplicate_id": duplicate_id})
            bind.execute(sa.text("""
                UPDATE raw_job_record
                   SET standard_job_id=:target_id,
                       standardized_title='Java开发工程师',
                       normalization_version='job-title-v5',
                       normalized_data=JSON_SET(
                           COALESCE(normalized_data, JSON_OBJECT()),
                           '$.job_title.version', 'job-title-v5',
                           '$.job_title.level', :level
                       )
                 WHERE standard_job_id=:duplicate_id
            """), {"target_id": target_id, "duplicate_id": duplicate_id, "level": level})
            bind.execute(jobs.update().where(jobs.c.id == duplicate_id).values(
                status="archived", source_count=0
            ))

        bind.execute(jobs.update().where(jobs.c.id == target["id"]).values(
            name="Java开发工程师", aliases=merged_aliases, status="active",
            stack="backend", role_family="backend", specialization_key="java",
            occupation_code=f"backend:java:{level}", first_seen_at=first_seen,
            last_seen_at=last_seen, normalization_version="job-title-v5",
        ))
        bind.execute(sa.text("""
            INSERT INTO standard_job_alias
                (standard_job_id, alias, alias_key, source_type, confidence,
                 normalization_version, created_at)
            SELECT :target_id, 'Java工程师', 'java工程师', 'canonical_merge', 1.0,
                   'job-title-v5', CURRENT_TIMESTAMP
            WHERE NOT EXISTS (
                SELECT 1 FROM standard_job_alias
                WHERE standard_job_id=:target_id AND alias_key='java工程师'
            )
        """), {"target_id": int(target["id"])})

    # Route any legacy no-level identity before archiving it. Historical data
    # normally has no direct raw reference here, but upgrades must remain safe
    # for databases that do.
    middle_target = by_key.get("java开发工程师:middle")
    if middle_target is not None:
        middle_target_id = int(middle_target["id"])
        for legacy_key in ("java工程师", "java开发工程师"):
            legacy = by_key.get(legacy_key)
            if legacy is None:
                continue
            legacy_id = int(legacy["id"])
            conflicts = int(bind.execute(sa.text("""
                SELECT COUNT(*) FROM analysis_insight_decision source_decision
                JOIN analysis_insight_decision target_decision
                  ON target_decision.insight_type=source_decision.insight_type
                 AND target_decision.created_by=source_decision.created_by
                 AND target_decision.target_id=:target_id
                WHERE source_decision.target_id=:legacy_id
                  AND source_decision.insight_type='emerging_job'
            """), {"target_id": middle_target_id, "legacy_id": legacy_id}).scalar_one())
            if conflicts:
                raise RuntimeError(
                    f"Cannot archive legacy StandardJob {legacy_id}: conflicting decisions exist."
                )
            bind.execute(sa.text("""
                UPDATE analysis_insight_decision SET target_id=:target_id
                WHERE target_id=:legacy_id AND insight_type='emerging_job'
            """), {"target_id": middle_target_id, "legacy_id": legacy_id})
            bind.execute(sa.text("""
                UPDATE raw_job_record
                   SET standard_job_id=:target_id,
                       standardized_title='Java开发工程师',
                       normalization_version='job-title-v5',
                       normalized_data=JSON_SET(
                           COALESCE(normalized_data, JSON_OBJECT()),
                           '$.job_title.version', 'job-title-v5',
                           '$.job_title.level', 'middle'
                       )
                 WHERE standard_job_id=:legacy_id
            """), {"target_id": middle_target_id, "legacy_id": legacy_id})

    # RawJobRecord is authoritative. This also separates old no-level Java
    # projections according to the level already assigned to each raw job.
    bind.execute(sa.text("""
        UPDATE standard_job_source source
        JOIN raw_job_record raw ON source.source_type='raw' AND source.source_id=raw.id
        SET source.standard_job_id=raw.standard_job_id
        WHERE raw.standard_job_id IS NOT NULL
          AND source.standard_job_id<>raw.standard_job_id
    """))
    bind.execute(sa.text("""
        UPDATE evidence_chunk chunk
        JOIN raw_job_record raw ON raw.id=chunk.raw_job_record_id
        SET chunk.standard_job_id=raw.standard_job_id
        WHERE raw.standard_job_id IS NOT NULL
          AND chunk.standard_job_id<>raw.standard_job_id
    """))
    bind.execute(sa.text("""
        UPDATE job_duplicate_cluster cluster
        JOIN raw_job_record raw ON raw.id=cluster.representative_raw_job_id
        SET cluster.standard_job_id=raw.standard_job_id
        WHERE raw.standard_job_id IS NOT NULL
          AND cluster.standard_job_id<>raw.standard_job_id
    """))
    bind.execute(sa.text("""
        UPDATE raw_job_record raw JOIN standard_job job ON job.id=raw.standard_job_id
        SET raw.standardized_title=job.name,
            raw.normalization_version=job.normalization_version,
            raw.normalized_data=JSON_SET(
                COALESCE(raw.normalized_data, JSON_OBJECT()),
                '$.job_title.version', job.normalization_version,
                '$.job_title.level', job.level
            )
        WHERE job.canonical_key LIKE 'java开发工程师:%'
    """))
    bind.execute(sa.text("""
        UPDATE standard_job job SET source_count=(
            SELECT COUNT(*) FROM standard_job_source source
            WHERE source.standard_job_id=job.id
        )
    """))
    bind.execute(sa.text("""
        UPDATE standard_job SET status='archived', source_count=0
        WHERE canonical_key IN ('java工程师', 'java开发工程师')
    """))

    checks = {
        "source/raw": """SELECT COUNT(*) FROM standard_job_source source
            JOIN raw_job_record raw ON source.source_type='raw' AND source.source_id=raw.id
            WHERE raw.standard_job_id IS NOT NULL AND source.standard_job_id<>raw.standard_job_id""",
        "chunk/raw": """SELECT COUNT(*) FROM evidence_chunk chunk
            JOIN raw_job_record raw ON raw.id=chunk.raw_job_record_id
            WHERE raw.standard_job_id IS NOT NULL AND chunk.standard_job_id<>raw.standard_job_id""",
        "cluster/raw": """SELECT COUNT(*) FROM job_duplicate_cluster cluster
            JOIN raw_job_record raw ON raw.id=cluster.representative_raw_job_id
            WHERE raw.standard_job_id IS NOT NULL AND cluster.standard_job_id<>raw.standard_job_id""",
        "raw/legacy-java": """SELECT COUNT(*) FROM raw_job_record raw
            JOIN standard_job job ON job.id=raw.standard_job_id
            WHERE job.canonical_key IN ('java工程师', 'java开发工程师',
                                        'java工程师:junior', 'java工程师:middle',
                                        'java工程师:senior')""",
    }
    failed = {
        name: count for name, sql in checks.items()
        if (count := int(bind.execute(sa.text(sql)).scalar_one()))
    }
    if failed:
        raise RuntimeError(f"Standard-job projection repair failed: {failed}")


def downgrade() -> None:
    # Archived identities and aliases remain auditable, but fact ownership
    # cannot be losslessly split after a canonical merge.
    pass
