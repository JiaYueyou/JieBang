"""可替换的结构化 LLM Provider。"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel

from app.core.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_CONNECT_TIMEOUT_SECONDS,
    DEEPSEEK_MODEL,
    DEEPSEEK_MAX_ATTEMPTS,
    DEEPSEEK_TIMEOUT_SECONDS,
)

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


@dataclass
class ProviderAttempt:
    attempt: int
    outcome: str
    error_code: str | None
    duration_ms: int
    retry_delay_ms: int = 0


@dataclass
class ProviderDiagnostics:
    attempts: int = 0
    retry_count: int = 0
    duration_ms: int = 0
    outcome: str = "running"
    error_code: str | None = None
    attempt_history: list[ProviderAttempt] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class LLMProviderError(RuntimeError):
    """Stable, non-sensitive provider failure contract for callers and audits."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        retryable: bool,
        attempts: int,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable
        self.attempts = attempts


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
        started = time.perf_counter()
        diagnostics = ProviderDiagnostics()
        metadata["provider_diagnostics"] = diagnostics.to_dict()
        last_error = "unknown provider error"
        last_error_code = "provider_unknown"
        last_retryable = False
        max_attempts = max(
            1,
            min(4, int(metadata.get("max_attempts", DEEPSEEK_MAX_ATTEMPTS))),
        )
        for attempt in range(max_attempts):
            attempt_started = time.perf_counter()
            raw_content = ""
            retryable = False
            error_code: str | None = None
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
                    result = response_schema.model_validate(json.loads(raw_content))
                    diagnostics.attempts = attempt + 1
                    diagnostics.retry_count = attempt
                    diagnostics.duration_ms = int((time.perf_counter() - started) * 1000)
                    diagnostics.outcome = "succeeded"
                    diagnostics.error_code = None
                    diagnostics.attempt_history.append(ProviderAttempt(
                        attempt=attempt + 1,
                        outcome="succeeded",
                        error_code=None,
                        duration_ms=int((time.perf_counter() - attempt_started) * 1000),
                    ))
                    metadata["provider_diagnostics"] = diagnostics.to_dict()
                    return result
            except httpx.ConnectTimeout as exc:
                last_error = (
                    "DeepSeek connection or TLS handshake timed out after "
                    f"{min(self.connect_timeout_seconds, timeout_seconds)} seconds"
                )
                error_code = "provider_connect_timeout"
                retryable = True
            except httpx.ReadTimeout as exc:
                last_error = f"DeepSeek response timed out after {timeout_seconds} seconds"
                error_code = "provider_read_timeout"
                retryable = True
            except httpx.TimeoutException as exc:
                last_error = f"DeepSeek request timed out: {type(exc).__name__}"
                error_code = "provider_timeout"
                retryable = True
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                last_error = f"DeepSeek returned HTTP {status}"
                error_code = (
                    "provider_rate_limited" if status == 429
                    else "provider_server_error" if status >= 500
                    else "provider_auth_error" if status in {401, 403}
                    else "provider_request_rejected"
                )
                retryable = status in {408, 429, 500, 502, 503, 504}
            except httpx.RequestError as exc:
                detail = str(exc).strip() or type(exc).__name__
                last_error = f"DeepSeek request failed: {detail}"
                error_code = "provider_transport_error"
                retryable = True
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                detail = str(exc).strip() or type(exc).__name__
                last_error = f"invalid structured output: {detail}"
                error_code = "provider_invalid_output"
                retryable = True
                if raw_content:
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
            last_error_code = error_code or "provider_unknown"
            last_retryable = retryable
            should_retry = retryable and attempt + 1 < max_attempts
            delay = min(4.0, 0.75 * (2 ** attempt)) if should_retry else 0.0
            diagnostics.attempt_history.append(ProviderAttempt(
                attempt=attempt + 1,
                outcome="retrying" if should_retry else "failed",
                error_code=last_error_code,
                duration_ms=int((time.perf_counter() - attempt_started) * 1000),
                retry_delay_ms=int(delay * 1000),
            ))
            diagnostics.attempts = attempt + 1
            diagnostics.retry_count = attempt if not should_retry else attempt + 1
            diagnostics.error_code = last_error_code
            metadata["provider_diagnostics"] = diagnostics.to_dict()
            if should_retry:
                logger.warning(
                    "deepseek_structured_retry attempt=%d/%d delay=%.2fs error_code=%s",
                    attempt + 1, max_attempts, delay, last_error_code,
                )
                await asyncio.sleep(delay)
                continue
            break
        diagnostics.duration_ms = int((time.perf_counter() - started) * 1000)
        diagnostics.outcome = "failed"
        diagnostics.error_code = last_error_code
        metadata["provider_diagnostics"] = diagnostics.to_dict()
        suffix = (
            f" ({diagnostics.attempts} attempts exhausted)"
            if last_retryable and diagnostics.attempts >= max_attempts
            else ""
        )
        raise LLMProviderError(
            f"DeepSeek structured output failed: {last_error}{suffix}",
            error_code=last_error_code,
            retryable=last_retryable,
            attempts=diagnostics.attempts,
        )
