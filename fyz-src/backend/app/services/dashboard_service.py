from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    JobPosting,
    JobSkillFact,
    MatchRecord,
    RawJobRecord,
    Resume,
    Skill,
    SourceDocument,
    StandardJob,
    StandardJobSource,
)


class DashboardService:
    """Build the management dashboard exclusively from persisted business data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def overview(
        self,
        *,
        user_id: int,
        hot_jobs_page: int = 1,
        hot_jobs_page_size: int = 10,
        emerging_page: int = 1,
        emerging_page_size: int = 10,
    ) -> dict:
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
        hot_jobs = await self._hot_jobs()
        hot_jobs_total = len(hot_jobs)
        hot_jobs = hot_jobs[
            (hot_jobs_page - 1) * hot_jobs_page_size :
            (hot_jobs_page - 1) * hot_jobs_page_size + hot_jobs_page_size
        ]
        emerging_skills = self._emerging_skills(verified_facts, month_start)
        emerging_skills_total = len(emerging_skills)
        emerging_skills = emerging_skills[
            (emerging_page - 1) * emerging_page_size :
            (emerging_page - 1) * emerging_page_size + emerging_page_size
        ]

        return {
            "heroCards": hero_cards,
            "kanban": kanban[:20],
            "highMatches": high_match_talents[:20],
            "hotJobs": hot_jobs,
            "hotJobsTotal": hot_jobs_total,
            "emergingSkills": emerging_skills,
            "emergingSkillsTotal": emerging_skills_total,
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

    async def _hot_jobs(self) -> list[dict]:
        """热门岗位：基于爬取数据（RawJobRecord）经标准岗位聚合，按独立来源数排序。

        数据源为质量达标、未排除的爬取岗位记录，按 StandardJobSource 映射
        聚合到标准岗位；demand=独立来源数，spark=近 6 个月来源数，
        trend=最近一个月来源数差，core_skills=该岗位已确认事实 Top 技能。
        """
        rows = list((await self.db.execute(
            select(RawJobRecord, StandardJobSource.standard_job_id, SourceDocument)
            .join(
                StandardJobSource,
                (StandardJobSource.source_type == "raw")
                & (StandardJobSource.source_id == RawJobRecord.id),
            )
            .join(SourceDocument, SourceDocument.id == RawJobRecord.source_document_id)
            .where(
                RawJobRecord.quality_status.in_(("accepted", "warning")),
                RawJobRecord.is_excluded.is_(False),
                RawJobRecord.standard_job_id.is_not(None),
            )
        )).all())
        if not rows:
            return []

        now = datetime.utcnow()
        month_keys: list[tuple[int, int]] = []
        for offset in range(5, -1, -1):
            absolute_month = now.year * 12 + now.month - 1 - offset
            month_keys.append((absolute_month // 12, absolute_month % 12 + 1))
        month_index = {key: index for index, key in enumerate(month_keys)}

        grouped: dict[int, dict] = {}
        raw_ids: set[int] = set()
        for raw, standard_job_id, document in rows:
            item = grouped.setdefault(standard_job_id, {
                "standard_job_id": standard_job_id,
                "title": "",
                "demand": 0,
                "city": "",
                "city_counts": Counter(),
                "spark": [0] * 6,
                "raw_ids": [],
                "evidence_clusters": set(),
                "periods": set(),
            })
            item["demand"] += 1
            item["raw_ids"].append(raw.id)
            raw_ids.add(raw.id)
            if raw.city:
                item["city_counts"][raw.city] += 1
            observed = raw.posted_at or raw.crawled_at or raw.created_at
            if observed is not None:
                key = (observed.year, observed.month)
                month = observed.strftime("%Y-%m")
                company = (
                    raw.company_key or raw.company or document.company or "unknown"
                ).strip().casefold()
                location = raw.city_code or raw.city or "unknown"
                item["periods"].add(month)
                item["evidence_clusters"].add(
                    (standard_job_id, company, location, month)
                )
                if key in month_index:
                    item["spark"][month_index[key]] += 1

        standard_rows = list((await self.db.execute(
            select(StandardJob).where(StandardJob.id.in_(grouped.keys()))
        )).scalars())
        standard_names = {standard.id: standard.name for standard in standard_rows}

        skills_by_raw: dict[int, list[str]] = defaultdict(list)
        if raw_ids:
            facts = list((await self.db.execute(
                select(JobSkillFact, Skill)
                .join(Skill, Skill.id == JobSkillFact.skill_id)
                .where(
                    JobSkillFact.raw_job_record_id.in_(raw_ids),
                    JobSkillFact.verification_status == "verified",
                )
            )).all())
            for fact, skill in facts:
                if fact.raw_job_record_id:
                    skills_by_raw[fact.raw_job_record_id].append(skill.name)

        result: list[dict] = []
        for standard_job_id, item in grouped.items():
            skill_counts = Counter(
                skill_name
                for raw_id in item["raw_ids"]
                for skill_name in skills_by_raw.get(raw_id, [])
            )
            spark = item["spark"]
            cluster_count = len(item["evidence_clusters"])
            period_count = len(item["periods"])
            lifecycle_stage = (
                "mature"
                if cluster_count >= 5 and period_count >= 3
                else "established"
                if cluster_count >= 3 and period_count >= 2
                else "observed"
            )
            result.append({
                "standard_job_id": standard_job_id,
                "title": standard_names.get(standard_job_id) or f"标准岗位 #{standard_job_id}",
                "demand": item["demand"],
                "city": (
                    item["city_counts"].most_common(1)[0][0]
                    if item["city_counts"]
                    else "全国"
                ),
                "trend": spark[-1] - spark[-2],
                "spark": spark,
                "core_skills": [name for name, _ in skill_counts.most_common(5)],
                "lifecycle_stage": lifecycle_stage,
                "active_period_count": period_count,
            })
        return sorted(
            result,
            key=lambda item: (-item["demand"], -item["trend"], item["standard_job_id"]),
        )

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
