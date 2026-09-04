from pathlib import Path

from app.core.database import async_session
from app.services.analysis_service import AnalysisService
from app.services.import_service import ImportService


async def test_competition_data_shows_new_job_and_existing_job_capability_update(
    monkeypatch,
):
    repository_root = Path(__file__).resolve().parents[4]
    monkeypatch.setattr(
        "app.services.import_service.DATA_DIR",
        str(repository_root / "data"),
    )
    async with async_session() as db:
        service = ImportService(db)

        baseline = await service.import_files(
            ["competition-test/01_existing_job_baseline.json"]
        )
        scenario = await service.import_files(
            ["competition-test/02_new_job_and_existing_update_v2.json"]
        )

        assert baseline["imported"] == 2
        assert scenario["imported"] == 4
        assert baseline["validation"][0]["failed"] == 0
        assert scenario["validation"][0]["failed"] == 0
        assert scenario["verified_skill_facts"] > 0

        insights = await AnalysisService(db).job_insights(
            skill=None,
            limit=100,
            user_id=1,
        )
        new_job = next(
            item for item in insights.emerging_jobs if "大模型安全工程师" in item.name
        )
        assert new_job.source_count == 2
        assert {"Python", "机器学习", "大模型"}.issubset(set(new_job.core_skills))

        change = next(
            item for item in insights.capability_changes if "AI应用开发工程师" in item.job
        )
        assert {"RAG", "LangChain"}.issubset(set(change.added))
        assert "Python" not in change.weakened + change.removed
        assert "FastAPI" not in change.weakened + change.removed
        assert change.removed == []
        assert change.previous_sample_count == 2
        assert change.current_sample_count == 2
