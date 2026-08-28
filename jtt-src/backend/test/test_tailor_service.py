from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ResourceNotFoundError
from app.services.tailor_service import PositionContext, TailorService


def context():
    return PositionContext(
        id="raw:1", name="Backend Engineer", summary="Build APIs",
        responsibilities=["API development"], required_skills=["Python", "FastAPI"],
        preferred_skills=["Docker"], source="raw_job_record",
    )


@pytest.mark.asyncio
async def test_position_context_routing_and_raw_loading(db_session):
    service = TailorService(db_session)
    service.raw_job_repo.get_by_id = AsyncMock(return_value={
        "standardized_title": "Backend Engineer", "requirements": "Python FastAPI",
        "jd_text": "Docker", "keywords": "Python",
    })
    raw = await service._load_position_context("raw:1")
    assert raw.source == "raw_job_record"
    assert "Python" in raw.required_skills

    service.raw_job_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ResourceNotFoundError):
        await service._load_from_raw_record("raw:999")
    with pytest.raises(ResourceNotFoundError):
        await service._load_position_context("invalid")


@pytest.mark.asyncio
async def test_mysql_context_and_missing(db_session):
    service = TailorService(db_session)
    position = SimpleNamespace(name="Backend", summary="Summary", responsibilities=["Build"])
    service.position_repo.get_by_id = AsyncMock(return_value=position)
    service.position_repo.get_skills_for_positions = AsyncMock(return_value={1: [
        {"name": "Python", "kind": "required"}, {"name": "Docker", "kind": "preferred"},
    ]})
    result = await service._load_position_context("position:1")
    assert result.required_skills == ["Python"]
    assert result.preferred_skills == ["Docker"]

    service.position_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ResourceNotFoundError):
        await service._load_position_context("1")


def test_fallback_suggestions_cover_missing_and_matched_skills(db_session):
    service = TailorService(db_session)
    resume = SimpleNamespace(
        skill_list=[{"name": "Python"}], self_evaluation="Good",
    )
    suggestions = service._fallback_suggestions(resume, context(), [
        {"name": "Python", "kind": "required"},
        {"name": "FastAPI", "kind": "required"},
        {"name": "Docker", "kind": "preferred"},
    ])
    assert len(suggestions) == 3
    assert {item["section"] for item in suggestions} == {"skills", "selfEvaluation"}


@pytest.mark.asyncio
async def test_optimize_phrase_success_and_fallback(db_session):
    service = TailorService(db_session)
    service.llm.chat = AsyncMock(return_value={"content": '{"suggestions":["Improved"]}'})
    assert await service.optimize_phrase("Original", "professional") == ["Improved"]
    service.llm.chat = AsyncMock(side_effect=RuntimeError("offline"))
    assert await service.optimize_phrase("Original", "unknown") == ["Original"]
