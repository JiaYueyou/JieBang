"""Rebuild the Phase 2 evidence index from authoritative MySQL facts."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import async_session, engine
from app.core.config import RETRIEVAL_VECTOR_BACKEND
from app.models import User
from app.services.retrieval_service import RetrievalService


async def rebuild(*, backend: str) -> dict:
    async with async_session() as session:
        admin_id = await session.scalar(
            select(User.id).where(User.role == "admin").order_by(User.id)
        )
        if admin_id is None:
            raise RuntimeError("No administrator exists to own the index build")
        result = await RetrievalService(session).rebuild_index(
            created_by=admin_id,
            backend=backend,
        )
        return result.model_dump(mode="json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backend",
        choices=("local_hash", "neo4j_vector", "chroma"),
        default=RETRIEVAL_VECTOR_BACKEND,
    )
    args = parser.parse_args()

    async def run() -> dict:
        try:
            return await rebuild(backend=args.backend)
        finally:
            await engine.dispose()

    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
