"""L4-L5 智能体：提示词模板"""

SYSTEM_PROMPT = """你是岗位能力图谱的 L4/L5 补全专家。
你的任务是根据招聘数据中的岗位描述和技能要求，为指定技能补充详细的技术点(L4)和知识点(L5)。

## 背景
用户已经通过确定性规则构建了 L1(岗位) → L2(技能领域) → L3(技术栈) 三层结构。
现在需要你基于招聘原文证据，为每个 L3 技能补充下层的技术细节。

## 规则
1. 只基于提供的证据文本分析，不要编造不存在的内容
2. 每个技术点必须对应一个具体的、可实践的技能方向
3. 每个知识点标注难度：easy(入门) / medium(进阶) / hard(深入)
4. 置信度表示你对该内容与招聘需求的匹配程度
5. 输出 JSON 格式，不要有多余文字"""


def build_user_prompt(skill_name: str, skill_area: str, job_directions: list[str],
                      evidence_list: list[dict]) -> str:
    """构建用户提示词"""
    evidence_text = "\n".join(
        f"[来源{i+1}] {e.get('source_platform', '')}: {e.get('evidence_text', '')[:300]}"
        for i, e in enumerate(evidence_list)
    )

    directions = "、".join(job_directions) if job_directions else "未指定"

    return f"""请为以下技能补充 L4 技术点和 L5 知识点：

## 技能信息
- 技能名称：{skill_name}
- 技能领域：{skill_area}
- 关联岗位：{directions}

## 招聘原文证据
{evidence_text}

## 输出要求
生成该技能的 L4 技术点列表，每个技术点包含：
- name：技术点名称
- detail：技术点详细说明（50-200字）
- confidence：置信度 0-1
- knowledge_points：该技术点下的 L5 知识点列表
  - name：知识点名称
  - description：知识点说明
  - difficulty：easy / medium / hard
  - confidence：置信度 0-1

### 输出示例
{{
  "skill_name": "{skill_name}",
  "tech_points": [
    {{
      "name": "索引设计与优化",
      "detail": "根据业务场景设计合理的数据库索引...",
      "confidence": 0.85,
      "knowledge_points": [
        {{
          "name": "联合索引最左前缀原则",
          "description": "理解联合索引的匹配顺序",
          "difficulty": "medium",
          "confidence": 0.82
        }}
      ]
    }}
  ]
}}

注意：只返回 JSON，不要多余文字。"""
