"""Read-only Agent run audit queries."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models import AgentRun
from app.schemas.agent import AgentRunResponse


class AgentRunService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self, run_id: str, *, user_id: int, allow_all: bool = False
    ) -> AgentRunResponse:
        run = await self.db.get(AgentRun, run_id)
        if run is None or (not allow_all and run.created_by != user_id):
            raise ResourceNotFoundError("Agent 运行记录不存在")
        return self.to_response(run)

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        agent_type: str | None = None,
        status: str | None = None,
        created_by: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[AgentRunResponse], int]:
        filters = []
        if agent_type:
            filters.append(AgentRun.agent_type == agent_type)
        if status:
            filters.append(AgentRun.status == status)
        if created_by is not None:
            filters.append(AgentRun.created_by == created_by)
        if created_from is not None:
            filters.append(AgentRun.created_at >= created_from)
        if created_to is not None:
            filters.append(AgentRun.created_at <= created_to)

        total = int(
            await self.db.scalar(
                select(func.count()).select_from(AgentRun).where(*filters)
            )
            or 0
        )
        rows = list(
            (
                await self.db.execute(
                    select(AgentRun)
                    .where(*filters)
                    .order_by(AgentRun.created_at.desc(), AgentRun.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).scalars()
        )
        return [self.to_response(row) for row in rows], total

    @staticmethod
    def to_response(run: AgentRun) -> AgentRunResponse:
        return AgentRunResponse(
            id=run.id,
            agent_type=run.agent_type,
            provider=run.provider,
            model=run.model,
            prompt_version=run.prompt_version,
            input_summary=run.input_summary,
            structured_output=run.structured_output,
            status=run.status,
            duration_ms=run.duration_ms,
            prompt_tokens=run.prompt_tokens,
            completion_tokens=run.completion_tokens,
            retry_count=run.retry_count,
            error_code=run.error_code,
            error_message=run.error_message,
            created_by=run.created_by,
            created_at=run.created_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
