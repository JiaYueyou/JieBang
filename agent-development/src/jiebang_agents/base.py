"""Agent 与宿主后端之间的最小 Provider 接口。"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class StructuredLLMProvider(Protocol):
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
