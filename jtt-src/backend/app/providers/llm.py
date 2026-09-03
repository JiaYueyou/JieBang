"""
大模型 Provider —— 封装 LLM API 调用，支持结构化和非结构化输出。
包含真实 Provider (DeepSeek/讯飞星火) 和 Mock Provider (测试用)。
"""
import asyncio
import json
import httpx
from app.core.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT_SECONDS, TESTING


class LLMProvider:
    """LLM 调用接口，所有 Provider 需实现 chat 方法"""

    async def chat(self, messages: list[dict], response_format: dict | None = None) -> dict:
        """
        调用大模型。
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        response_format: 可选，强制 JSON 输出 {"type": "json_object"}
        返回: {"content": "回复文本", "usage": {"prompt_tokens": N, "completion_tokens": N}}
        """
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    """测试用 Mock Provider，不调用真实 API"""

    async def chat(self, messages: list[dict], response_format: dict | None = None) -> dict:
        # 返回一个模拟的成功响应
        return {
            "content": json.dumps({"result": "mock_response"}) if response_format else "这是 Mock 回复。",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }


class DeepSeekProvider(LLMProvider):
    """DeepSeek API Provider，也兼容讯飞星火 OpenAI 兼容接口"""

    def __init__(self):
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL.rstrip("/")
        self.model = LLM_MODEL
        self.timeout = LLM_TIMEOUT_SECONDS

    async def chat(self, messages: list[dict], response_format: dict | None = None) -> dict:
        """调用 DeepSeek Chat API，支持结构化 JSON 输出"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,  # 降低随机性，输出更稳定
            "max_tokens": 8192,  # 思考型模型需要足够空间，防 content 被截断
        }
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 最多重试 1 次（指数退避）；async 环境必须用 asyncio.sleep，
        # time.sleep 会阻塞事件循环导致整个服务无响应
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    msg = data["choices"][0]["message"]
                    # 思考型模型可能把结论放在 reasoning_content，content 为空时兜底取它
                    content = msg.get("content") or msg.get("reasoning_content") or ""
                    return {
                        "content": content,
                        "usage": data.get("usage", {}),
                    }
            except Exception as e:
                if attempt == 1:
                    raise RuntimeError(f"LLM API 调用失败（已重试2次）: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # 指数退避: 1s


def get_llm_provider() -> LLMProvider:
    """工厂函数：测试模式返回 Mock，否则返回真实 Provider"""
    if TESTING:
        return MockLLMProvider()
    return DeepSeekProvider()
