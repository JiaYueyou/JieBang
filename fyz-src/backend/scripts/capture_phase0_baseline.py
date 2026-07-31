"""Capture a read-only Phase 0 runtime baseline."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import async_session, engine
from app.core.neo4j import close_driver
from app.evaluation.phase0_baseline import (
    build_report,
    collect_git_metadata,
    collect_neo4j_baseline,
    collect_relational_baseline,
    render_markdown,
)


async def capture() -> dict:
    try:
        async with async_session() as session:
            relational = await collect_relational_baseline(session)
        neo4j = await asyncio.to_thread(collect_neo4j_baseline)
        return build_report(
            git=collect_git_metadata(PROJECT_ROOT),
            relational=relational,
            neo4j=neo4j,
        )
    finally:
        await asyncio.to_thread(close_driver)
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "docs" / "dev-prompt-tmp" / "phase0-runtime",
    )
    args = parser.parse_args()
    report = asyncio.run(capture())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = (
        report["generated_at"]
        .replace("-", "")
        .replace(":", "")
        .replace(".", "")
    )
    json_path = args.output_dir / f"phase0-baseline-{stamp}.json"
    markdown_path = args.output_dir / f"phase0-baseline-{stamp}.md"
    json_payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    markdown_payload = render_markdown(report)
    json_path.write_text(json_payload, encoding="utf-8")
    markdown_path.write_text(markdown_payload, encoding="utf-8")
    (args.output_dir / "latest.json").write_text(json_payload, encoding="utf-8")
    (args.output_dir / "latest.md").write_text(markdown_payload, encoding="utf-8")
    print(json.dumps({
        "json": str(json_path),
        "markdown": str(markdown_path),
        "neo4j_connected": report["neo4j"]["connected"],
        "vector_supported": report["neo4j"]["vector"]["supported"],
        "rag_backend": report["rag_decision"]["selected_phase1_backend"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
