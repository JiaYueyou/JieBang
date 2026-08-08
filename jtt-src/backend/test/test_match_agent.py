"""
[Agent 3] 智能匹配 —— 技能语义匹配 + 经验相关性评估 测试。
测试模式下 LLM 为 MockProvider，应降级到规则匹配/计数评分。
"""
import pytest
import pytest_asyncio
from app.core.database import async_session
from app.services.match_service import MatchService, _skill_names_match


@pytest.mark.asyncio
async def test_skill_names_match_rules():
    """规则模糊匹配：等价词元 / 中文包含"""
    assert _skill_names_match("LangChain", "LangChain / LangGraph")
    assert _skill_names_match("RAG", "RAG 检索增强生成")
    assert _skill_names_match("微服务", "微服务架构")
    assert not _skill_names_match("Java", "Python")


@pytest.mark.asyncio
async def test_semantic_skill_match_fallback():
    """Mock LLM 返回无效结果 → 降级到规则匹配"""
    async with async_session() as session:
        service = MatchService(session)
        resume_skills = ["Python", "Pandas", "NumPy"]
        position_skills = ["Python", "数据分析", "Spring"]
        matched = await service._semantic_skill_match(resume_skills, position_skills)
        # 规则匹配："Python" 匹配 "Python"；"Pandas" ↔ "数据分析" 无词元交集
        assert "Python" in matched
        assert "Spring" not in matched


@pytest.mark.asyncio
async def test_experience_relevance_no_exp():
    """无工作经历 → 返回 0"""
    async with async_session() as session:
        service = MatchService(session)
        score = await service._assess_experience_relevance([], "Java后端", ["Java"])
        assert score == 0


@pytest.mark.asyncio
async def test_experience_relevance_fallback():
    """Mock LLM 返回无效结果 → 降级到基于经历数量的评分"""
    async with async_session() as session:
        service = MatchService(session)
        exps = [
            {"company": "A", "position": "后端开发", "description": "负责系统开发"},
            {"company": "B", "position": "架构师", "description": "系统设计"},
        ]
        score = await service._assess_experience_relevance(exps, "Java后端", ["Java"])
        # 降级：2 段经历 → 40 + 2*20 = 80
        assert score == 80
