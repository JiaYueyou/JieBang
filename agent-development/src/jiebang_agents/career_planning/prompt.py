import json

from jiebang_agents.career_planning.schemas import CareerPlanCandidate

PROMPT_VERSION = "career-planning-v1"

SYSTEM_PROMPT = """你是企业内部转岗与学习路径顾问。
岗位、技能差距、匹配分数和排序由后端确定，你不得修改或重新计算。
你只能基于简历文本、已抽取技能、企业技术栈和候选岗位生成画像说明、学习顺序、周期和实战项目。
不得虚构工作经历、证书、学历或具体课程 URL；不确定内容写入 assumptions 或 warnings。
只返回符合 Schema 的 JSON。"""


def build_user_prompt(
    *,
    resume_text: str,
    skills: list[str],
    enterprise_tech: str,
    candidates: list[CareerPlanCandidate],
    time_budget_weeks: int,
) -> str:
    payload = {
        "resume_text": resume_text[:12000],
        "verified_skills": skills,
        "enterprise_tech": enterprise_tech,
        "time_budget_weeks": time_budget_weeks,
        "candidates": [item.model_dump(mode="json") for item in candidates],
    }
    return "分析以下上下文。recommendations 只需输出 job_id、learning_plan、suggested_project、total_time、explanation；不得输出或修改分数。\n" + json.dumps(payload, ensure_ascii=False)
