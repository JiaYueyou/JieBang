"""JD Generation Prompt v3。"""

from jiebang_agents.jd_generation.schemas import GenerateJDRequest

PROMPT_VERSION = "jd-generation-v3"

SYSTEM_PROMPT = """你是企业招聘 JD 起草助手。
只根据用户明确提供的需求生成可编辑草稿，不得虚构薪资、福利、学历、工作年限、公司制度或合规承诺。
岗位名称、职级和部门由系统控制，不能在输出中修改。未知信息写入 assumptions 或 warnings。
只返回 JSON 对象，不得返回 Markdown、解释文字或额外字段。"""


def build_user_prompt(request: GenerateJDRequest) -> str:
    return """请生成一份待人工审核的岗位 JD 草稿。
生成模式：{mode}
岗位名称：{title}
职级：{level}
部门：{department}
地点：{location}
公司：{company}
招聘人数：{headcount}
需求或人才画像：{skills_input}

严格返回下列 JSON 对象：
{{
  "standardized_title": "可选标准岗位名称或 null",
  "responsibilities": ["职责 1"],
  "requirements": ["要求 1"],
  "skills": ["核心技能"],
  "bonus_skills": ["加分技能"],
  "jd_text": "完整 JD 正文",
  "assumptions": ["待确认事项"],
  "warnings": ["风险或需人工复核事项"]
}}
数组字段必须是字符串数组；不得输出 position_name、title、level、department、generation_mode。""".format(
        mode=request.mode.value,
        title=request.title,
        level=request.level or "未提供",
        department=request.department or "未提供",
        location=request.location or "未提供",
        company=request.company or "未提供",
        headcount=request.headcount or "未提供",
        skills_input=request.skills_input or "未提供",
    )
