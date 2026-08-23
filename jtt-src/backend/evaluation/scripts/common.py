"""评测脚本共享工具。"""
import json
import re
import unicodedata
from pathlib import Path


def load_json(path: str | Path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str | Path, data) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def pending(name: str, count: int = 0) -> dict:
    return {"metric": name, "status": "pending", "count": count, "accuracy": None}


def normalized(value) -> str:
    return "" if value is None else " ".join(str(value).strip().lower().split())


SKILL_ALIASES = {
    "vue3": "vue", "vue.js": "vue", "vuejs": "vue",
    "大语言模型": "llm", "大型语言模型": "llm", "large language model": "llm",
    "自然语言处理": "nlp", "natural language processing": "nlp",
    "嵌入式linux": "linux", "c语言": "c",
    "deepseek api": "deepseek", "deepseekapi": "deepseek",
    "sqlalchemy2.0": "sqlalchemy", "sqlalchemy 2.0": "sqlalchemy",
    "pytorch框架": "pytorch", "docker容器": "docker",
    "altium": "altium designer", "designer": "altium designer",
    "restful api": "restful", "restful": "restful",
    "pydantic v2": "pydantic", "office相关软件": "office",
}


def normalized_skill(value) -> str:
    text = unicodedata.normalize("NFKC", normalized(value))
    text = re.sub(r"\s+", " ", text).strip()
    # Resume models often append an English abbreviation in parentheses.
    text = re.sub(r"\s*[（(].*?[）)]", "", text).strip()
    return SKILL_ALIASES.get(text, text)


def set_value(value) -> set[str]:
    values = re.split(r"[,，、;/；|]", value) if isinstance(value, str) else (value or [])
    return {normalized_skill(v) for v in values if normalized_skill(v)}
