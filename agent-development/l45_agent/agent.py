"""L4-L5 智能体：核心逻辑"""

import json
import httpx
from .schema import AgentInput, AgentOutput, L4TechPoint, L5KnowledgePoint
from .prompt import SYSTEM_PROMPT, build_user_prompt


class L45Agent:
    """L4-L5 补全智能体"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com",
                 model: str = "deepseek-v4-flash", timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def complete(self, input_data: AgentInput) -> AgentOutput | None:
        """对单个技能调用 DeepSeek 生成 L4-L5"""
        if not self.enabled:
            print("  [SKIP] API Key 未配置")
            return None

        # 构建提示词
        user_prompt = build_user_prompt(
            skill_name=input_data.skill_name,
            skill_area=input_data.skill_area,
            job_directions=input_data.job_directions,
            evidence_list=[e.model_dump() for e in input_data.evidence],
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    data = json.loads(content)

                    # 转为 AgentOutput
                    tech_points = []
                    for pt in data.get("tech_points", []):
                        kps = [
                            L5KnowledgePoint(
                                name=kp.get("name", ""),
                                description=kp.get("description", ""),
                                difficulty=kp.get("difficulty", "medium"),
                                confidence=min(float(kp.get("confidence", 0.5)), 1.0),
                            )
                            for kp in pt.get("knowledge_points", [])
                        ]
                        tech_points.append(L4TechPoint(
                            name=pt.get("name", ""),
                            detail=pt.get("detail", ""),
                            confidence=min(float(pt.get("confidence", 0.5)), 1.0),
                            knowledge_points=kps,
                        ))

                    return AgentOutput(
                        skill_name=input_data.skill_name,
                        tech_points=tech_points,
                    )

            except Exception as e:
                print(f"  [RETRY] 第{attempt+1}次失败: {e}")
                if attempt == 0:
                    continue
                return None

        return None
