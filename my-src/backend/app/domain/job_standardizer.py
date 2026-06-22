"""岗位标题确定性清洗与图谱展示维度推断。"""

from __future__ import annotations

import re

_NOISE = (
    "急聘", "诚聘", "高薪", "双休", "五险一金", "接受应届", "应届生",
    "实习生", "校招", "社招", "外包", "驻场",
)
_LEVEL_WORDS = (
    "初级", "中级", "高级", "资深", "专家", "首席", "助理",
    "junior", "middle", "senior",
)


def standardize_job_title(title: str) -> tuple[str, str, str, float]:
    original = re.sub(r"\s+", " ", title or "").strip()
    value = re.sub(r"[（(][^（）()]{0,40}[）)]", "", original)
    value = re.sub(r"【[^】]{0,40}】", "", value)
    value = re.sub(r"\s*[-—|·]\s*(北京|上海|深圳|广州|杭州|合肥|武汉|南京|成都|西安).*$", "", value)
    for word in _NOISE:
        value = value.replace(word, "")
    level = infer_job_level(original)
    for word in _LEVEL_WORDS:
        value = re.sub(re.escape(word), "", value, flags=re.IGNORECASE)
    value = re.sub(r"\d+\s*[-~至]\s*\d+\s*年|\d+\s*年以上|经验不限", "", value)
    value = re.sub(r"[/、]\s*$", "", value)
    value = re.sub(r"\s+", "", value).strip("-—_|·/、")
    replacements = {
        "python": "Python", "java": "Java", "javascript": "JavaScript",
        "ai": "AI", "llm": "LLM", "c＋＋": "C++",
    }
    for raw, normalized in replacements.items():
        value = re.sub(raw, normalized, value, flags=re.IGNORECASE)
    if not value:
        value = original or "未命名岗位"
    # Keep specialized role wording; only normalize common equivalent suffixes.
    value = value.replace("软件研发工程师", "软件开发工程师")
    value = value.replace("研发工程师", "开发工程师")
    canonical_key = "".join(ch for ch in value.casefold() if ch.isalnum())
    return value[:180], canonical_key[:220], level, 0.95


def infer_job_level(title: str) -> str:
    lowered = (title or "").casefold()
    if any(word in lowered for word in ("资深", "高级", "专家", "首席", "架构", "senior")):
        return "senior"
    if any(word in lowered for word in ("初级", "助理", "实习", "应届", "junior")):
        return "junior"
    return "middle"


def infer_job_stack(title: str) -> str:
    lowered = (title or "").casefold()
    if any(word in lowered for word in ("算法", "大模型", "ai", "人工智能", "nlp", "视觉", "语音")):
        return "ai"
    if any(word in lowered for word in ("数据", "数仓", "大数据", "flink", "spark")):
        return "data"
    if any(word in lowered for word in ("运维", "devops", "云平台", "sre", "安全")):
        return "devops"
    return "backend"


CATEGORY_STACK = {
    "ai_ml": "ai",
    "cloud": "devops",
    "database": "data",
    "domain_knowledge": "data",
    "programming_language": "backend",
    "framework": "backend",
    "tool": "devops",
    "soft_skill": "backend",
}
