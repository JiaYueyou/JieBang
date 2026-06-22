"""LLM Provider Mock 行为测试。"""

import pytest

from app.providers import DeepSeekProvider, MockLLMProvider
import app.providers.llm as llm_module
from app.schemas.skill import LLMDiscoveredSkill, LLMDiscoveredSkills


async def test_mock_provider_returns_validated_schema():
    output = LLMDiscoveredSkills(
        skills=[
            LLMDiscoveredSkill(
                name="Spring AI", category="framework", kind="required",
                confidence=0.82, evidence="熟悉 Spring AI",
            )
        ]
    )
    result = await MockLLMProvider(output=output).generate_structured(
        system_prompt="", user_prompt="", response_schema=LLMDiscoveredSkills,
        timeout_seconds=1, metadata={},
    )
    assert result == output


async def test_mock_provider_propagates_timeout():
    provider = MockLLMProvider(error=TimeoutError("model timeout"))
    with pytest.raises(TimeoutError):
        await provider.generate_structured(
            system_prompt="", user_prompt="", response_schema=LLMDiscoveredSkills,
            timeout_seconds=1, metadata={},
        )


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


async def test_deepseek_retries_invalid_json_then_succeeds(monkeypatch):
    contents = iter(["not-json", "{bad", '{"skills": []}'])
    calls = []

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            calls.append(1)
            return _FakeResponse(next(contents))

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(llm_module.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(llm_module.asyncio, "sleep", no_sleep)
    provider = DeepSeekProvider()
    provider.api_key = "test-key"
    result = await provider.generate_structured(
        system_prompt="", user_prompt="", response_schema=LLMDiscoveredSkills,
        timeout_seconds=1, metadata={},
    )
    assert result.skills == []
    assert len(calls) == 3


async def test_deepseek_rejects_invalid_json_after_retries(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            calls.append(1)
            return _FakeResponse("invalid")

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(llm_module.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(llm_module.asyncio, "sleep", no_sleep)
    provider = DeepSeekProvider()
    provider.api_key = "test-key"
    with pytest.raises(RuntimeError):
        await provider.generate_structured(
            system_prompt="", user_prompt="", response_schema=LLMDiscoveredSkills,
            timeout_seconds=1, metadata={},
        )
    assert len(calls) == 3
