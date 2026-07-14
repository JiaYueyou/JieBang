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
    DEEPSEEK_CONNECT_TIMEOUT_SECONDS,
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
        self.connect_timeout_seconds = DEEPSEEK_CONNECT_TIMEOUT_SECONDS

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
        schema_text = json.dumps(
            response_schema.model_json_schema(), ensure_ascii=False, separators=(",", ":")
        )
        schema_instruction = (
            "\n\n你必须只返回一个 JSON 对象，并严格满足以下 JSON Schema；"
            "不得增加解释性文本：\n" + schema_text
        )
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt + schema_instruction},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        last_error = "unknown provider error"
        for attempt in range(2):
            raw_content = ""
            try:
                timeout = httpx.Timeout(
                    timeout_seconds,
                    connect=min(
                        float(self.connect_timeout_seconds),
                        float(timeout_seconds),
                    ),
                )
                # DeepSeek calls intentionally use the standard direct route.
                async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    response.raise_for_status()
                    raw_content = response.json()["choices"][0]["message"]["content"]
                    return response_schema.model_validate(json.loads(raw_content))
            except httpx.ConnectTimeout as exc:
                raise RuntimeError(
                    "DeepSeek connection or TLS handshake timed out after "
                    f"{min(self.connect_timeout_seconds, timeout_seconds)} seconds"
                ) from exc
            except httpx.ReadTimeout as exc:
                # Retrying the same long prompt immediately only doubles the UI wait.
                raise RuntimeError(
                    f"DeepSeek response timed out after {timeout_seconds} seconds"
                ) from exc
            except httpx.TimeoutException as exc:
                raise RuntimeError(f"DeepSeek request timed out: {type(exc).__name__}") from exc
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                last_error = f"DeepSeek returned HTTP {status}"
                if status not in {429, 500, 502, 503, 504}:
                    break
            except httpx.RequestError as exc:
                detail = str(exc).strip() or type(exc).__name__
                raise RuntimeError(f"DeepSeek request failed: {detail}") from exc
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                detail = str(exc).strip() or type(exc).__name__
                last_error = f"invalid structured output: {detail}"
                if attempt == 0 and raw_content:
                    payload["messages"] = [
                        payload["messages"][0],
                        {
                            "role": "user",
                            "content": (
                                user_prompt
                                + "\n\n上一次输出未通过 Schema 校验。请修复后只返回 JSON。"
                                + f"\n校验错误：{detail[:1500]}"
                                + f"\n上一次输出：{raw_content[:6000]}"
                            ),
                        },
                    ]
            if attempt == 0:
                await asyncio.sleep(0.5)
        raise RuntimeError(f"DeepSeek structured output failed: {last_error}")
