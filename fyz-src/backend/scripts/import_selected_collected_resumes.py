"""Import the top locally evaluated resumes into the persistent talent pool."""

from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import async_session, engine  # noqa: E402
from app.models import Resume, User  # noqa: E402
from app.services.matching_service import MatchingService  # noqa: E402


async def import_selected(private_input: Path, public_output: Path) -> dict[str, Any]:
    payload = json.loads(private_input.read_text(encoding="utf-8"))
    selected_ids = set(payload["selected_ids"])
    selected = [row for row in payload["records"] if row["id"] in selected_ids]
    if len(selected) != 15:
        raise RuntimeError(f"Expected 15 selected resumes, found {len(selected)}")
    imported: list[dict[str, Any]] = []
    refreshed: list[dict[str, Any]] = []
    async with async_session() as db:
        owner = await db.scalar(
            select(User).order_by((User.role == "admin").desc(), User.id)
        )
        if owner is None:
            raise RuntimeError("No database user exists to own the talent records")
        service = MatchingService(db)
        for row in selected:
            duplicate = await db.scalar(
                select(Resume).options(selectinload(Resume.parse_result)).where(
                    Resume.created_by == owner.id,
                    Resume.content_hash == row["content_hash"],
                    Resume.deleted_at.is_(None),
                )
            )
            if duplicate is not None:
                profile = service.profile_extractor.extract(row["text"])
                duplicate.current_position = duplicate.current_position or profile["current_position"]
                duplicate.experience = duplicate.experience or profile["experience"]
                duplicate.education = duplicate.education or profile["education"]
                duplicate.parse_result.profile = profile
                duplicate.name = profile["name"] or "姓名待补充"
                await db.commit()
                refreshed.append({
                    "source_id": row["id"],
                    "pseudonym": row["pseudonym"],
                    "resume_id": duplicate.id,
                    "reason": "existing_record_refreshed",
                })
                continue
            image_path = Path(row["image_path"])
            filename = f"talent-source-{row['id']}{image_path.suffix.lower()}"
            result = await service.create_resume(
                content=image_path.read_bytes(),
                filename=filename,
                content_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
                user_id=owner.id,
                name=row["profile"].get("name") or row["pseudonym"],
                current_position=row["profile"].get("current_position"),
                experience=row["profile"].get("experience"),
                education=row["profile"].get("education"),
                preparsed_text=row["text"],
                parse_warnings=["批量入库复用了本地双通道 OCR 评测结果。"],
            )
            imported.append({
                "source_id": row["id"],
                "pseudonym": row["pseudonym"],
                "resume_id": result.id,
                "skill_count": len(result.skills),
                "match_count": len(result.matches),
            })
    report = {
        "owner_user_id": owner.id,
        "requested": 15,
        "imported": len(imported),
        "existing_refreshed": len(refreshed),
        "active": len(imported) + len(refreshed),
        "active_resume_ids": [row["resume_id"] for row in [*imported, *refreshed]],
        "records": imported,
        "refreshed_records": refreshed,
        "privacy": "Only pseudonyms and database IDs are included; personal fields remain in the protected database.",
    }
    public_output.parent.mkdir(parents=True, exist_ok=True)
    public_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--private-input",
        type=Path,
        default=PROJECT_DIR / "tmp" / "collected_resume_evaluation" / "ocr_private.json",
    )
    parser.add_argument(
        "--public-output",
        type=Path,
        default=BACKEND_DIR / "evaluation" / "collected_resume_import_report.json",
    )
    args = parser.parse_args()
    async def run_and_dispose() -> dict[str, Any]:
        try:
            return await import_selected(args.private_input, args.public_output)
        finally:
            await engine.dispose()

    report = asyncio.run(run_and_dispose())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
