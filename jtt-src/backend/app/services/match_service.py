"""
匹配服务 —— 人岗匹配评分算法、差距分析。
"""
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundError
from app.repositories.match_repository import MatchRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.position_repository import PositionRepository


def _skill_tokens(name: str) -> set[str]:
    """技能名拆分为词元集合：按 / 、空格 括号等分隔并转小写，用于模糊匹配"""
    parts = re.split(r"[/、，,（）()\s]+", name.strip())
    return {p.lower() for p in parts if p}


def _has_cjk(s: str) -> bool:
    """判断是否含中文字符"""
    return any("一" <= c <= "鿿" for c in s)


def _skill_names_match(resume_skill: str, position_skill: str) -> bool:
    """
    判断简历技能与岗位技能是否等价（模糊匹配）：
    - 全名相等（忽略大小写）
    - 词元交集：如 "LangChain" ↔ "LangChain / LangGraph"、"RAG" ↔ "RAG 检索增强生成"
    - 中文包含关系：如 "微服务" ↔ "微服务架构"
    """
    a, b = resume_skill.strip().lower(), position_skill.strip().lower()
    if not a or not b:
        return False
    if a == b:
        return True
    if _skill_tokens(resume_skill) & _skill_tokens(position_skill):
        return True
    if _has_cjk(a) or _has_cjk(b):
        return a in b or b in a
    return False


