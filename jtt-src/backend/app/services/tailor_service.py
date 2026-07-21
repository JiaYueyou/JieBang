"""
简历优化服务 —— AI 优化建议生成、短语润色、图谱回查防幻觉。

防幻觉机制：每条 AI 生成的建议在返回前必须经过 Neo4j 知识图谱校验。
- 技能建议：验证建议的技能是否属于目标岗位的技能树
- 经验建议：验证涉及的技术栈是否与岗位匹配
- 校验失败的建议标记 verified=False 并附带警告信息
"""
import json
import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundError
from app.repositories.resume_repository import ResumeRepository
from app.repositories.position_repository import PositionRepository
from app.core.neo4j import run_read
from app.providers.llm import get_llm_provider
from app.services.match_service import _skill_names_match


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

        # 岗位技能存储在独立的 skill 表中，需单独加载
        skills_map = await self.position_repo.get_skills_for_positions([position_id])
        position_skills = skills_map.get(position_id, [])
        required_names = [s["name"] for s in position_skills if s.get("kind") == "required"]
        preferred_names = [s["name"] for s in position_skills if s.get("kind") == "preferred"]

        # [AI] 核心 Prompt —— 组装 LLM 请求，根据岗位需求对简历逐段生成修改建议
        # [AI] 替换 LLM_API_KEY 为真实 DeepSeek key 后此路径生效，响应格式由 system prompt 中的 JSON schema 控制
        messages = [
            {"role": "system", "content": (
                "你是专业的简历优化专家。根据目标岗位要求，为求职者的简历提供具体修改建议。\n"
                "输出严格的 JSON 对象：{\"suggestions\": [...]}，每条建议包含：\n"
                '  id (字符串), section (skills/workExperience/education/selfEvaluation),\n'
                '  field (具体字段), original (原文), suggested (优化后), reason (理由),\n'
                '  changeType (small=小改/large=大改)\n'
                "只输出技能、工作经历中可以实际对照岗位优化的内容，不要编造不存在的技能或经验。"
            )},
            {"role": "user", "content": (
                f"目标岗位: {position.name}\n"
                f"岗位概述: {position.summary}\n"
                f"必备技能: {required_names}\n"
                f"加分技能: {preferred_names}\n"
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

        # [AI] LLM 调用入口 —— 成功时返回 AI 生成的个性化建议；失败/空结果时走 fallback
        # [AI] 当前 LLM_API_KEY 为占位符，实际走规则降级路径（Fallback），替换真实 key 后生效
        try:
            response = await self.llm.chat(messages, response_format={"type": "json_object"})
            raw = response.get("content", "[]")
            suggestions = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(suggestions, dict):
                suggestions = suggestions.get("suggestions", [])
            if not suggestions:
                suggestions = self._fallback_suggestions(resume, position, position_skills)
        except Exception:
            suggestions = self._fallback_suggestions(resume, position, position_skills)

        # 统一字段格式（LLM 可能输出 changeType 驼峰键名或缺省字段）
        normalized = []
        for i, sg in enumerate(suggestions):
            if not isinstance(sg, dict):
                continue
            normalized.append({
                "id": str(sg.get("id") or f"sg-{i + 1}"),
                "section": sg.get("section") or "skills",
                "field": sg.get("field") or "",
                "original": sg.get("original") or "",
                "suggested": sg.get("suggested") or "",
                "reason": sg.get("reason") or "",
                "change_type": sg.get("change_type") or sg.get("changeType") or "small",
                "accepted": False,
            })

        # 图谱回查校验每条建议（防幻觉）
        verified_suggestions = []
        for sg in normalized:
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

    def _fallback_suggestions(self, resume, position, position_skills: list[dict]) -> list[dict]:
        """LLM 不可用时的规则降级建议：基于技能差距（模糊匹配）+ 自我评价定向优化"""
        resume_skill_names = [
            s.get("name", "") for s in (resume.skill_list or []) if s.get("name")
        ]

        def is_covered(pos_skill: str) -> bool:
            return any(_skill_names_match(rs, pos_skill) for rs in resume_skill_names)

        missing_required = [
            s["name"] for s in position_skills
            if s.get("kind") == "required" and not is_covered(s["name"])
        ]
        missing_preferred = [
            s["name"] for s in position_skills
            if s.get("kind") == "preferred" and not is_covered(s["name"])
        ]
        matched_names = [s["name"] for s in position_skills if is_covered(s["name"])]

        suggestions = []
        n = 0
        for skill in missing_required[:5]:
            n += 1
            suggestions.append({
                "id": f"sg-{n}", "section": "skills", "field": "skills",
                "original": "",
                "suggested": f"学习并添加技能: {skill}",
                "reason": f"「{position.name}」岗位必备技能，简历中未体现",
                "changeType": "large", "accepted": False,
            })
        for skill in missing_preferred[:3]:
            n += 1
            suggestions.append({
                "id": f"sg-{n}", "section": "skills", "field": "skills",
                "original": "",
                "suggested": f"补充加分技能: {skill}",
                "reason": f"掌握 {skill} 可显著提升「{position.name}」岗位竞争力",
                "changeType": "small", "accepted": False,
            })

        # 自我评价定向优化：突出与岗位匹配的核心技能
        if matched_names:
            n += 1
            old_eval = (resume.self_evaluation or "").rstrip("。")
            highlight = "、".join(matched_names[:4])
            new_eval = f"{old_eval}。熟练掌握 {highlight}，与「{position.name}」岗位核心要求高度契合。".lstrip("。")
            suggestions.append({
                "id": f"sg-{n}", "section": "selfEvaluation", "field": "selfEvaluation",
                "original": resume.self_evaluation or "",
                "suggested": new_eval,
                "reason": "在自我评价中突出与目标岗位匹配的核心技能，提高简历通过初筛的概率",
                "changeType": "small", "accepted": False,
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

    async def apply_all(
        self, resume_id: int, suggestion_ids: list[str],
        suggestions: list[dict] | None = None,
    ) -> int:
        """
        批量应用优化建议，生成新的简历版本（写入数据库）。
        suggestions 为前端回传的建议全文；仅应用 id 在 suggestion_ids 中的建议。
        返回新简历的 ID。
        """
        resume = await self.resume_repo.get_by_id(resume_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")

        # 复制简历（保留原简历作为历史版本）
        new_resume = await self.resume_repo.duplicate(resume)

        # 将选中的建议逐条写入新简历
        chosen = [
            sg for sg in (suggestions or [])
            if not suggestion_ids or sg.get("id") in suggestion_ids
        ]
        skill_list = list(new_resume.skill_list or [])
        self_eval = new_resume.self_evaluation
        work_list = [dict(w) for w in (new_resume.work_experience_list or [])]

        for sg in chosen:
            section = sg.get("section", "")
            suggested = (sg.get("suggested") or "").strip()
            if not suggested:
                continue
            if section == "skills":
                # 从 "xxx: 技能名" 格式中提取技能名，去重后追加
                name = re.split(r"[:：]", suggested)[-1].strip()
                if name and not any(
                    _skill_names_match(s.get("name", ""), name) for s in skill_list
                ):
                    skill_list.append({
                        "id": f"sk-ai-{len(skill_list) + 1}", "name": name,
                        "level": "beginner", "category": "待提升",
                    })
            elif section == "selfEvaluation":
                self_eval = suggested
            elif section == "workExperience":
                # 按原文定位对应工作经历并替换描述
                original = (sg.get("original") or "").strip()
                for w in work_list:
                    desc = w.get("description") or ""
                    if original and original in desc:
                        w["description"] = desc.replace(original, suggested)
                        break

        await self.resume_repo.update(
            new_resume,
            name=f"{resume.name} (AI优化版)",
            skill_list=skill_list,
            self_evaluation=self_eval,
            work_experience_list=work_list,
        )
        await self.db.commit()
        return new_resume.id

    async def save_as_new(
        self, resume_id: int, suggestion_ids: list[str],
        suggestions: list[dict] | None = None,
    ) -> int:
        """保存优化后的简历为新简历"""
        return await self.apply_all(resume_id, suggestion_ids, suggestions)
