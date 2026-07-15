from jiebang_agents.jd_generation import (
    GenerateJDRequest,
    JDGenerationAgent,
    JDInputSuggestionRequest,
    LLMGeneratedJDDraft,
    LLMJDInputSuggestion,
)


class FakeProvider:
    provider_name = "fake"
    model_name = "fake-structured"
    enabled = True

    def __init__(self, output):
        self.output = output
        self.call = None

    async def generate_structured(self, **kwargs):
        self.call = kwargs
        return kwargs["response_schema"].model_validate(self.output.model_dump())


async def test_agent_preserves_system_owned_fields_and_tracks_prompt_version():
    provider = FakeProvider(
        LLMGeneratedJDDraft(
            title="模型试图覆盖的标题",
            responsibilities=["负责服务设计"],
            requirements=["熟悉 Python"],
            skills=["Python"],
            jd_text="可编辑 JD 草稿",
        )
    )
    agent = JDGenerationAgent(provider, timeout_seconds=9)
    request = GenerateJDRequest(
        title="后端工程师",
        level="senior",
        department="研发中心",
        skills_input="Python, FastAPI",
    )

    draft = await agent.generate(request)

    assert draft.title == "后端工程师"
    assert draft.level == "senior"
    assert draft.department == "研发中心"
    assert provider.call["timeout_seconds"] == 9
    assert provider.call["metadata"]["prompt_version"] == agent.prompt_version


async def test_agent_returns_template_when_provider_is_disabled():
    class DisabledProvider:
        provider_name = "disabled"
        model_name = "none"
        enabled = False

    draft = await JDGenerationAgent(DisabledProvider()).generate(
        GenerateJDRequest(title="数据工程师", skills_input="Python，MySQL")
    )

    assert draft.generation_mode == "template"
    assert draft.skills == ["Python", "MySQL"]
    assert draft.warnings


async def test_internal_target_uses_private_mobility_prompt_and_fields():
    provider = FakeProvider(
        LLMGeneratedJDDraft(
            responsibilities=["负责内部平台交付"],
            requirements=["具备相近项目经验"],
            skills=["Python", "FastAPI"],
            trainable_skills=["Kubernetes"],
            transfer_profile=["后端研发背景"],
            manager_confirmations=["确认计划到岗时间"],
            jd_text="内部岗位需求说明",
        )
    )
    draft = await JDGenerationAgent(provider).generate(
        GenerateJDRequest(
            target="internal",
            title="AI 平台工程师",
            department="平台研发部",
            internal_reason="内部能力升级",
            receiving_manager="平台负责人",
        )
    )

    assert draft.target.value == "internal"
    assert draft.trainable_skills == ["Kubernetes"]
    assert not set(draft.skills) & set(draft.trainable_skills)
    assert draft.transfer_profile == ["后端研发背景"]
    assert "内部岗位" in provider.call["system_prompt"]
    assert "不是公开招聘" in provider.call["system_prompt"]
    assert provider.call["metadata"]["target"] == "internal"


async def test_public_target_drops_internal_only_llm_fields():
    provider = FakeProvider(
        LLMGeneratedJDDraft(
            skills=["Python"],
            trainable_skills=["不应保留"],
            transfer_profile=["不应保留"],
            manager_confirmations=["不应保留"],
        )
    )
    draft = await JDGenerationAgent(provider).generate(
        GenerateJDRequest(target="public", title="Python 工程师")
    )

    assert draft.target.value == "public"
    assert draft.trainable_skills == []
    assert draft.transfer_profile == []
    assert draft.manager_confirmations == []
    assert "公开招聘" in provider.call["system_prompt"]


async def test_internal_template_separates_required_and_trainable_skills():
    class DisabledProvider:
        provider_name = "disabled"
        model_name = "none"
        enabled = False

    draft = await JDGenerationAgent(DisabledProvider()).generate(
        GenerateJDRequest(
            target="internal",
            title="平台工程师",
            skills_input="Java, MySQL, Redis, Docker, Kubernetes, Prometheus",
        )
    )

    assert draft.skills == ["Java", "MySQL", "Redis", "Docker"]
    assert draft.trainable_skills == ["Kubernetes", "Prometheus"]
    assert not set(draft.skills) & set(draft.trainable_skills)


async def test_agent_generates_structured_input_suggestions():
    provider = FakeProvider(
        LLMJDInputSuggestion(
            suggestions=["Java", "Spring Boot", "MySQL"],
            warnings=["请结合团队技术栈复核"],
        )
    )
    agent = JDGenerationAgent(provider, timeout_seconds=9)

    result = await agent.suggest_input(
        JDInputSuggestionRequest(
            title="高级 Java 开发工程师",
            mode="requirements",
            level="senior",
            department="后台开发组",
        )
    )

    assert result.suggestions == ["Java", "Spring Boot", "MySQL"]
    assert result.generation_mode == "llm"
    assert provider.call["metadata"]["agent_type"] == "jd_input_suggestion"
    assert provider.call["metadata"]["prompt_version"] == agent.suggestion_prompt_version


async def test_suggestion_fallback_matches_title_and_profile_mode():
    class DisabledProvider:
        provider_name = "disabled"
        model_name = "none"
        enabled = False

    agent = JDGenerationAgent(DisabledProvider())
    skills = await agent.suggest_input(
        JDInputSuggestionRequest(title="Java 开发工程师", mode="requirements")
    )
    profile = await agent.suggest_input(
        JDInputSuggestionRequest(title="Java 开发工程师", mode="profile")
    )

    assert skills.suggestions == ["Java", "Spring Boot", "MySQL", "Redis", "微服务架构"]
    assert profile.suggestions
    assert profile.suggestions != skills.suggestions
    assert skills.generation_mode == profile.generation_mode == "template"
    assert skills.warnings and profile.warnings
