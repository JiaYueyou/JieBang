PROMPT_VERSION = "skill-extract-v2"

SYSTEM_PROMPT = """你是招聘技能抽取器。只输出文本中明确出现且可验证的技术技能，
不得推测；kind 只能是 required 或 preferred；只返回符合 Schema 的 JSON。"""


def build_user_prompt(*, text: str, known_skills: list[str]) -> str:
    normalized = " ".join(text.split())[:8000]
    known = "，".join(known_skills) or "无"
    return f"从以下 JD 中仅补充已知规则未识别的明确技能。已识别技能：{known}。JD：{normalized}"
