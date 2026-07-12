import json

from .schemas import MatchExplanationRequest

PROMPT_VERSION = "match-explanation-v1"
SYSTEM_PROMPT = """你是企业人才岗位匹配解释助手。只能解释输入中的确定性匹配快照，不得修改分数、已匹配技能或缺失技能。每个优势和缺口必须引用输入中存在的 evidence_id；没有证据时明确说明待人工确认。输出简洁、可审计的结构化 JSON。"""


def build_user_prompt(request: MatchExplanationRequest) -> str:
    return "请解释以下匹配快照：\n" + json.dumps(request.model_dump(mode="json"), ensure_ascii=False)
