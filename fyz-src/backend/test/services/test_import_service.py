"""批量 JD 导入幂等与交叉验证测试。"""

import json
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import event, func, select

from app.core.database import async_session, engine
from app.core.exceptions import InvalidParameterError
from app.models import (
    JobDuplicateCluster,
    JobSourceObservation,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    SourceTrustPolicy,
)
from app.services import ImportService
import app.services.import_service as import_module


@pytest.fixture
def enforce_foreign_keys():
    """临时对 SQLite 连接启用外键检查（连接级 PRAGMA）。

    SQLite 默认不检查外键，导致 `_mark_near_duplicate` 的 flush 时序错误
    只在 MySQL 上暴露（1452）。启用后回归测试能在 SQLite 上复现该语义。
    """

    @event.listens_for(engine.sync_engine, "connect")
    def _enable(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    yield
    event.remove(engine.sync_engine, "connect", _enable)


async def test_import_is_idempotent_without_cross_validating_different_jobs(monkeypatch):
    records = [
        {
            "title": "Java 开发", "company": "A", "source": "来源A",
            "url": "https://a/1", "jd_text": "精通 Java、Spring Boot、MySQL",
            "require": "熟悉 Redis", "duty": "",
            "post_date": "2026-07-01", "crawled_at": "2026-07-29T10:00:00",
            "keywords": ["Java", "Spring Boot"],
            "archived_at": "2025-12-01T09:00:00",
            "archive_url": "https://archive.example.test/java",
            "source_type": "official_career_site",
            "license_note": "public-job-page",
            "source_meta": {"collector": "official-test"},
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
            assert first["observations"] == 2
            assert second["observations"] == 0
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
            first_document = await db.get(SourceDocument, first_raw.source_document_id)
            assert first_document.source_meta["archived_at"] == "2025-12-01T09:00:00"
            assert first_document.source_meta["archive_url"] == "https://archive.example.test/java"
            assert first_document.source_meta["source_type"] == "official_career_site"
            assert first_document.source_meta["collector"] == "official-test"


async def test_import_versions_changed_content_for_stable_source_identity(monkeypatch):
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

        async with async_session() as db:
            result = await ImportService(db).import_files(["test.json"])

            assert result["imported"] == 2
            assert result["duplicates"] == 0
            sources = (
                await db.execute(select(SourceDocument).order_by(SourceDocument.id))
            ).scalars().all()
            assert len(sources) == 2
            assert {source.external_id for source in sources} == {"source-job-42"}
            assert sources[1].source_meta["supersedes_source_document_id"] == sources[0].id
            assert await db.scalar(select(func.count(JobSourceObservation.id))) == 2


async def test_repeat_snapshot_adds_observation_without_duplicate_raw_job(monkeypatch):
    base = {
        "external_id": "portal-job-1",
        "title": "AI 平台研发工程师",
        "company": "示例公司",
        "source": "示例官方社会招聘门户",
        "url": "https://example.test/jobs/1",
        "jd_text": "负责 Python、Kubernetes 和大模型服务平台研发。",
        "posted_at": "2026-05-01",
        "keywords": ["Python", "Kubernetes", "大模型"],
    }
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "snapshot-1.json").write_text(
            json.dumps([{**base, "crawled_at": "2026-07-29T10:00:00+08:00"}], ensure_ascii=False),
            encoding="utf-8",
        )
        (test_dir / "snapshot-2.json").write_text(
            json.dumps([{**base, "crawled_at": "2026-07-30T10:00:00+08:00"}], ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))

        async with async_session() as db:
            service = ImportService(db)
            first = await service.import_files(["snapshot-1.json"])
            second = await service.import_files(["snapshot-2.json"])

            assert first["imported"] == 1
            assert first["observations"] == 1
            assert second["imported"] == 0
            assert second["duplicates"] == 1
            assert second["observations"] == 1
            assert await db.scalar(select(func.count(RawJobRecord.id))) == 1
            observations = (
                await db.execute(
                    select(JobSourceObservation).order_by(JobSourceObservation.observed_on)
                )
            ).scalars().all()
            assert [row.observed_on.isoformat() for row in observations] == [
                "2026-07-29",
                "2026-07-30",
            ]


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
            "title": "高级 Java 研发工程师",
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


async def test_near_duplicate_is_retained_and_downweighted(monkeypatch, enforce_foreign_keys):
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
            assert len({raw.duplicate_cluster_id for raw in raws}) == 1
            assert raws[0].normalization_version == "job-title-v3"

            # 外键检查开启下 cluster 必须完整存在（1452 回归）
            group_id = raws[0].duplicate_cluster_id
            clusters = (
                await db.execute(select(JobDuplicateCluster))
            ).scalars().all()
            assert len(clusters) == 1
            assert clusters[0].id == group_id
            assert clusters[0].member_count == 2
            assert clusters[0].representative_raw_job_id == raws[0].id


async def test_near_duplicate_cluster_member_count_increments(monkeypatch, enforce_foreign_keys):
    """同一近重复组追加记录：cluster 只建一次，member_count 递增。"""
    base = {
        "company": "A",
        "jd_text": "负责 Python 服务开发、MySQL 数据建模和 FastAPI 接口维护。",
        "crawled_at": "2026-07-29T10:00:00+08:00",
        "keywords": ["Python", "MySQL"],
    }
    first_two = [
        {**base, "title": "Python 开发工程师", "source": "来源A",
         "url": "https://a/python", "posted_at": "2026-07-20"},
        {**base, "title": "Python 研发工程师", "source": "来源B",
         "url": "https://b/python", "posted_at": "2026-07-21"},
    ]
    third = {
        **base, "title": "Python 研发工程师", "source": "来源C",
        "url": "https://c/python", "posted_at": "2026-07-22",
    }
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "test.json").write_text(
            json.dumps(first_two, ensure_ascii=False), encoding="utf-8"
        )
        (test_dir / "test2.json").write_text(
            json.dumps([third], ensure_ascii=False), encoding="utf-8"
        )
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))

        async with async_session() as db:
            first = await ImportService(db).import_files(["test.json"])
            assert first["imported"] == 2
            second = await ImportService(db).import_files(["test2.json"])
            assert second["imported"] == 1

            raws = (
                await db.execute(select(RawJobRecord).order_by(RawJobRecord.id))
            ).scalars().all()
            assert len({raw.duplicate_cluster_id for raw in raws}) == 1
            clusters = (
                await db.execute(select(JobDuplicateCluster))
            ).scalars().all()
            assert len(clusters) == 1
            assert clusters[0].member_count == 3
            assert clusters[0].id == raws[0].duplicate_cluster_id


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

        async with async_session() as db:
            service = ImportService(db)
            try:
                await service.import_files(["test.json"])
                assert False, "invalid job-v1 payload must be rejected"
            except Exception as exc:
                assert "job-v1 校验失败" in str(exc)
            assert await db.scalar(select(func.count(RawJobRecord.id))) == 0


async def test_import_rejects_question_mark_only_source(monkeypatch):
    records = [{
        "title": "Python Engineer",
        "company": "Example Co",
        "source": "??????",
        "url": "https://example.test/jobs/1",
        "jd_text": "Build reliable Python services and maintain APIs.",
        "posted_at": "2026-07-29",
        "crawled_at": "2026-07-29T10:00:00",
        "keywords": ["Python"],
    }]
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "test.json").write_text(json.dumps(records), encoding="utf-8")
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))

        async with async_session() as db:
            with pytest.raises(InvalidParameterError):
                await ImportService(db).import_files(["test.json"])
            assert await db.scalar(select(func.count(RawJobRecord.id))) == 0
