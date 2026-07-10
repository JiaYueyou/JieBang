"""Tests for the idempotent local data initializer."""

from sqlalchemy import func, select

from app.core.database import async_session
from app.domain.skill_dictionary import SKILL_DICT
from app.models import Skill
from scripts.init_data import seed_initial_admin, seed_reference_skills


async def test_reference_skill_seed_is_idempotent():
    async with async_session() as db:
        first = await seed_reference_skills(db)
        second = await seed_reference_skills(db)
        count = await db.scalar(select(func.count(Skill.id)))

    assert first["created"] == len(SKILL_DICT)
    assert first["updated"] == 0
    assert second == {
        "created": 0,
        "updated": 0,
        "unchanged": len(SKILL_DICT),
    }
    assert count == len(SKILL_DICT)


async def test_admin_seed_does_not_reset_existing_account():
    async with async_session() as db:
        result = await seed_initial_admin(db)

    assert result == {"status": "existing", "username": "admin", "role": "admin"}
