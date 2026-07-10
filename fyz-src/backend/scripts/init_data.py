"""Initialize shared development data after applying Alembic migrations.

This command is intentionally idempotent: reference skills are upserted by
``canonical_key`` and crawled JD records are deduplicated by their content
fingerprint. MySQL remains the source of truth; Neo4j synchronization is an
explicit opt-in step.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import (  # noqa: E402
    INITIAL_ADMIN_ENABLED,
    INITIAL_ADMIN_PASSWORD,
    INITIAL_ADMIN_USERNAME,
)
from app.core.database import async_session  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.domain.skill_dictionary import (  # noqa: E402
    SKILL_ALIASES,
    SKILL_DICT,
    canonical_key,
)
from app.models import Skill, User  # noqa: E402
from app.services.graph_service import GraphService  # noqa: E402
from app.services.import_service import ALLOWED_FILES, ImportService  # noqa: E402
from app.services.skill_service import SkillService  # noqa: E402

DEFAULT_FILES = (
    "jd_crawl_ifly.json",
    "jd_crawl_zl.json",
    "jd_crawl2.json",
)


class RuleOnlyProvider:
    """Disable model calls so every developer receives the same baseline."""

    provider_name = "disabled"
    model_name = "rule-only"
    enabled = False

    async def generate_structured(self, **_kwargs):  # pragma: no cover
        raise RuntimeError("RuleOnlyProvider does not call an external model")


def code_migration_heads() -> set[str]:
    """Return the migration heads declared by the checked-out source tree."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    return set(script.get_heads())


async def require_database_at_head(db: AsyncSession) -> list[str]:
    """Fail before seeding when the target database is not at Alembic head."""
    expected = code_migration_heads()
    try:
        rows = await db.execute(text("SELECT version_num FROM alembic_version"))
        current = {str(row[0]) for row in rows.all()}
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Alembic version table is unavailable; run 'alembic upgrade head' first."
        ) from exc

    if current != expected:
        raise RuntimeError(
            "Database migration mismatch: "
            f"current={sorted(current) or ['<base>']}, expected={sorted(expected)}. "
            "Run 'alembic upgrade head' before importing initial data."
        )
    return sorted(current)


async def seed_reference_skills(db: AsyncSession) -> dict[str, int]:
    """Upsert the shared skill dictionary without deleting observed aliases."""
    aliases_by_name: dict[str, set[str]] = defaultdict(set)
    for alias, canonical_name in SKILL_ALIASES.items():
        aliases_by_name[canonical_name].add(alias)

    existing_rows = list((await db.execute(select(Skill))).scalars())
    existing_by_key = {row.canonical_key: row for row in existing_rows}
    created = updated = unchanged = 0

    for name, category in sorted(SKILL_DICT.items(), key=lambda item: canonical_key(item[0])):
        key = canonical_key(name)
        seed_aliases = aliases_by_name.get(name, set())
        row = existing_by_key.get(key)
        if row is None:
            db.add(
                Skill(
                    name=name,
                    canonical_name=name,
                    canonical_key=key,
                    category=category,
                    aliases=sorted(seed_aliases),
                )
            )
            created += 1
            continue

        merged_aliases = sorted(set(row.aliases or []) | seed_aliases)
        changed = any(
            (
                row.name != name,
                row.canonical_name != name,
                row.category != category,
                list(row.aliases or []) != merged_aliases,
            )
        )
        if changed:
            row.name = name
            row.canonical_name = name
            row.category = category
            row.aliases = merged_aliases
            updated += 1
        else:
            unchanged += 1

    await db.commit()
    return {"created": created, "updated": updated, "unchanged": unchanged}


async def seed_initial_admin(db: AsyncSession) -> dict[str, str]:
    """Create the configured local administrator without resetting passwords."""
    if not INITIAL_ADMIN_ENABLED:
        return {"status": "disabled"}
    if not INITIAL_ADMIN_PASSWORD:
        raise RuntimeError(
            "INITIAL_ADMIN_PASSWORD is required when INITIAL_ADMIN_ENABLED=true."
        )

    result = await db.execute(
        select(User).where(User.username == INITIAL_ADMIN_USERNAME)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {
            "status": "existing",
            "username": existing.username,
            "role": existing.role,
        }

    user = User(
        username=INITIAL_ADMIN_USERNAME,
        password_hash=hash_password(INITIAL_ADMIN_PASSWORD),
        role="admin",
    )
    db.add(user)
    await db.commit()
    return {"status": "created", "username": user.username, "role": user.role}


async def initialize(args: argparse.Namespace) -> dict:
    async with async_session() as db:
        result: dict[str, object] = {
            "migration_heads": await require_database_at_head(db),
            "admin": {"status": "skipped"},
            "skills": await seed_reference_skills(db),
            "jobs": {"status": "skipped"},
            "standard_jobs": {"status": "skipped"},
            "neo4j": {"status": "skipped"},
        }

        if not args.skip_admin:
            result["admin"] = await seed_initial_admin(db)

        if not args.skip_jobs:
            skill_service = None
            if not args.use_deepseek:
                skill_service = SkillService(db, llm_provider=RuleOnlyProvider())
            result["jobs"] = await ImportService(
                db, skill_service=skill_service
            ).import_files(args.files)

        graph_service = GraphService(db)
        if not args.skip_standard_jobs:
            count = await graph_service.aggregate_standard_jobs()
            await db.commit()
            result["standard_jobs"] = {"status": "ready", "count": count}

        if args.sync_neo4j:
            result["neo4j"] = {
                "status": "succeeded",
                **await graph_service.sync(
                    mode="full",
                    enrich_top_skills=args.enrich_top_skills,
                    user_id=None,
                ),
            }

        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import idempotent shared development data into MySQL."
    )
    parser.add_argument(
        "--files",
        nargs="+",
        choices=sorted(ALLOWED_FILES),
        default=list(DEFAULT_FILES),
        help="Whitelisted JD files under DATA_DIR (defaults to all three).",
    )
    parser.add_argument("--skip-admin", action="store_true")
    parser.add_argument("--skip-jobs", action="store_true")
    parser.add_argument("--skip-standard-jobs", action="store_true")
    parser.add_argument(
        "--use-deepseek",
        action="store_true",
        help="Allow model-assisted skill extraction (off for reproducible defaults).",
    )
    parser.add_argument(
        "--sync-neo4j",
        action="store_true",
        help="Rebuild namespace=jiebang in Neo4j after MySQL initialization.",
    )
    parser.add_argument(
        "--enrich-top-skills",
        action="store_true",
        help="Enable DeepSeek L4/L5 candidate generation during Neo4j sync.",
    )
    args = parser.parse_args()
    if args.use_deepseek and args.skip_jobs:
        parser.error("--use-deepseek cannot be combined with --skip-jobs")
    if args.enrich_top_skills and not args.sync_neo4j:
        parser.error("--enrich-top-skills requires --sync-neo4j")
    return args


def main() -> int:
    try:
        result = asyncio.run(initialize(parse_args()))
    except Exception as exc:
        print(f"Initialization failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
