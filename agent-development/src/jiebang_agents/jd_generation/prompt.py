"""JD Generation 与输入建议 Prompt。"""

from jiebang_agents.jd_generation.schemas import GenerateJDRequest, JDInputSuggestionRequest

PROMPT_VERSION = "jd-generation-v4-targeted"
SUGGESTION_PROMPT_VERSION = "jd-input-suggestion-v2-targeted"

PUBLIC_SYSTEM_PROMPT = """你是企业公开招聘 JD 起草助手。
只根据用户明确提供的需求生成可编辑草稿，不得虚构薪资、福利、学历、工作年限、公司制度或合规承诺。
岗位名称、职级和部门由系统控制，不能在输出中修改。未知信息写入 assumptions 或 warnings。
内容面向外部候选人，可以使用清晰的招聘语言，但不能承诺录用、薪酬或福利。
只返回 JSON 对象，不得返回 Markdown、解释文字或额外字段。"""

INTERNAL_SYSTEM_PROMPT = """你是企业内部岗位需求说明起草助手。
该岗位仅用于企业内部人才流动，不是公开招聘 JD，不得使用招聘宣传、对外投递、薪资福利或吸引候选人的措辞。
只根据管理者提供的组织需求生成可编辑内部草稿；岗位名称、职级和接收部门由系统控制，不能在输出中修改。
必须区分岗位必备技能和可在转岗后培养的技能，并给出适合内部转岗的人才特征及管理层待确认事项。
不得假设员工意愿、绩效结论、调动审批结果或公司制度。未知内容写入 assumptions、warnings 或 manager_confirmations。
只返回 JSON 对象，不得返回 Markdown、解释文字或额外字段。"""


def build_user_prompt(request: GenerateJDRequest) -> str:
    if request.target.value == "internal":
        return """请生成一份待管理层审核的内部岗位需求草稿。
岗位名称：{title}
职级：{level}
接收部门：{department}
接收负责人：{receiving_manager}
内部需求原因：{internal_reason}
内部名额：{headcount}
岗位技能或目标人才信息：{skills_input}

严格返回下列 JSON 对象：
{{
  "standardized_title": "可选标准岗位名称或 null",
  "responsibilities": ["内部岗位职责 1"],
  "requirements": ["内部任职要求 1"],
  "skills": ["必须在转岗前具备的核心技能"],
  "bonus_skills": ["可作为优先条件的技能"],
  "trainable_skills": ["允许转岗后培养的技能"],
  "transfer_profile": ["适合内部转岗的人才特征"],
  "manager_confirmations": ["管理层仍需确认的条件"],
  "jd_text": "内部岗位需求说明，不得出现公开投递或招聘宣传",
  "assumptions": ["待确认假设"],
  "warnings": ["风险或需人工复核事项"]
}}
数组字段必须是字符串数组；不得输出 title、level、department、target 或 generation_mode。""".format(
            title=request.title,
            level=request.level or "未提供",
            department=request.department or "未提供",
            receiving_manager=request.receiving_manager or "未提供",
            internal_reason=request.internal_reason or "未提供",
            headcount=request.headcount or "未提供",
            skills_input=request.skills_input or "未提供",
        )
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
  "trainable_skills": [],
  "transfer_profile": [],
  "manager_confirmations": [],
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


PUBLIC_SUGGESTION_SYSTEM_PROMPT = """你是企业公开招聘岗位信息补全助手。
你的任务仅是根据岗位名称，为待人工编辑的表单补充常见核心技能或目标人才特征。
不得生成完整 JD，不得虚构薪资、福利、学历、工作年限、公司制度或合规承诺。
岗位名称、职级和部门由系统控制，不能在输出中修改。
只返回 JSON 对象，不得返回 Markdown、解释文字或额外字段。"""

INTERNAL_SUGGESTION_SYSTEM_PROMPT = """你是企业内部岗位需求信息补全助手。
你的任务仅是根据岗位名称，为内部岗位表单补充必备技能或适合转岗的人才特征。
不得生成公开招聘宣传、薪资福利、对外投递要求或完整 JD。
岗位名称、职级和接收部门由系统控制，不能在输出中修改。
只返回 JSON 对象，不得返回 Markdown、解释文字或额外字段。"""


def build_suggestion_prompt(request: JDInputSuggestionRequest) -> str:
    if request.target.value == "internal":
        target = "5 至 10 个内部岗位必备技能" if request.mode.value == "requirements" else "3 至 6 条适合内部转岗的人才能力特征"
        context = "内部私有需求，仅供企业人才流动分析"
    else:
        target = "5 至 10 个简短、具体、可编辑的常见核心技能" if request.mode.value == "requirements" else "3 至 6 条简短、可编辑的目标人才能力特征"
        context = "公开招聘需求，面向外部候选人"
    return """请为岗位表单生成输入建议。
需求场景：{context}
岗位名称：{title}
生成模式：{mode}
职级：{level}
部门：{department}
输出要求：{target}

严格返回下列 JSON 对象：
{{
  "suggestions": ["建议 1"],
  "warnings": ["需要人工复核的事项"]
}}
suggestions 和 warnings 必须是字符串数组；不得输出 title、mode、level、department 或完整 JD。""".format(
        title=request.title,
        mode=request.mode.value,
        level=request.level or "未提供",
        department=request.department or "未提供",
        target=target,
        context=context,
    )
