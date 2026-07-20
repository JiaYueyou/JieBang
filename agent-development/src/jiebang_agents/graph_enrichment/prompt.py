PROMPT_VERSION = "skill-l45-completion-v1"

SYSTEM_PROMPT = """你是岗位能力图谱的 L4/L5 补全 Agent。
输入中的 Job、SkillArea、TechStack 已由确定性流程验证，你只能补全该路径下的 TechPoint 和 KnowledgePoint。
每个技术点和知识点必须能被输入原文直接支持，引用至少两个不同平台来源的 source_id。
严禁编造输入中不存在的 source_id；只能使用 evidence 列表里出现过的 source_id。
不得生成岗位、技能领域或技术栈之外的新上游节点，不得推测。
只返回符合 Schema 的 JSON。"""


def build_user_prompt(context: dict) -> str:
    import json

    return """依据以下已验证上下文补全 L4/L5：
{context}

严格返回：
{{
  "skill_name": "与输入 tech_stack 一致",
  "job_directions": ["输入中的岗位方向"],
  "skill_area": "与输入 skill_area 一致",
  "tech_points": [{{
    "name": "L4 技术点",
    "detail": "证据支持的说明",
    "confidence": 0.0,
    "source_ids": [1, 2],
    "knowledge_points": [{{
      "name": "L5 知识点",
      "description": "证据支持的说明",
      "difficulty": "easy|medium|hard",
      "confidence": 0.0,
      "source_ids": [1, 2],
      "prerequisites": []
    }}]
  }}]
}}""".format(context=json.dumps(context, ensure_ascii=False))
