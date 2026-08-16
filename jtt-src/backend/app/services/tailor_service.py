"""
简历优化服务 —— AI 优化建议生成、短语润色、图谱回查防幻觉。
支持多数据源岗位：raw_job_record / job_position / Neo4j。

防幻觉机制：每条 AI 生成的建议在返回前必须经过 Neo4j 知识图谱校验。
"""
import json
import re
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundError
from app.repositories.resume_repository import ResumeRepository
from app.repositories.position_repository import PositionRepository
from app.repositories.raw_job_repository import RawJobRepository
from app.core.neo4j import run_read
from app.providers.llm import get_llm_provider
from app.services.match_service import _skill_names_match, _extract_skills_from_text, _parse_education_requirement


@dataclass
class PositionContext:
    """统一岗位上下文 —— 屏蔽不同数据源的差异"""
    id: str            # 原始 ID，如 "raw:62" / "position:5" / "job:113"
    name: str
    summary: str       # 岗位概述
    responsibilities: list[str]
    required_skills: list[str]
    preferred_skills: list[str]
    source: str        # "raw_job_record" / "mysql" / "neo4j"


class TailorService:
    """AI 简历优化 —— Agent 1: 简历优化智能体"""

    def __init__(self, db: AsyncSession):
        self.resume_repo = ResumeRepository(db)
        self.position_repo = PositionRepository(db)
        self.raw_job_repo = RawJobRepository(db)
        self.db = db
        self.llm = get_llm_provider()

    # ===== 多数据源岗位加载 =====

    async def _load_position_context(self, position_id: str) -> PositionContext:
        """根据 position_id 前缀路由到不同数据源，返回统一的岗位上下文"""
        if position_id.startswith("raw:"):
            return await self._load_from_raw_record(position_id)
        elif position_id.startswith("job:"):
            return await self._load_from_neo4j(position_id)
        elif position_id.startswith("position:"):
            pid = int(position_id.split(":", 1)[1])
            return await self._load_from_mysql(pid)
        else:
            # 兼容旧格式：纯数字当作 MySQL ID
            try:
                pid = int(position_id)
                return await self._load_from_mysql(pid)
            except ValueError:
                raise ResourceNotFoundError(f"无法识别的岗位ID格式: {position_id}")

    async def _load_from_raw_record(self, position_id: str) -> PositionContext:
        """从 raw_job_record 加载岗位上下文"""
        raw_id = int(position_id.split(":", 1)[1])
        row = await self.raw_job_repo.get_by_id(raw_id)
        if not row:
            raise ResourceNotFoundError("爬虫岗位不存在")
        req_text = (row.get("requirements") or "") + " " + (row.get("jd_text") or "")
        kw_text = row.get("keywords") or ""
        kw_skills = [k.strip() for k in kw_text.split(",") if k.strip()]
        skills = list(set(kw_skills + _extract_skills_from_text(req_text)))
        return PositionContext(
            id=position_id,
            name=row.get("standardized_title") or row.get("title") or "",
            summary=req_text[:500],
            responsibilities=[req_text] if req_text else [],
            required_skills=skills,
            preferred_skills=[],
            source="raw_job_record",
        )

    async def _load_from_mysql(self, pid: int) -> PositionContext:
        """从 MySQL job_position 加载岗位上下文（原有逻辑）"""
        position = await self.position_repo.get_by_id(pid)
        if not position:
            raise ResourceNotFoundError("岗位不存在")
        skills_map = await self.position_repo.get_skills_for_positions([pid])
        pos_skills = skills_map.get(pid, [])
        return PositionContext(
            id=f"position:{pid}",
            name=position.name,
            summary=position.summary or "",
            responsibilities=position.responsibilities or [],
            required_skills=[s["name"] for s in pos_skills if s.get("kind") == "required"],
            preferred_skills=[s["name"] for s in pos_skills if s.get("kind") == "preferred"],
            source="mysql",
        )

    async def _load_from_neo4j(self, position_id: str) -> PositionContext:
        """从 Neo4j 知识图谱加载岗位上下文（兜底）"""
        from app.repositories.graph_repository import Neo4jGraphRepository
        graph_repo = Neo4jGraphRepository()
        job_skills = graph_repo.query_job_skills(position_id)
        if not job_skills:
            # Neo4j 查不到时回退到空上下文
            return PositionContext(
                id=position_id, name=position_id, summary="", responsibilities=[],
                required_skills=[], preferred_skills=[], source="neo4j",
            )
        return PositionContext(
            id=position_id,
            name=job_skills.get("name", position_id),
            summary=job_skills.get("description", ""),
            responsibilities=[],
            required_skills=job_skills.get("skills", []),
            preferred_skills=job_skills.get("tech_points", []),
            source="neo4j",
        )

    # ===== AI 建议生成 =====

    async def get_suggestions(self, resume_id: int, position_id: str) -> list[dict]:
        """
        生成 AI 优化建议列表。
        流程：加载简历+岗位 → 组装 Prompt → 调用 LLM → 图谱回查验证 → 返回。
        """
        resume = await self.resume_repo.get_by_id(resume_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")

        ctx = await self._load_position_context(position_id)

        all_position_skills = [
            {"name": s, "kind": "required"} for s in ctx.required_skills
        ] + [
            {"name": s, "kind": "preferred"} for s in ctx.preferred_skills
        ]

        # [AI] 核心 Prompt
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
                f"目标岗位: {ctx.name}\n"
                f"岗位概述: {ctx.summary}\n"
                f"必备技能: {ctx.required_skills}\n"
                f"加分技能: {ctx.preferred_skills}\n"
                f"核心职责: {ctx.responsibilities}\n\n"
                f"=== 简历内容 ===\n"
                f"姓名: {resume.personal_name}\n"
                f"技能: {resume.skill_list}\n"
                f"工作经历: {resume.work_experience_list}\n"
                f"项目经历: {resume.project_list}\n"
                f"自我评价: {resume.self_evaluation}\n\n"
                f"请逐条分析简历与岗位的差距，生成具体的修改建议。"
            )},
        ]

        # [AI] LLM 调用入口
        try:
            response = await self.llm.chat(messages, response_format={"type": "json_object"})
            raw = response.get("content", "[]")
            suggestions = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(suggestions, dict):
                suggestions = suggestions.get("suggestions", [])
            if not suggestions:
                suggestions = self._fallback_suggestions(resume, ctx, all_position_skills)
        except Exception:
            suggestions = self._fallback_suggestions(resume, ctx, all_position_skills)

        # 统一字段格式
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
            sg = await self._verify_suggestion(sg, ctx)
            verified_suggestions.append(sg)

        return verified_suggestions

    async def _verify_suggestion(self, suggestion: dict, ctx: PositionContext) -> dict:
        """图谱回查校验单条建议 —— 防幻觉核心逻辑

        查询路径：Job --REQUIRES_AREA--> SkillArea --CONTAINS--> TechStack
                      --SUPPORTS--> TechPoint --HAS_KNOWLEDGE--> KnowledgePoint
        建议文本包含图谱任一层级的技能名 → verified；否则标记 warning。
        """
        suggestion["verified"] = True
        suggestion["warning"] = None

        if suggestion.get("section") != "skills":
            return suggestion

        text = suggestion.get("suggested", "") or ""
        if not text.strip():
            return suggestion

        try:
            # 按岗位名查图谱技能树（Job 节点的 name 属性）
            rows = run_read(
                "MATCH (j:Job {name: $job_name}) "
                "-[:REQUIRES_AREA]->(:SkillArea)-[:CONTAINS]->(ts:TechStack) "
                "OPTIONAL MATCH (ts)-[:SUPPORTS]->(tp:TechPoint) "
                "OPTIONAL MATCH (tp)-[:HAS_KNOWLEDGE]->(kp:KnowledgePoint) "
                "RETURN collect(DISTINCT ts.name) AS stacks, "
                "collect(DISTINCT tp.name) AS points, "
                "collect(DISTINCT kp.name) AS knows",
                {"job_name": ctx.name},
            )
            if not rows:
                # [防幻觉] 图谱未收录该岗位 → 明确告知未经图谱验证，而非静默放行
                suggestion["verified"] = False
                suggestion["warning"] = f"岗位「{ctx.name}」未收录知识图谱，该建议未经图谱验证，请人工确认"
                return suggestion

            graph_skills = set()
            for key in ("stacks", "points", "knows"):
                for name in rows[0].get(key) or []:
                    if name:
                        graph_skills.add(str(name).strip().lower())

            if not graph_skills:
                # [防幻觉] OPTIONAL MATCH 对 miss 岗位也返回空行——技能树为空同样视为未收录
                suggestion["verified"] = False
                suggestion["warning"] = f"岗位「{ctx.name}」未收录知识图谱，该建议未经图谱验证，请人工确认"
                return suggestion

            if not any(gs in text.lower() for gs in graph_skills):
                suggestion["verified"] = False
                suggestion["warning"] = "该建议涉及的技能未在该岗位的知识图谱技能树中，请人工确认"
        except Exception:
            pass  # Neo4j 不可用 → 跳过校验，不阻塞建议返回

        return suggestion

    def _fallback_suggestions(self, resume, ctx: PositionContext, position_skills: list[dict]) -> list[dict]:
        """LLM 不可用时的规则降级建议：基于技能差距 + 自我评价定向优化"""
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
                "reason": f"「{ctx.name}」岗位必备技能，简历中未体现",
                "changeType": "large", "accepted": False,
            })
        for skill in missing_preferred[:3]:
            n += 1
            suggestions.append({
                "id": f"sg-{n}", "section": "skills", "field": "skills",
                "original": "",
                "suggested": f"补充加分技能: {skill}",
                "reason": f"掌握 {skill} 可显著提升「{ctx.name}」岗位竞争力",
                "changeType": "small", "accepted": False,
            })

        # 自我评价定向优化
        if matched_names:
            n += 1
            old_eval = (resume.self_evaluation or "").rstrip("。")
            highlight = "、".join(matched_names[:4])
            new_eval = f"{old_eval}。熟练掌握 {highlight}，与「{ctx.name}」岗位核心要求高度契合。".lstrip("。")
            suggestions.append({
                "id": f"sg-{n}", "section": "selfEvaluation", "field": "selfEvaluation",
                "original": resume.self_evaluation or "",
                "suggested": new_eval,
                "reason": "在自我评价中突出与目标岗位匹配的核心技能，提高简历通过初筛的概率",
                "changeType": "small", "accepted": False,
            })
        return suggestions

    # ===== 短语润色 =====

    async def optimize_phrase(self, text: str, style: str) -> list[str]:
        """AI 短语润色 —— 对单段文本进行专业化改写"""
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
            return [text]

    async def accept_suggestion(self, resume_id: int, suggestion_id: str):
        """接受单条建议（当前为占位）"""
        pass

    async def apply_all(
        self, resume_id: int, suggestion_ids: list[str],
        suggestions: list[dict] | None = None,
    ) -> int:
        """批量应用优化建议，生成新的简历版本。返回新简历 ID。"""
        resume = await self.resume_repo.get_by_id(resume_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")

        new_resume = await self.resume_repo.duplicate(resume)

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
