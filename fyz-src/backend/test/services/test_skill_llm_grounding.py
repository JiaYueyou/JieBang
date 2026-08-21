"""Anti-hallucination checks for LLM-enriched JD skills."""

from app.services.skill_service import SkillService


def test_llm_skill_evidence_must_be_an_exact_source_span():
    assert SkillService._llm_evidence_is_grounded(
        "负责 FastAPI 服务开发",
        jd_text="负责 FastAPI 服务开发，并维护 MySQL 数据库。",
        responsibilities="",
        requirements="",
    )


def test_llm_skill_evidence_rejects_unsupported_claim():
    assert not SkillService._llm_evidence_is_grounded(
        "精通量子芯片流片",
        jd_text="负责 Vue 页面开发与前端性能优化。",
        responsibilities="",
        requirements="",
    )