class MatchService:
    """人岗匹配业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.match_repo = MatchRepository(db)
        self.resume_repo = ResumeRepository(db)
        self.position_repo = PositionRepository(db)
        self.db = db

    async def do_match(self, user_id: int, resume_id: int, position_id: int) -> dict:
        """
        执行单次人岗匹配。
        算法：多维度加权评分 + 语义理解 + 图谱推理（当前为基础版实现）。
        """
        # 加载简历和岗位数据
        resume = await self.resume_repo.get_by_id(resume_id)
        position = await self.position_repo.get_by_id(position_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")
        if not position:
            raise ResourceNotFoundError("岗位不存在")

        # 岗位技能存储在独立的 skill 表中，需单独查询（模型上无 ORM 关系）
        skills_map = await self.position_repo.get_skills_for_positions([position_id])
        position_skills = skills_map.get(position_id, [])
        # 技能名 -> 分类 映射，用于差距分析展示
        skill_category = {s["name"]: (s.get("category") or "未分类") for s in position_skills}

        resume_skill_names = [
            s.get("name", "") for s in (resume.skill_list or []) if s.get("name")
        ]
        required_skills = {s["name"] for s in position_skills if s.get("kind") == "required"}
        preferred_skills = {s["name"] for s in position_skills if s.get("kind") == "preferred"}
        all_position_skills = required_skills | preferred_skills

        # 1) 技能匹配评分 (40%) —— 逐个岗位技能与简历技能做模糊匹配
        # [AI] 此处可接入 LLM 对技能进行语义级匹配（如 "懂 Python 数据分析" ↔ "Pandas/NumPy 经验"），当前为规则模糊匹配
        matched = {
            ps for ps in all_position_skills
            if any(_skill_names_match(rs, ps) for rs in resume_skill_names)
        }
        missing = all_position_skills - matched
        required_matched = required_skills & matched
        required_missing = required_skills - matched

        if all_position_skills:
            # 必备技能权重 70%，加分技能权重 30%
            req_ratio = len(required_matched) / len(required_skills) if required_skills else 1.0
            pref_ratio = (
                len(preferred_skills & matched) / len(preferred_skills)
                if preferred_skills else 1.0
            )
            skill_score = min(100, int(req_ratio * 70 + pref_ratio * 30))
        else:
            skill_score = 70

        # 2) 经验匹配评分 (30%) — 基于工作经历数量
        work_count = len(resume.work_experience_list or [])
        exp_score = min(100, 40 + work_count * 20) if work_count > 0 else 30

        # 3) 学历匹配评分 (15%) — 基于教育经历
        edu_count = len(resume.education_list or [])
        edu_score = min(100, 60 + edu_count * 20) if edu_count > 0 else 50

        # 4) 综合素质评分 (15%) — 基于项目经历和自我评价
        proj_count = len(resume.project_list or [])
        has_eval = bool(resume.self_evaluation and len(resume.self_evaluation) > 20)
        quality_score = min(100, proj_count * 25 + (25 if has_eval else 0))

        # 加权总分
        total_score = int(
            skill_score * 0.4 + exp_score * 0.3 + edu_score * 0.15 + quality_score * 0.15
        )

        # 构建差距分析
        gap_analysis = {
            "missing_skills": [
                {"name": s, "level": "required", "category": skill_category.get(s, "未分类")}
                for s in required_missing
            ],
            "weak_skills": [
                {"name": s, "level": "preferred", "category": skill_category.get(s, "未分类")}
                for s in (preferred_skills - matched)
            ],
            "match_skills": [
                {"name": s, "level": "required" if s in required_skills else "preferred",
                 "category": skill_category.get(s, "未分类")}
                for s in matched
            ],
        }

        # 构建维度详情
        # [AI] 此处可接入 LLM 对各维度生成自然语言解读（如 "您的 Python 技能完全满足要求，但缺少 LangChain 框架经验"）
        dimensions = [
            {"name": "技能匹配", "score": skill_score, "weight": 0.4,
             "details": f"匹配 {len(matched)}/{len(all_position_skills)} 项技能，缺失 {len(missing)} 项"},
            {"name": "经验匹配", "score": exp_score, "weight": 0.3,
             "details": f"{work_count} 段工作经历"},
            {"name": "学历匹配", "score": edu_score, "weight": 0.15,
             "details": f"{edu_count} 段教育经历"},
            {"name": "综合素质", "score": quality_score, "weight": 0.15,
             "details": f"{proj_count} 个项目{'，有自我评价' if has_eval else ''}"},
        ]

        # 生成优化建议（基础版规则生成，前端会另行调用 AI 建议接口增强）
        # [AI] 此处可接入 LLM 生成更个性化的优化建议（当前为规则降级，前端调用 /tailor/suggestions 获取 AI 增强版）
        suggestions = []
        for i, skill_name in enumerate(required_missing):
            suggestions.append({
                "id": f"sg-{i+1}",
                "section": "skills",
                "field": "skills",
                "original": "",
                "suggested": f"建议学习并添加技能: {skill_name}",
                "reason": f"该岗位要求掌握 {skill_name}",
                "change_type": "large",
                "accepted": False,
                "verified": True,
                "warning": None,
            })
        for j, skill_name in enumerate(preferred_skills - matched):
            suggestions.append({
                "id": f"sg-p{j+1}",
                "section": "skills",
                "field": "skills",
                "original": "",
                "suggested": f"建议补充加分技能: {skill_name}",
                "reason": f"掌握 {skill_name} 可显著提升该岗位竞争力",
                "change_type": "small",
                "accepted": False,
                "verified": True,
                "warning": None,
            })

        # 保存匹配结果
        match_data = {
            "resume_id": resume_id,
            "position_id": position_id,
            "position_name": position.name,
            "resume_name": resume.name,
            "total_score": total_score,
            "dimensions": dimensions,
            "gap_analysis": gap_analysis,
            "suggestions": suggestions,
            "match_date": datetime.now(),
        }
        result = await self.match_repo.create(user_id, match_data)
        await self.db.commit()

        # 直接从已有数据构建返回结果，避免访问 ORM server_default 列触发懒加载
        return {
            "id": result.id,
            "resume_id": resume_id,
            "position_id": position_id,
            "position_name": position.name,
            "resume_name": resume.name,
            "total_score": total_score,
            "dimensions": dimensions,
            "gap_analysis": gap_analysis,
            "suggestions": suggestions,
            "match_date": str(match_data["match_date"]),
        }

    async def get_result(self, resume_id: int, position_id: int) -> dict:
        """获取已有匹配结果"""
        result = await self.match_repo.get_by_ids(resume_id, position_id)
        if not result:
            raise ResourceNotFoundError("匹配结果不存在，请先执行匹配")
        return self._to_dict(result)

    async def get_history(self, user_id: int) -> list[dict]:
        """获取匹配历史"""
        results = await self.match_repo.get_history(user_id)
        return [self._to_dict(r) for r in results]

    async def batch_match(self, user_id: int, resume_id: int, position_ids: list[int]) -> list[dict]:
        """批量匹配（一份简历 vs 多个岗位）"""
        results = []
        for pid in position_ids:
            result = await self.do_match(user_id, resume_id, pid)
            results.append(result)
        return results

    # [Agent 3] 智能匹配 —— 自动将简历与系统中所有岗位逐一匹配，按分数降序返回
    # [AI] 此处可接入 LLM 对匹配结果进行语义排序和自然语言解读（当前为分数降序排列）
    async def auto_match(self, user_id: int, resume_id: int) -> list[dict]:
        """自动匹配简历与所有岗位，按综合分数降序返回诊断报告列表"""
        all_ids = await self.position_repo.get_all_ids()
        results = await self.batch_match(user_id, resume_id, all_ids)
        results.sort(key=lambda r: r["total_score"], reverse=True)
        return results

    def _to_dict(self, m) -> dict:
        """将 MatchResult 模型转为 API 返回格式"""
        return {
            "id": m.id,
            "resume_id": m.resume_id,
            "position_id": m.position_id,
            "position_name": m.position_name,
            "resume_name": m.resume_name,
            "total_score": m.total_score,
            "dimensions": m.dimensions or [],
            "gap_analysis": m.gap_analysis or {},
            "suggestions": m.suggestions or [],
            "match_date": str(m.match_date) if m.match_date else None,
        }
