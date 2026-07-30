from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobPosting, JobSkillFact, MatchRecord, Resume, Skill


class DashboardService:
    """Build the management dashboard exclusively from persisted business data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def overview(self, *, user_id: int) -> dict:
        now = datetime.utcnow()
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)

        jobs = list(
            (
                await self.db.execute(
                    select(JobPosting)
                    .where(JobPosting.deleted_at.is_(None))
                    .order_by(JobPosting.created_at.desc(), JobPosting.id.desc())
                )
            ).scalars()
        )
        resumes = list(
            (
                await self.db.execute(
                    select(Resume)
                    .where(
                        Resume.created_by == user_id,
                        Resume.deleted_at.is_(None),
                        Resume.status == "active",
                    )
                    .order_by(Resume.created_at.desc(), Resume.id.desc())
                )
            ).scalars()
        )
        match_rows = list(
            (
                await self.db.execute(
                    select(MatchRecord)
                    .join(Resume, Resume.id == MatchRecord.resume_id)
                    .join(JobPosting, JobPosting.id == MatchRecord.job_id)
                    .where(
                        Resume.created_by == user_id,
                        Resume.deleted_at.is_(None),
                        Resume.status == "active",
                        MatchRecord.status == "active",
                        JobPosting.deleted_at.is_(None),
                        JobPosting.status == "open",
                    )
                    .order_by(
                        MatchRecord.updated_at.desc(),
                        MatchRecord.created_at.desc(),
                        MatchRecord.id.desc(),
                    )
                )
            ).scalars()
        )
        latest_matches: dict[tuple[int, int], MatchRecord] = {}
        for match in match_rows:
            latest_matches.setdefault((match.job_id, match.resume_id), match)
        matches = list(latest_matches.values())
        verified_facts = list(
            (
                await self.db.execute(
                    select(JobSkillFact, Skill)
                    .join(Skill, Skill.id == JobSkillFact.skill_id)
                    .where(JobSkillFact.verification_status == "verified")
                )
            ).all()
        )

        open_jobs = [job for job in jobs if job.status == "open"]
        high_matches = [match for match in matches if match.score >= 80]
        high_match_resume_ids = {match.resume_id for match in high_matches}
        recent_high_match_resume_ids = {
            match.resume_id
            for match in high_matches
            if match.created_at >= month_start
        }
        hero_cards = [
            {
                "value": str(len(open_jobs)),
                "label": "在招岗位",
                "change": f"本周 +{sum(job.created_at >= week_start for job in jobs)}",
                "up": True,
                "color": "brand",
                "action": "管理岗位",
                "link": "/jobs",
            },
            {
                "value": str(len(resumes)),
                "label": "人才档案",
                "change": f"本周 +{sum(resume.created_at >= week_start for resume in resumes)}",
                "up": True,
                "color": "green",
                "action": "查看人才",
                "link": "/matching",
            },
            {
                "value": str(len(high_match_resume_ids)),
                "label": "高匹配人才",
                "change": f"近30天 +{len(recent_high_match_resume_ids)}",
                "up": True,
                "color": "amber",
                "action": "处理匹配",
                "link": "/matching",
            },
            {
                "value": str(len(verified_facts)),
                "label": "已确认技能事实",
                "change": f"本周 +{sum(fact.updated_at >= week_start for fact, _ in verified_facts)}",
                "up": True,
                "color": "rose",
                "action": "查看事实",
                "link": "/admin",
            },
        ]

        matches_by_job: dict[int, list[MatchRecord]] = defaultdict(list)
        matches_by_resume: dict[int, list[MatchRecord]] = defaultdict(list)
        for match in matches:
            matches_by_job[match.job_id].append(match)
            matches_by_resume[match.resume_id].append(match)

        kanban = []
        talent_pool_size = len(resumes)
        for job in open_jobs:
            job_matches = matches_by_job[job.id]
            evaluated_resume_ids = {match.resume_id for match in job_matches}
            pending_count = max(talent_pool_size - len(evaluated_resume_ids), 0)
            kanban.append(
                {
                    "job_id": job.id,
                    "title": job.title,
                    "department": job.department,
                    "location": job.location or "地点待确认",
                    "headcount": max(job.headcount, 1),
                    "urgent": job.urgent,
                    "skills": [skill.name for skill in job.skills[:5]],
                    "total": talent_pool_size,
                    "evaluated": len(evaluated_resume_ids),
                    "pending": pending_count,
                    "coverage": (
                        round(len(evaluated_resume_ids) / talent_pool_size * 100)
                        if talent_pool_size
                        else 0
                    ),
                    "stages": [
                        {
                            "name": "高匹配",
                            "kind": "high",
                            "count": sum(match.score >= 80 for match in job_matches),
                        },
                        {
                            "name": "可推进",
                            "kind": "progress",
                            "count": sum(60 <= match.score < 80 for match in job_matches),
                        },
                        {
                            "name": "待补强",
                            "kind": "gap",
                            "count": sum(match.score < 60 for match in job_matches),
                        },
                        {
                            "name": "待评估",
                            "kind": "pending",
                            "count": pending_count,
                        },
                    ],
                }
            )
        kanban.sort(
            key=lambda item: (
                -int(item["urgent"]),
                -item["pending"],
                -item["evaluated"],
                item["job_id"],
            )
        )

        high_match_talents = self._talent_summaries(resumes, matches_by_resume)
        hot_jobs = self._hot_jobs(open_jobs, matches_by_job, now)
        emerging_skills = self._emerging_skills(verified_facts, month_start)

        return {
            "heroCards": hero_cards,
            "kanban": kanban[:20],
            "highMatches": high_match_talents[:20],
            "hotJobs": hot_jobs[:12],
            "emergingSkills": emerging_skills[:20],
        }

    @staticmethod
    def _talent_summaries(
        resumes: list[Resume],
        matches_by_resume: dict[int, list[MatchRecord]],
    ) -> list[dict]:
        result: list[dict] = []
        for resume in resumes:
            active_matches = sorted(
                matches_by_resume.get(resume.id, []),
                key=lambda item: (-item.score, item.job_id),
            )
            if not active_matches:
                continue
            best = active_matches[0]
            result.append(
                {
                    "id": resume.id,
                    "resume_id": resume.id,
                    "match_id": best.id,
                    "name": resume.name,
                    "position": resume.current_position or "待确认",
                    "score": best.score,
                    "isNew": (datetime.utcnow() - resume.created_at).days <= 7,
                    "experience": resume.experience or "待确认",
                    "education": resume.education or "待确认",
                    "department": resume.department or "待确认",
                    "matched": best.matched_skills,
                    "missing": best.missing_skills,
                    "targetJobs": [match.job.title for match in active_matches],
                    "targetJobIds": [match.job_id for match in active_matches],
                    "resumeFile": resume.original_filename,
                    "uploadDate": resume.created_at.date().isoformat(),
                    "urgent": best.job.urgent,
                    "company": resume.company or "",
                    "location": resume.location or "",
                }
            )
        return sorted(result, key=lambda item: (-item["score"], item["id"]))

    @staticmethod
    def _hot_jobs(
        jobs: list[JobPosting],
        matches_by_job: dict[int, list[MatchRecord]],
        now: datetime,
    ) -> list[dict]:
        month_keys: list[tuple[int, int]] = []
        year, month = now.year, now.month
        for offset in range(5, -1, -1):
            absolute_month = year * 12 + month - 1 - offset
            month_keys.append((absolute_month // 12, absolute_month % 12 + 1))

        result = []
        for job in jobs:
            job_matches = matches_by_job[job.id]
            monthly = defaultdict(int)
            for match in job_matches:
                monthly[(match.created_at.year, match.created_at.month)] += 1
            spark = [monthly[key] for key in month_keys]
            result.append(
                {
                    "job_id": job.id,
                    "title": job.title,
                    "demand": len(job_matches),
                    "city": job.location or "待确认",
                    "trend": spark[-1] - spark[-2],
                    "spark": spark,
                }
            )
        return sorted(result, key=lambda item: (-item["demand"], item["job_id"]))

    @staticmethod
    def _emerging_skills(
        verified_facts: list[tuple[JobSkillFact, Skill]],
        month_start: datetime,
    ) -> list[dict]:
        grouped: dict[int, dict] = {}
        for fact, skill in verified_facts:
            item = grouped.setdefault(
                skill.id,
                {
                    "id": skill.id,
                    "name": skill.canonical_name,
                    "category": skill.category,
                    "fact_count": 0,
                    "source_count": 0,
                    "recent_count": 0,
                    "confidence_total": 0.0,
                },
            )
            item["fact_count"] += 1
            item["source_count"] += fact.source_count
            item["recent_count"] += int(fact.updated_at >= month_start)
            item["confidence_total"] += fact.confidence

        result = []
        for item in grouped.values():
            result.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "combo": (
                        f'{item["category"]} · {item["fact_count"]} 条事实'
                        f' · {item["source_count"]} 条来源'
                    ),
                    "growth": item["recent_count"],
                    "confidence": round(item["confidence_total"] / item["fact_count"] * 100),
                }
            )
        return sorted(
            result,
            key=lambda item: (-item["growth"], -item["confidence"], item["name"]),
        )
