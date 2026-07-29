"""批量 JD 导入幂等与交叉验证测试。"""

import json
import tempfile
from pathlib import Path

from sqlalchemy import func, select

from app.core.database import async_session
from app.models import JobSkillFact, RawJobRecord, Skill, SourceDocument
from app.services import ImportService
import app.services.import_service as import_module


async def test_import_is_idempotent_and_cross_validates_sources(monkeypatch):
    records = [
        {
            "title": "Java 开发", "company": "A", "source": "来源A",
            "url": "https://a/1", "jd_text": "精通 Java、Spring Boot、MySQL",
            "require": "熟悉 Redis", "duty": "",
            "post_date": "2026-07-01", "crawled_at": "2026-07-29T10:00:00",
            "keywords": ["Java", "Spring Boot"],
        },
        {
            "title": "后端工程师", "company": "B", "source": "来源B",
            "url": "https://b/1", "jd_text": "掌握 Java、Spring Boot、MySQL",
            "requirements": "Docker 优先", "responsibilities": "",
            "posted_at": "2026-07-02", "crawled_at": "2026-07-29T10:00:00",
            "keywords": ["Java", "Docker"],
        },
    ]
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "test.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))
        monkeypatch.setattr(import_module, "ALLOWED_FILES", {"test.json"})

        async with async_session() as db:
            service = ImportService(db)
            first = await service.import_files(["test.json"])
            second = await service.import_files(["test.json"])
            assert first["imported"] == 2
            assert first["validation"][0]["passed"] == 2
            assert first["verified_skill_facts"] >= 2
            assert second["imported"] == 0
            assert second["duplicates"] == 2
            assert await db.scalar(select(func.count(RawJobRecord.id))) == 2
            assert await db.scalar(select(func.count(SourceDocument.id))) == 2
            assert await db.scalar(select(func.count(Skill.id))) >= 4
            java = (await db.execute(select(Skill).where(Skill.canonical_key == "java"))).scalar_one()
            facts = (await db.execute(
                select(JobSkillFact).where(JobSkillFact.skill_id == java.id)
            )).scalars().all()
            assert all(fact.source_count == 2 for fact in facts)
            assert all(fact.verification_status == "verified" for fact in facts)
            facts[0].verification_status = "rejected"
            facts[0].review_note = "人工判定证据不足"
            await db.flush()
            await service._cross_validate_facts([])
            assert facts[0].verification_status == "rejected"
            assert facts[0].review_note == "人工判定证据不足"
            first_raw = (
                await db.execute(
                    select(RawJobRecord).where(RawJobRecord.title == "Java 开发")
                )
            ).scalar_one()
            assert first_raw.requirements == "熟悉 Redis"


async def test_import_rejects_invalid_job_v1(monkeypatch):
    records = [{
        "title": "无来源岗位",
        "company": "A",
        "source": "来源A",
        "url": "",
        "jd_text": "内容太短",
        "posted_at": "",
        "crawled_at": "2026-07-29T10:00:00",
        "keywords": [],
    }]
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "test.json").write_text(
            json.dumps(records, ensure_ascii=False), encoding="utf-8"
        )
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))
        monkeypatch.setattr(import_module, "ALLOWED_FILES", {"test.json"})

        async with async_session() as db:
            service = ImportService(db)
            try:
                await service.import_files(["test.json"])
                assert False, "invalid job-v1 payload must be rejected"
            except Exception as exc:
                assert "job-v1 校验失败" in str(exc)
            assert await db.scalar(select(func.count(RawJobRecord.id))) == 0
