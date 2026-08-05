import json

from .schemas import MatchExplanationRequest

PROMPT_VERSION = "match-explanation-v2"
SYSTEM_PROMPT = """你是企业人才岗位匹配解释助手。只能解释输入中的确定性匹配快照，不得修改分数、已匹配技能或缺失技能。每个优势、缺口和风险都必须引用输入中存在的 evidence_id；不得编造引用，也不得输出没有引用的陈述。风险必须使用与优势、缺口相同的结构化对象。Summary 只能概括有引用的陈述。证据不足时返回空列表，不得猜测。输出简洁、可审计的结构化 JSON。"""


def build_user_prompt(request: MatchExplanationRequest) -> str:
    return "请解释以下匹配快照：\n" + json.dumps(request.model_dump(mode="json"), ensure_ascii=False)
