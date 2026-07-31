"""批量 JD 导入幂等与交叉验证测试。"""

import json
import tempfile
from pathlib import Path

from sqlalchemy import func, select

from app.core.database import async_session
from app.models import (
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    SourceTrustPolicy,
)
from app.services import ImportService
import app.services.import_service as import_module


async def test_import_is_idempotent_without_cross_validating_different_jobs(monkeypatch):
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
            assert first["verified_skill_facts"] == 0
            assert (
                first["quality_status_counts"]["accepted"]
                + first["quality_status_counts"]["warning"]
                == 2
            )
            assert second["imported"] == 0
            assert second["duplicates"] == 2
            assert await db.scalar(select(func.count(RawJobRecord.id))) == 2
            assert await db.scalar(select(func.count(SourceDocument.id))) == 2
            assert await db.scalar(select(func.count(SourceTrustPolicy.id))) == 2
            assert await db.scalar(select(func.count(Skill.id))) >= 4
            java = (await db.execute(select(Skill).where(Skill.canonical_key == "java"))).scalar_one()
            facts = (await db.execute(
                select(JobSkillFact).where(JobSkillFact.skill_id == java.id)
            )).scalars().all()
            assert all(fact.source_count == 1 for fact in facts)
            assert all(fact.verification_status == "unverified" for fact in facts)
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
            assert first_raw.posted_at is not None
            assert first_raw.crawled_at is not None
            assert first_raw.quality_status in {"accepted", "warning"}
            assert first_raw.standard_job_id is not None


async def test_import_deduplicates_stable_source_external_identity(monkeypatch):
    records = [
        {
            "external_id": "source-job-42",
            "title": "Python 开发工程师",
            "company": "A",
            "source": "来源A",
            "url": "https://a/42",
            "jd_text": "负责 Python 服务开发、MySQL 数据建模和接口维护。",
            "posted_at": "2026-07-20",
            "crawled_at": "2026-07-29T10:00:00+08:00",
            "keywords": ["Python", "MySQL"],
        },
        {
            "external_id": "source-job-42",
            "title": "Python 研发工程师",
            "company": "A",
            "source": "来源A",
            "url": "https://a/42?from=feed",
            "jd_text": "负责 Python 服务研发，包含 MySQL 数据建模和 API 维护。",
            "posted_at": "2026-07-21",
            "crawled_at": "2026-07-29T11:00:00+08:00",
            "keywords": ["Python", "MySQL"],
        },
    ]
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "test.json").write_text(
            json.dumps(records, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))
        monkeypatch.setattr(import_module, "ALLOWED_FILES", {"test.json"})

        async with async_session() as db:
            result = await ImportService(db).import_files(["test.json"])

            assert result["imported"] == 1
            assert result["duplicates"] == 1
            source = (await db.execute(select(SourceDocument))).scalar_one()
            assert source.external_id == "source-job-42"


async def test_same_standard_job_cross_validates_independent_sources(monkeypatch):
    records = [
        {
            "title": "高级 Java 开发工程师",
            "company": "A",
            "source": "来源A",
            "url": "https://a/java",
            "jd_text": "负责 Java 服务开发，要求熟练掌握 Spring Boot、MySQL 和 Redis。",
            "posted_at": "2026-07-20",
            "crawled_at": "2026-07-29T10:00:00+08:00",
            "keywords": ["Java", "Spring Boot"],
        },
        {
            "title": "Java 研发工程师",
            "company": "B",
            "source": "来源B",
            "url": "https://b/java",
            "jd_text": "承担 Java 服务研发，熟悉 Spring Boot、MySQL、Redis 与接口测试。",
            "posted_at": "2026-07-21",
            "crawled_at": "2026-07-29T11:00:00+08:00",
            "keywords": ["Java", "Spring Boot"],
        },
    ]
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "test.json").write_text(
            json.dumps(records, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))
        monkeypatch.setattr(import_module, "ALLOWED_FILES", {"test.json"})

        async with async_session() as db:
            result = await ImportService(db).import_files(["test.json"])
            java = await db.scalar(select(Skill).where(Skill.canonical_key == "java"))
            facts = (
                await db.execute(
                    select(JobSkillFact).where(JobSkillFact.skill_id == java.id)
                )
            ).scalars().all()

            assert result["cross_source_verified"] >= 1
            assert all(fact.source_count == 2 for fact in facts)
            assert all(fact.verification_status == "verified" for fact in facts)
            raws = (await db.execute(select(RawJobRecord))).scalars().all()
            assert len({raw.standard_job_id for raw in raws}) == 1


async def test_near_duplicate_is_retained_and_downweighted(monkeypatch):
    records = [
        {
            "title": "Python 开发工程师",
            "company": "A",
            "source": "来源A",
            "url": "https://a/python",
            "jd_text": "负责 Python 服务开发、MySQL 数据建模和 FastAPI 接口维护。",
            "posted_at": "2026-07-20",
            "crawled_at": "2026-07-29T10:00:00+08:00",
            "keywords": ["Python", "MySQL"],
        },
        {
            "title": "Python 研发工程师",
            "company": "B",
            "source": "来源B",
            "url": "https://b/python",
            "jd_text": "负责 Python 服务开发、MySQL 数据建模和 FastAPI 接口维护。",
            "posted_at": "2026-07-21",
            "crawled_at": "2026-07-29T11:00:00+08:00",
            "keywords": ["Python", "MySQL"],
        },
    ]
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "test.json").write_text(
            json.dumps(records, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))
        monkeypatch.setattr(import_module, "ALLOWED_FILES", {"test.json"})

        async with async_session() as db:
            result = await ImportService(db).import_files(["test.json"])
            raws = (
                await db.execute(select(RawJobRecord).order_by(RawJobRecord.id))
            ).scalars().all()

            assert result["imported"] == 2
            assert result["near_duplicates"] == 1
            assert all(raw.dedup_status == "near_duplicate" for raw in raws)
            assert len({raw.near_duplicate_group_id for raw in raws}) == 1
            assert all("near_duplicate" in raw.quality_flags for raw in raws)


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
