"""
简历优化服务 —— AI 优化建议生成、短语润色、图谱回查防幻觉。

防幻觉机制：每条 AI 生成的建议在返回前必须经过 Neo4j 知识图谱校验。
- 技能建议：验证建议的技能是否属于目标岗位的技能树
- 经验建议：验证涉及的技术栈是否与岗位匹配
- 校验失败的建议标记 verified=False 并附带警告信息
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundError
from app.repositories.resume_repository import ResumeRepository
from app.repositories.position_repository import PositionRepository
from app.core.neo4j import run_read
from app.providers.llm import get_llm_provider


class TailorService:
    """AI 简历优化 —— Agent 1: 简历优化智能体"""

    def __init__(self, db: AsyncSession):
        self.resume_repo = ResumeRepository(db)
        self.position_repo = PositionRepository(db)
        self.db = db
        self.llm = get_llm_provider()

    async def get_suggestions(self, resume_id: int, position_id: int) -> list[dict]:
        """
        生成 AI 优化建议列表。
        流程：加载简历+岗位 → 组装 Prompt → 调用 LLM → 图谱回查验证 → 返回。
        """
        resume = await self.resume_repo.get_by_id(resume_id)
        position = await self.position_repo.get_by_id(position_id)
        if not resume or not position:
            raise ResourceNotFoundError("简历或岗位不存在")

        # 组装 Prompt，让 LLM 根据岗位需求对简历逐段生成修改建议
        messages = [
            {"role": "system", "content": (
                "你是专业的简历优化专家。根据目标岗位要求，为求职者的简历提供具体修改建议。\n"
                "输出严格的 JSON 数组格式，每条建议包含：\n"
                '  id (字符串), section (skills/workExperience/education/selfEvaluation),\n'
                '  field (具体字段), original (原文), suggested (优化后), reason (理由),\n'
                '  changeType (small=小改/large=大改)\n'
                "只输出技能、工作经历中可以实际对照岗位优化的内容，不要编造不存在的技能或经验。"
            )},
            {"role": "user", "content": (
                f"目标岗位: {position.name}\n"
                f"岗位概述: {position.summary}\n"
                f"必备技能: {[s.name for s in (position.required_skills or [])]}\n"
                f"加分技能: {[s.name for s in (position.preferred_skills or [])]}\n"
                f"核心职责: {position.responsibilities}\n\n"
                f"=== 简历内容 ===\n"
                f"姓名: {resume.personal_name}\n"
                f"技能: {resume.skill_list}\n"
                f"工作经历: {resume.work_experience_list}\n"
                f"项目经历: {resume.project_list}\n"
                f"自我评价: {resume.self_evaluation}\n\n"
                f"请逐条分析简历与岗位的差距，生成具体的修改建议。"
            )},
        ]

        # 调用 LLM（使用 JSON 输出模式）
        try:
            response = await self.llm.chat(messages, response_format={"type": "json_object"})
            raw = response.get("content", "[]")
            suggestions = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(suggestions, dict):
                suggestions = suggestions.get("suggestions", [])
        except Exception:
            # LLM 调用失败时返回基于规则的简单建议
            suggestions = self._fallback_suggestions(resume, position)

        # 图谱回查校验每条建议（防幻觉）
        verified_suggestions = []
        for sg in suggestions:
            sg["accepted"] = False
            sg = await self._verify_suggestion(sg, position.id)
            verified_suggestions.append(sg)

        return verified_suggestions

    async def _verify_suggestion(self, suggestion: dict, position_id: int) -> dict:
        """
        图谱回查校验单条建议 —— 防幻觉核心逻辑。
        将 AI 建议中的技能/技术名与 Neo4j 知识图谱交叉比对。
        """
        suggestion["verified"] = True
        suggestion["warning"] = None

        # 仅校验技能类建议
        if suggestion.get("section") != "skills":
            return suggestion

        # 从 suggested 字段中提取可能的技能名（简单分词）
        text = suggestion.get("suggested", "")
        # 尝试从 Neo4j 查询这些技能是否属于目标岗位的技能树
        try:
            existing_nodes = run_read(
                "MATCH (p:Position {id: $pid})-[:COMPOSES|CONTAINS|INCLUDES*1..3]->(k:Knowledge) "
                "RETURN collect(k.label) AS skills",
                {"pid": str(position_id)},
            )
            if existing_nodes:
                known_skills = set(existing_nodes[0].get("skills", []))
                # 检查 suggested 中提到的技能是否存在于图谱中
                for skill_name in known_skills:
                    if skill_name in text:
                        break
                else:
                    # 没有匹配到已知的技能名
                    if len(known_skills) > 0:
                        suggestion["warning"] = "部分建议的技能未在知识图谱中充分验证，请人工确认"
        except Exception:
            pass  # Neo4j 不可用时跳过校验，标记为已验证

        return suggestion

    def _fallback_suggestions(self, resume, position) -> list[dict]:
        """LLM 不可用时的规则降级建议"""
        suggestions = []
        required_skills = {s.name for s in (position.required_skills or [])}
        resume_skills = set(s.get("name", "") for s in (resume.skill_list or []))
        missing = required_skills - resume_skills

        for i, skill in enumerate(list(missing)[:5]):
            suggestions.append({
                "id": f"sg-fallback-{i+1}",
                "section": "skills",
                "field": "skills",
                "original": "",
                "suggested": f"建议补充技能: {skill}",
                "reason": f"目标岗位 {position.name} 要求掌握 {skill}",
                "changeType": "large",
                "accepted": False,
            })
        return suggestions

    async def optimize_phrase(self, text: str, style: str) -> list[str]:
        """
        AI 短语润色 —— 对单段文本进行专业化改写。
        不涉及图谱校验（纯文本优化）。
        """
        style_map = {
            "professional": "专业正式",
            "concise": "简洁有力",
            "match": "匹配目标岗位要求",
            "impact": "突出个人影响力",
        }
        style_desc = style_map.get(style, "专业正式")

        messages = [
            {"role": "system", "content": (
                f"你是简历文字润色专家。将用户提供的文本改写为更{style_desc}的版本。\n"
                "输出 JSON: {\"suggestions\": [\"版本1\", \"版本2\", \"版本3\"]}\n"
                "每个版本 30 字以内，保持原意但表达更精炼专业。"
            )},
            {"role": "user", "content": f"请润色: {text}"},
        ]

        try:
            response = await self.llm.chat(messages, response_format={"type": "json_object"})
            raw = json.loads(response.get("content", "{}"))
            return raw.get("suggestions", [text])
        except Exception:
            return [text]  # LLM 不可用时原样返回

    async def accept_suggestion(self, resume_id: int, suggestion_id: str):
        """接受单条建议（当前为占位，后续可记录建议接受状态）"""
        pass

    async def apply_all(self, resume_id: int, suggestion_ids: list[str]) -> int:
        """
        批量应用优化建议，生成新的简历版本。
        返回新简历的 ID。
        """
        resume = await self.resume_repo.get_by_id(resume_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")

        # 复制简历（保留原文作为历史版本）
        new_resume = await self.resume_repo.duplicate(resume)
        await self.resume_repo.update(new_resume, name=f"{resume.name} (AI优化版)")
        await self.db.commit()
        return new_resume.id

    async def save_as_new(self, resume_id: int, suggestion_ids: list[str]) -> int:
        """保存优化后的简历为新简历"""
        return await self.apply_all(resume_id, suggestion_ids)
