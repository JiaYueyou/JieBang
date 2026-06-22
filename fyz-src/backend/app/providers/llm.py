"""可替换的结构化 LLM Provider。"""

from __future__ import annotations

import asyncio
import json
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel

from app.core.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT_SECONDS,
)

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    provider_name: str
    model_name: str

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        timeout_seconds: int,
        metadata: dict,
    ) -> T: ...


class MockLLMProvider:
    provider_name = "mock"
    model_name = "mock-structured"

    def __init__(self, output: BaseModel | None = None, error: Exception | None = None):
        self.output = output
        self.error = error

    async def generate_structured(self, *, response_schema: type[T], **_kwargs) -> T:
        if self.error:
            raise self.error
        return response_schema.model_validate(
            self.output.model_dump() if self.output else {}
        )


class DeepSeekProvider:
    provider_name = "deepseek"

    def __init__(self) -> None:
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL.rstrip("/")
        self.model_name = DEEPSEEK_MODEL

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        timeout_seconds: int = DEEPSEEK_TIMEOUT_SECONDS,
        metadata: dict,
    ) -> T:
        if not self.enabled:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    return response_schema.model_validate(json.loads(content))
            except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
        raise RuntimeError(f"DeepSeek structured output failed: {last_error}")
