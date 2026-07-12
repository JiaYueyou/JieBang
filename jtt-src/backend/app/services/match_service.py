"""
匹配服务 —— 人岗匹配评分算法、差距分析。
"""
import json
import math
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundError
from app.repositories.match_repository import MatchRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.position_repository import PositionRepository
from app.providers.llm import get_llm_provider


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

        resume_skills = set(s.get("name", "") for s in (resume.skill_list or []))
        required_skills = {s.name for s in (position.required_skills or [])}
        preferred_skills = {s.name for s in (position.preferred_skills or [])}
        all_position_skills = required_skills | preferred_skills

        # 1) 技能匹配评分 (40%)
        matched = resume_skills & all_position_skills
        missing = all_position_skills - resume_skills
        required_matched = resume_skills & required_skills
        required_missing = required_skills - resume_skills

        if all_position_skills:
            skill_score = min(100, int((len(matched) / len(all_position_skills)) * 100))
        else:
            skill_score = 70

        # 2) 经验匹配评分 (30%) — 基于工作经历数量和技能匹配度
        work_count = len(resume.work_experience_list or [])
        exp_score = min(100, work_count * 25) if work_count > 0 else 40

        # 3) 学历匹配评分 (15%) — 基于教育经历
        edu_count = len(resume.education_list or [])
        edu_score = min(100, 60 + edu_count * 20) if edu_count > 0 else 50

        # 4) 综合素质评分 (15%) — 基于项目经历和自我评价
        proj_count = len(resume.project_list or [])
        has_eval = bool(resume.self_evaluation and len(resume.self_evaluation) > 20)
        quality_score = min(100, proj_count * 20 + (20 if has_eval else 0))

        # 加权总分
        total_score = int(
            skill_score * 0.4 + exp_score * 0.3 + edu_score * 0.15 + quality_score * 0.15
        )

        # 构建差距分析
        gap_analysis = {
            "missingSkills": [
                {"name": s, "level": "required", "category": "未知"}
                for s in required_missing
            ],
            "weakSkills": [
                {"name": s, "level": "preferred", "category": "未知"}
                for s in (preferred_skills - resume_skills)
            ],
            "matchSkills": [
                {"name": s, "level": "required", "category": "未知"}
                for s in matched
            ],
        }

        # 构建维度详情
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

        # 生成优化建议（基础版规则生成，后续可由 AI 增强）
        suggestions = []
        for i, skill_name in enumerate(required_missing):
            suggestions.append({
                "id": f"sg-{i+1}",
                "section": "skills",
                "field": "skills",
                "original": "",
                "suggested": f"建议学习并添加技能: {skill_name}",
                "reason": f"该岗位要求掌握 {skill_name}",
                "changeType": "large",
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
        }
        result = await self.match_repo.create(user_id, match_data)
        await self.db.commit()

        return self._to_dict(result)

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
            # 每次匹配前需要从 DB 重新获取 session 中的对象
            result = await self.do_match(user_id, resume_id, pid)
            results.append(result)
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
