import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ResourceNotFoundError
from app.services.learning_service import LearningService


@pytest.mark.asyncio
async def test_generate_path_fallback_and_resources(db_session):
    service = LearningService(db_session)
    service.llm.chat = AsyncMock(return_value={"content": json.dumps({"result": "invalid"})})

    path = await service.generate_path("Backend Engineer", ["Python", "FastAPI"])
    assert path["position_name"] == "Backend Engineer"
    assert len(path["steps"]) == 3
    assert all(step["id"].startswith("step-") for step in path["steps"])
    assert all(resource["id"].startswith("res-") for step in path["steps"] for resource in step["resources"])

    no_gap = await service.generate_path("Backend Engineer", [])
    assert len(no_gap["steps"]) == 1

    resources = await service.recommend_resources(["Python", "Docker"])
    assert set(resources["skills"]) == {"Python", "Docker"}
    assert len(resources["skills"]["Python"]) == 2


@pytest.mark.asyncio
async def test_generate_path_uses_valid_llm_plan(db_session):
    service = LearningService(db_session)
    service.llm.chat = AsyncMock(return_value={"content": json.dumps({
        "name": "Custom Path",
        "steps": [{"title": "Step", "duration": "invalid", "resources": [{}]}],
    })})
    result = await service.generate_path("Engineer", ["Python"])
    assert result["name"] == "Custom Path"
    assert result["total_duration"]
    assert result["steps"][0]["resources"][0]["id"].startswith("res-")


@pytest.mark.asyncio
async def test_quiz_success_empty_and_missing_path(db_session):
    service = LearningService(db_session)
    path = SimpleNamespace(steps=[
        {"id": "s1", "title": "Python", "completed": True},
        {"id": "s2", "title": "FastAPI", "completed": False},
    ])
    service.repo.get_by_id = AsyncMock(return_value=path)
    service.llm.chat = AsyncMock(return_value={"content": json.dumps({
        "questions": [{"type": "choice", "question": "Q", "options": []}]
    })})
    quiz = await service.generate_quiz(1, [], 1)
    assert quiz["questions"][0]["id"].startswith("q-")

    service.llm.chat = AsyncMock(side_effect=RuntimeError("offline"))
    assert await service.generate_quiz(1, ["s2"], 1) == {"questions": []}

    service.repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ResourceNotFoundError):
        await service.generate_quiz(999, [], 1)


@pytest.mark.asyncio
async def test_chat_success_and_fallback(db_session, monkeypatch):
    service = LearningService(db_session)
    service.llm.chat = AsyncMock(return_value={"content": "Answer"})

    # _extract_related_concepts 已改为 async，测试桩需要用协程函数
    async def fake_extract(message):
        return [{"name": "Python"}]

    monkeypatch.setattr(service, "_extract_related_concepts", fake_extract)
    result = await service.chat("question", None, [{"role": "user", "content": "before"}])
    assert result["reply"] == "Answer"
    assert result["related_concepts"] == [{"name": "Python"}]

    service.llm.chat = AsyncMock(side_effect=RuntimeError("offline"))
    fallback = await service.chat("question", None, [])
    assert fallback["reply"]

