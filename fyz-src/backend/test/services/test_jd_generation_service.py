from app.models import AgentRun
from app.core.database import async_session
from app.providers import MockLLMProvider
from app.schemas.agent import (
    GenerateJDRequest,
    JDInputSuggestionRequest,
    LLMGeneratedJDDraft,
    LLMJDInputSuggestion,
)
from app.services.jd_generation_service import JDGenerationService


def request_payload(**overrides):
    payload = {
        "mode": "requirements",
        "title": "高级 Java 开发工程师",
        "level": "senior",
        "department": "研发中心",
        "skills_input": "Java, Spring Boot, MySQL",
    }
    payload.update(overrides)
    return GenerateJDRequest.model_validate(payload)


async def add_run(db, run_id="run-1"):
    db.add(AgentRun(
        id=run_id,
        agent_type="jd_generation",
        provider="mock",
        model="mock-structured",
        prompt_version="jd-generation-v1",
        input_summary="test",
        status="queued",
        retry_count=0,
    ))
    await db.commit()
    return run_id


async def test_generation_preserves_user_owned_fields_and_audits_run():
    output = LLMGeneratedJDDraft(
        title="模型错误标题",
        standardized_title="Java 开发工程师",
        responsibilities=["负责服务开发"],
        requirements=["熟悉 Java"],
        skills=["Java"],
        bonus_skills=["Redis"],
        jd_text="一份 JD 草稿",
        assumptions=[],
        warnings=[],
    )
    async with async_session() as db:
        run_id = await add_run(db)
        service = JDGenerationService(db, llm_provider=MockLLMProvider(output=output))

        draft = await service.generate(request_payload(), agent_run_id=run_id)
        await db.commit()

        assert draft.title == "高级 Java 开发工程师"
        assert draft.level == "senior"
        assert draft.department == "研发中心"
        assert draft.generation_mode == "llm"
        run = await service.get_run(run_id)
        assert run.status == "succeeded"
        assert run.structured_output["title"] == "高级 Java 开发工程师"
        assert run.duration_ms is not None


async def test_generation_normalizes_the_previously_failed_position_name_shape():
    output = LLMGeneratedJDDraft.model_validate({
        "position_name": "高级 Java 开发工程师",
        "responsibilities": {"skills": ["Java", "Spring Boot"]},
        "requirements": {"skills": ["Java", "MySQL"]},
        "skills": ["Java", "Spring Boot", "MySQL"],
        "assumptions": {"location": "未提供"},
    })
    async with async_session() as db:
        run_id = await add_run(db, "run-normalized")
        service = JDGenerationService(db, llm_provider=MockLLMProvider(output=output))

        draft = await service.generate(request_payload(), agent_run_id=run_id)
        await db.commit()

        assert draft.generation_mode == "llm"
        assert draft.title == "高级 Java 开发工程师"
        assert draft.responsibilities
        assert draft.requirements
        assert draft.skills == ["Java", "Spring Boot", "MySQL"]
        assert (await service.get_run(run_id)).status == "succeeded"


async def test_generation_uses_explicit_template_fallback_when_provider_disabled():
    class DisabledProvider:
        provider_name = "deepseek"
        model_name = "deepseek-chat"
        enabled = False

    async with async_session() as db:
        run_id = await add_run(db)
        service = JDGenerationService(db, llm_provider=DisabledProvider())

        draft = await service.generate(request_payload(), agent_run_id=run_id)
        await db.commit()

        assert draft.generation_mode == "template"
        assert draft.skills == ["Java", "Spring Boot", "MySQL"]
        assert "未配置 DeepSeek" in draft.warnings[0]
        assert (await service.get_run(run_id)).status == "degraded"


async def test_input_suggestion_audits_structured_llm_output():
    output = LLMJDInputSuggestion(
        suggestions=["Java", "Spring Boot", "MySQL"],
        warnings=[],
    )
    async with async_session() as db:
        run_id = await add_run(db, "run-suggestion")
        service = JDGenerationService(db, llm_provider=MockLLMProvider(output=output))

        result = await service.suggest_input(
            JDInputSuggestionRequest(
                title="高级 Java 开发工程师",
                mode="requirements",
                department="后台开发组",
            ),
            agent_run_id=run_id,
        )
        await db.commit()

        assert result.suggestions == ["Java", "Spring Boot", "MySQL"]
        run = await service.get_run(run_id)
        assert run.status == "succeeded"
        assert run.structured_output["suggestions"] == result.suggestions
