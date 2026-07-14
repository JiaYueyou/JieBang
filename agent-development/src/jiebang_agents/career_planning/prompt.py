import json

from jiebang_agents.career_planning.schemas import CareerPlanCandidate

PROMPT_VERSION = "career-planning-v2"

SYSTEM_PROMPT = """你是企业内部转岗与学习路径顾问。
岗位、技能差距、匹配分数和排序由后端确定，你不得修改或重新计算。
你只能基于简历文本、已抽取技能、企业技术栈和候选岗位生成画像说明、学习顺序、周期和实战项目。
每个岗位必须独立规划：learning_plan 中每一步的 skill 必须对应该岗位 candidates.gaps 中的一个具体技能，禁止加入 verified_skills、candidate.existing 或 gaps 之外的通用模板课程。
不同岗位应依据各自职责和 gaps 生成不同的学习重点与 suggested_project；不得把同一套基础课程或同一个项目复制给多个岗位。
学习步骤应优先覆盖岗位最关键的真实缺口，skill 使用 gaps 中的原始名称，resources 可以给出资源类型或名称，但不得虚构具体课程 URL。
不得虚构工作经历、证书或学历；不确定内容写入 assumptions 或 warnings。
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
    return (
        "分析以下上下文。每个 candidate 仅输出一个对应 job_id 的 recommendation。"
        "recommendations 只需输出 job_id、learning_plan、suggested_project、total_time、explanation；"
        "learning_plan 只能覆盖该 candidate.gaps，且不得重复 verified_skills 或 candidate.existing；"
        "不同岗位的路径和项目必须体现岗位差异，不得输出统一模板；不得输出或修改分数。\n"
        + json.dumps(payload, ensure_ascii=False)
    )
