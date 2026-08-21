"""学习服务的规则降级与辅助逻辑测试。"""

from app.core.database import async_session
from app.core.exceptions import ResourceNotFoundError
from app.services.learning_service import LearningService
import pytest


class FailingLLM:
    async def chat(self, *args, **kwargs):
        raise RuntimeError("LLM unavailable in tests")


async def test_generate_path_falls_back_without_llm():
    async with async_session() as session:
        service = LearningService(session)
        service.llm = FailingLLM()
        result = await service.generate_path(
            "Python 后端工程师", ["FastAPI", "Redis"], ["Python"]
        )
        assert result["name"] == "Python 后端工程师学习路径"
        assert len(result["steps"]) == 3
        assert result["steps"][0]["order"] == 1
        assert result["steps"][0]["resources"][0]["id"].startswith("res-")
        assert result["total_duration"] == "6周"


async def test_generate_path_for_already_qualified_user():
    async with async_session() as session:
        service = LearningService(session)
        service.llm = FailingLLM()
        result = await service.generate_path("数据工程师", [])
        assert len(result["steps"]) == 1
        assert "巩固" in result["steps"][0]["title"]


async def test_chat_resources_and_followups_fallback():
    async with async_session() as session:
        service = LearningService(session)
        service.llm = FailingLLM()
        chat = await service.chat("如何学习 Python", None, [])
        assert "暂时不可用" in chat["reply"]
        assert "需要哪些前置知识？" in chat["follow_up_questions"]

        resources = await service.recommend_resources(["FastAPI"])
        assert len(resources["skills"]["FastAPI"]) == 2
        assert service._generate_follow_ups("请解释 RAG")[0].startswith("这个技术")
        assert service._generate_follow_ups("你好") == ["能详细说说吗？", "有什么实际应用场景？"]


async def test_generate_quiz_handles_llm_failure():
    async with async_session() as session:
        service = LearningService(session)
        path = await service.create_path(1, {
            "name": "测试路线", "position_name": "测试岗位",
            "steps": [{
                "id": "s1", "order": 1, "title": "Python 基础",
                "description": "", "duration": "1周", "resources": [],
                "completed": True,
            }],
        })
        service.llm = FailingLLM()
        result = await service.generate_quiz(path["id"], [], 5)
        assert result == {"questions": []}


async def test_missing_learning_path_errors():
    async with async_session() as session:
        service = LearningService(session)
        with pytest.raises(ResourceNotFoundError):
            await service.get_path(999)
        with pytest.raises(ResourceNotFoundError):
            await service.update_path(999, {"name": "不存在"})
        with pytest.raises(ResourceNotFoundError):
            await service.delete_path(999)
