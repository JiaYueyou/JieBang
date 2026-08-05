"""收藏与浏览足迹领域服务。"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidParameterError, ResourceNotFoundError
from app.models import JobPosting, MatchRecord, Resume, UserBrowseHistory, UserFavorite
from app.schemas.user_activity import (
    FavoriteResponse,
    HistoryCreateRequest,
    HistoryFocusStat,
    HistoryInsightsResponse,
    HistoryResponse,
)
from app.services.job_service import JobService


class UserActivityService:
    HISTORY_LIMIT = 50

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_favorites(self, user_id: int) -> list[FavoriteResponse]:
        favorites = (
            await self.db.execute(
                select(UserFavorite)
                .where(UserFavorite.user_id == user_id)
                .order_by(UserFavorite.created_at.desc(), UserFavorite.id.desc())
            )
        ).scalars().all()
        job_ids = [item.target_id for item in favorites if item.target_type == "job"]
        resume_ids = [item.target_id for item in favorites if item.target_type == "resume"]
        jobs = {
            row.id: row
            for row in (
                await self.db.execute(
                    select(JobPosting).where(
                        JobPosting.id.in_(job_ids),
                        JobPosting.deleted_at.is_(None),
                    )
                )
            ).scalars().all()
        } if job_ids else {}
        resumes = {
            row.id: row
            for row in (
                await self.db.execute(
                    select(Resume).where(
                        Resume.id.in_(resume_ids),
                        Resume.created_by == user_id,
                        Resume.deleted_at.is_(None),
                    )
                )
            ).scalars().all()
        } if resume_ids else {}
        match_scores = await self._match_scores(user_id)

        result: list[FavoriteResponse] = []
        stale_ids: list[int] = []
        for favorite in favorites:
            if favorite.target_type == "job":
                job = jobs.get(favorite.target_id)
                if not job:
                    stale_ids.append(favorite.id)
                    continue
                result.append(self._job_favorite(favorite, job, match_scores))
            else:
                resume = resumes.get(favorite.target_id)
                if not resume:
                    stale_ids.append(favorite.id)
                    continue
                result.append(self._resume_favorite(favorite, resume, match_scores))
        if stale_ids:
            await self.db.execute(
                delete(UserFavorite).where(UserFavorite.id.in_(stale_ids))
            )
            await self.db.commit()
        return result

    async def toggle_favorite(
        self,
        *,
        user_id: int,
        target_type: str,
        target_id: int,
    ) -> bool:
        await self._validate_target(user_id, target_type, target_id)
        current = (
            await self.db.execute(
                select(UserFavorite).where(
                    UserFavorite.user_id == user_id,
                    UserFavorite.target_type == target_type,
                    UserFavorite.target_id == target_id,
                )
            )
        ).scalar_one_or_none()
        if current:
            await self.db.delete(current)
            await self.db.commit()
            return False
        self.db.add(
            UserFavorite(
                user_id=user_id,
                target_type=target_type,
                target_id=target_id,
            )
        )
        await self.db.commit()
        return True

    async def remove_favorites(self, user_id: int, ids: list[int]) -> int:
        result = await self.db.execute(
            delete(UserFavorite).where(
                UserFavorite.user_id == user_id,
                UserFavorite.id.in_(ids),
            )
        )
        await self.db.commit()
        return result.rowcount or 0

    async def update_favorite_note(self, user_id: int, favorite_id: int, note: str) -> None:
        favorite = (
            await self.db.execute(
                select(UserFavorite).where(
                    UserFavorite.id == favorite_id,
                    UserFavorite.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if not favorite:
            raise ResourceNotFoundError("收藏记录不存在")
        favorite.note = note.strip()
        await self.db.commit()

    async def record_history(
        self,
        user_id: int,
        payload: HistoryCreateRequest,
    ) -> HistoryResponse:
        now = datetime.now()
        target_id = str(payload.targetId) if payload.targetId is not None else None
        target_key = f"{payload.type}:{target_id or payload.url}"
        record = (
            await self.db.execute(
                select(UserBrowseHistory).where(
                    UserBrowseHistory.user_id == user_id,
                    UserBrowseHistory.event_type == payload.type,
                    UserBrowseHistory.target_key == target_key,
                )
            )
        ).scalar_one_or_none()
        if record:
            record.title = payload.title.strip()
            record.description = payload.description.strip()
            record.source = payload.source.strip() or "智联职引"
            record.url = payload.url
            record.tags = list(dict.fromkeys(payload.tags))
            record.visit_count += 1
            record.last_viewed_at = now
        else:
            record = UserBrowseHistory(
                user_id=user_id,
                event_type=payload.type,
                target_key=target_key,
                target_id=target_id,
                title=payload.title.strip(),
                description=payload.description.strip(),
                source=payload.source.strip() or "智联职引",
                url=payload.url,
                tags=list(dict.fromkeys(payload.tags)),
                visit_count=1,
                first_viewed_at=now,
                last_viewed_at=now,
            )
            self.db.add(record)
        await self.db.flush()
        await self._trim_history(user_id)
        await self.db.commit()
        await self.db.refresh(record)
        return self._history_response(record, now=now)

    async def list_history(self, user_id: int) -> list[HistoryResponse]:
        now = datetime.now()
        records = (
            await self.db.execute(
                select(UserBrowseHistory)
                .where(UserBrowseHistory.user_id == user_id)
                .order_by(
                    UserBrowseHistory.last_viewed_at.desc(),
                    UserBrowseHistory.id.desc(),
                )
                .limit(self.HISTORY_LIMIT)
            )
        ).scalars().all()
        return [self._history_response(item, now=now) for item in records]

    async def remove_history(self, user_id: int, history_id: int) -> None:
        result = await self.db.execute(
            delete(UserBrowseHistory).where(
                UserBrowseHistory.user_id == user_id,
                UserBrowseHistory.id == history_id,
            )
        )
        if not result.rowcount:
            raise ResourceNotFoundError("浏览记录不存在")
        await self.db.commit()

    async def clear_history(self, user_id: int) -> int:
        result = await self.db.execute(
            delete(UserBrowseHistory).where(UserBrowseHistory.user_id == user_id)
        )
        await self.db.commit()
        return result.rowcount or 0

    async def history_insights(self, user_id: int) -> HistoryInsightsResponse:
        rows = (
            await self.db.execute(
                select(UserBrowseHistory).where(UserBrowseHistory.user_id == user_id)
            )
        ).scalars().all()
        total_visits = sum(item.visit_count for item in rows)
        labels = {
            "job": "岗位",
            "resume": "候选人",
            "search": "搜索",
            "graph": "技能图谱",
            "match": "匹配报告",
        }
        counts = Counter()
        for row in rows:
            counts[row.event_type] += row.visit_count
        focus = [
            HistoryFocusStat(
                label=labels[event_type],
                count=count,
                percent=round(count * 100 / total_visits) if total_visits else 0,
            )
            for event_type, count in counts.most_common()
        ]
        frequent = [
            {"history_id": item.id, "count": item.visit_count}
            for item in sorted(
                rows,
                key=lambda row: (row.visit_count, row.last_viewed_at),
                reverse=True,
            )[:5]
            if item.visit_count > 1
        ]
        return HistoryInsightsResponse(
            focusStats=focus,
            frequentRecords=frequent,
        )

    async def _validate_target(self, user_id: int, target_type: str, target_id: int) -> None:
        if target_type == "job":
            target = (
                await self.db.execute(
                    select(JobPosting.id).where(
                        JobPosting.id == target_id,
                        JobPosting.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
        elif target_type == "resume":
            target = (
                await self.db.execute(
                    select(Resume.id).where(
                        Resume.id == target_id,
                        Resume.created_by == user_id,
                        Resume.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
        else:
            raise InvalidParameterError("不支持的收藏类型")
        if target is None:
            raise ResourceNotFoundError("收藏目标不存在或无权访问")

    async def _match_scores(self, user_id: int) -> dict[tuple[str, int], int]:
        rows = (
            await self.db.execute(
                select(MatchRecord).where(MatchRecord.created_by == user_id)
            )
        ).scalars().all()
        scores: dict[tuple[str, int], int] = {}
        for row in rows:
            scores[("job", row.job_id)] = max(
                row.score,
                scores.get(("job", row.job_id), 0),
            )
            scores[("resume", row.resume_id)] = max(
                row.score,
                scores.get(("resume", row.resume_id), 0),
            )
        return scores

    @staticmethod
    def _job_favorite(
        favorite: UserFavorite,
        job: JobPosting,
        match_scores: dict[tuple[str, int], int],
    ) -> FavoriteResponse:
        saved_at = favorite.created_at
        return FavoriteResponse(
            id=favorite.id,
            target_type="job",
            target_id=job.id,
            title=job.title,
            subtitle=f"{job.department} · {job.level}",
            company=job.company or job.department,
            location=job.location or "地点待确认",
            salary=JobService._salary_range(job) or "薪资待确认",
            experience=job.experience or "经验不限",
            education=job.education or "学历不限",
            skills=[skill.name for skill in job.skills],
            match=match_scores.get(("job", job.id), 0),
            savedAt=saved_at,
            savedOrder=int(saved_at.timestamp()),
            note=favorite.note,
            urgent=job.urgent,
        )

    @staticmethod
    def _resume_favorite(
        favorite: UserFavorite,
        resume: Resume,
        match_scores: dict[tuple[str, int], int],
    ) -> FavoriteResponse:
        saved_at = favorite.created_at
        return FavoriteResponse(
            id=favorite.id,
            target_type="resume",
            target_id=resume.id,
            title=resume.name,
            subtitle=resume.current_position or "候选人",
            company=resume.company or resume.department or "",
            location=resume.location or "地点待确认",
            salary="",
            experience=resume.experience or "经验待确认",
            education=resume.education or "学历待确认",
            skills=[skill.name for skill in resume.skills],
            match=match_scores.get(("resume", resume.id), 0),
            savedAt=saved_at,
            savedOrder=int(saved_at.timestamp()),
            note=favorite.note,
        )

    @staticmethod
    def _history_response(
        record: UserBrowseHistory,
        *,
        now: datetime,
    ) -> HistoryResponse:
        viewed_at = record.last_viewed_at
        day_gap = (now.date() - viewed_at.date()).days
        if day_gap <= 0:
            date_key = "today"
        elif day_gap == 1:
            date_key = "yesterday"
        elif viewed_at >= now - timedelta(days=7):
            date_key = "week"
        else:
            date_key = "month"
        target: int | str | None = record.target_id
        if record.target_id and record.target_id.isdigit():
            target = int(record.target_id)
        badge = f"浏览 {record.visit_count} 次" if record.visit_count > 1 else None
        return HistoryResponse(
            id=record.id,
            type=record.event_type,
            targetId=target,
            title=record.title,
            description=record.description,
            source=record.source,
            dateKey=date_key,
            date=viewed_at.strftime("%Y-%m-%d"),
            time=viewed_at.strftime("%H:%M"),
            tags=record.tags or [],
            url=record.url,
            badge=badge,
        )

    async def _trim_history(self, user_id: int) -> None:
        stale_ids = (
            await self.db.execute(
                select(UserBrowseHistory.id)
                .where(UserBrowseHistory.user_id == user_id)
                .order_by(
                    UserBrowseHistory.last_viewed_at.desc(),
                    UserBrowseHistory.id.desc(),
                )
                .offset(self.HISTORY_LIMIT)
            )
        ).scalars().all()
        if stale_ids:
            await self.db.execute(
                delete(UserBrowseHistory).where(UserBrowseHistory.id.in_(stale_ids))
            )
