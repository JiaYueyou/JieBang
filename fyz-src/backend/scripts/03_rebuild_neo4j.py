"""Step 3: rebuild the JieBang Neo4j read model from imported MySQL facts."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import async_session, engine  # noqa: E402
from app.core.neo4j import close_driver, health_detail  # noqa: E402
from app.services.graph_service import GraphService  # noqa: E402


async def rebuild() -> None:
    try:
        detail = await asyncio.to_thread(health_detail)
        if not detail.startswith("OK"):
            raise RuntimeError(
                f"Neo4j is unavailable: {detail}. Check NEO4J_URI/USER/PASSWORD in .env."
            )
        print(f"[3/4] {detail}")
        print("[3/4] Rebuilding only the Neo4j namespace 'jiebang' from MySQL facts...")
        async with async_session() as session:
            result = await GraphService(session).sync(
                mode="full",
                enrich_top_skills=False,
                user_id=None,
            )
        print(f"[3/4] Neo4j rebuild succeeded: {result}")
    finally:
        close_driver()
        await engine.dispose()


def main() -> None:
    asyncio.run(rebuild())


if __name__ == "__main__":
    main()
