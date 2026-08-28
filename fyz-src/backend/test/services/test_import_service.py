"""批量 JD 导入幂等与交叉验证测试。"""

import json
import hashlib
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import event, func, select

from app.core.database import async_session, engine
from app.core.exceptions import InvalidParameterError
from app.models import (
    ExternalJobIdentity,
    ExternalJobVersion,
    JobImportQuarantine,
    JobDuplicateCluster,
    JobSourceObservation,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    SourceSnapshot,
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


async def test_full_snapshots_version_and_close_jobs_after_consecutive_absence(monkeypatch):
    monkeypatch.setattr(import_module, "JOB_MISSING_CLOSE_THRESHOLD", 2)
    source = "生命周期测试官方招聘门户"

    def job(external_id: str, day: int, *, jd_text: str) -> dict:
        return {
            "external_id": external_id,
            "title": "Python 平台工程师",
            "company": "示例公司",
            "source": source,
            "url": f"https://example.test/jobs/{external_id}",
            "jd_text": jd_text,
            "posted_at": "2026-08-01",
            "crawled_at": f"2026-08-{day:02d}T10:00:00+08:00",
            "keywords": ["Python", "FastAPI"],
            "source_meta": {
                "snapshot_type": "full",
                "snapshot_complete": True,
                "snapshot_observed_at": f"2026-08-{day:02d}T10:00:00+08:00",
            },
        }

    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        snapshots = {
            "full-1.json": [
                job("active", 18, jd_text="使用 Python 与 FastAPI 开发平台服务。"),
                job("closing", 18, jd_text="使用 Python 开发数据平台服务。"),
            ],
            "full-2.json": [
                job("active", 19, jd_text="使用 Python、FastAPI 与 Redis 开发平台服务。"),
            ],
            "full-3.json": [
                job("active", 20, jd_text="使用 Python、FastAPI 与 Redis 开发平台服务。"),
            ],
        }
        for filename, rows in snapshots.items():
            (test_dir / filename).write_text(
                json.dumps(rows, ensure_ascii=False), encoding="utf-8"
            )
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))

        async with async_session() as db:
            service = ImportService(db)
            first = await service.import_files(["full-1.json"])
            second = await service.import_files(["full-2.json"])
            third = await service.import_files(["full-3.json"])

            assert first["versions_created"] == 2
            assert second["versions_created"] == 1
            assert second["missing_observations"] == 1
            assert third["closed_jobs"] == 1
            identities = list((await db.execute(
                select(ExternalJobIdentity).order_by(ExternalJobIdentity.external_id)
            )).scalars())
            by_external_id = {row.external_id: row for row in identities}
            assert by_external_id["active"].lifecycle_status == "active"
            assert by_external_id["closing"].lifecycle_status == "closed"
            assert by_external_id["closing"].missing_streak == 2
            active_versions = list((await db.execute(
                select(ExternalJobVersion).where(
                    ExternalJobVersion.identity_id == by_external_id["active"].id
                ).order_by(ExternalJobVersion.version_no)
            )).scalars())
            assert [row.version_no for row in active_versions] == [1, 2]
            assert active_versions[0].is_current is False
            assert active_versions[1].is_current is True
            assert await db.scalar(select(func.count(SourceSnapshot.id))) == 3
            events = list((await db.execute(
                select(JobSourceObservation.event_type)
                .where(JobSourceObservation.external_job_identity_id == by_external_id["closing"].id)
                .order_by(JobSourceObservation.observed_on)
            )).scalars())
            assert events == ["seen", "missing", "closed"]

            (test_dir / "full-old.json").write_text(
                json.dumps([job("active", 17, jd_text="旧版 Python 平台岗位说明。")],
                           ensure_ascii=False),
                encoding="utf-8",
            )
            with pytest.raises(InvalidParameterError, match="乱序快照"):
                await service.import_files(["full-old.json"])
            await db.refresh(by_external_id["active"])
            assert by_external_id["active"].lifecycle_status == "active"
            assert by_external_id["active"].current_version_id == active_versions[1].id


async def test_same_day_missing_snapshots_only_advance_streak_once(monkeypatch):
    monkeypatch.setattr(import_module, "JOB_MISSING_CLOSE_THRESHOLD", 2)
    source = "同日观测测试源"

    def job(external_id: str, timestamp: str) -> dict:
        return {
            "external_id": external_id,
            "title": "Java 平台工程师",
            "company": "示例公司",
            "source": source,
            "url": f"https://example.test/jobs/{external_id}",
            "jd_text": "使用 Java、Spring Boot 和 MySQL 开发平台服务。",
            "posted_at": "2026-08-01",
            "crawled_at": timestamp,
            "keywords": ["Java", "Spring Boot"],
            "source_meta": {
                "snapshot_type": "full", "snapshot_complete": True,
                "snapshot_observed_at": timestamp,
            },
        }

    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        payloads = {
            "day-1.json": [job("seen", "2026-08-18T10:00:00+08:00"),
                           job("missing", "2026-08-18T10:00:00+08:00")],
            "day-2-a.json": [job("seen", "2026-08-19T10:00:00+08:00")],
            "day-2-b.json": [job("seen", "2026-08-19T11:00:00+08:00")],
        }
        for filename, rows in payloads.items():
            (test_dir / filename).write_text(
                json.dumps(rows, ensure_ascii=False), encoding="utf-8"
            )
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))
        async with async_session() as db:
            service = ImportService(db)
            for filename in payloads:
                await service.import_files([filename])
            identity = await db.scalar(select(ExternalJobIdentity).where(
                ExternalJobIdentity.external_id == "missing"
            ))
            assert identity.missing_streak == 1
            assert identity.lifecycle_status == "active"


async def test_empty_full_snapshots_advance_lifecycle_with_matching_scope(monkeypatch):
    monkeypatch.setattr(import_module, "JOB_MISSING_CLOSE_THRESHOLD", 2)
    source = "空快照测试源"
    scope = {"source": source}
    scope_payload = json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    scope_hash = hashlib.sha256(scope_payload.encode("utf-8")).hexdigest()
    record = {
        "external_id": "job-to-close",
        "title": "Go 平台工程师",
        "company": "示例公司",
        "source": source,
        "url": "https://example.test/jobs/job-to-close",
        "jd_text": "使用 Go、MySQL 和 Kubernetes 开发平台服务。",
        "posted_at": "2026-08-01",
        "crawled_at": "2026-08-18T10:00:00+08:00",
        "keywords": ["Go", "MySQL"],
        "source_meta": {
            "snapshot_type": "full", "snapshot_complete": True,
            "snapshot_observed_at": "2026-08-18T10:00:00+08:00",
        },
    }

    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "initial.json").write_text(
            json.dumps([record], ensure_ascii=False), encoding="utf-8"
        )

        def write_empty(filename: str, observed_at: str) -> None:
            snapshot = test_dir / filename
            snapshot.write_text("[]", encoding="utf-8")
            manifest = {
                "schema_version": "crawler-snapshot-manifest-v1",
                "source": source,
                "snapshot_type": "full",
                "snapshot_complete": True,
                "observed_at": observed_at,
                "scope": scope,
                "scope_hash": scope_hash,
                "record_count": 0,
                "payload_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            }
            snapshot.with_name(snapshot.name + ".manifest").write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )

        write_empty("empty-1.json", "2026-08-19T10:00:00+08:00")
        write_empty("empty-2.json", "2026-08-20T10:00:00+08:00")
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))

        async with async_session() as db:
            service = ImportService(db)
            await service.import_files(["initial.json"])
            first_missing = await service.import_files(["empty-1.json"])
            closed = await service.import_files(["empty-2.json"])
            identity = await db.scalar(select(ExternalJobIdentity).where(
                ExternalJobIdentity.external_id == "job-to-close"
            ))

            assert first_missing["missing_observations"] == 1
            assert closed["closed_jobs"] == 1
            assert identity.lifecycle_status == "closed"


async def test_full_snapshot_does_not_close_jobs_from_another_scope(monkeypatch):
    monkeypatch.setattr(import_module, "JOB_MISSING_CLOSE_THRESHOLD", 1)
    source = "范围隔离测试源"

    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)

        def write_snapshot(
            filename: str, observed_at: str, scope: dict, rows: list[dict]
        ) -> None:
            snapshot = test_dir / filename
            snapshot.write_text(
                json.dumps(rows, ensure_ascii=False), encoding="utf-8"
            )
            scope_payload = json.dumps(
                scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            snapshot.with_name(snapshot.name + ".manifest").write_text(
                json.dumps({
                    "schema_version": "crawler-snapshot-manifest-v1",
                    "source": source,
                    "snapshot_type": "full",
                    "snapshot_complete": True,
                    "observed_at": observed_at,
                    "scope": scope,
                    "scope_hash": hashlib.sha256(
                        scope_payload.encode("utf-8")
                    ).hexdigest(),
                    "record_count": len(rows),
                    "payload_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                }, ensure_ascii=False),
                encoding="utf-8",
            )

        scope_a = {"city": "北京"}
        scope_b = {"city": "上海"}
        write_snapshot("beijing.json", "2026-08-18T10:00:00+08:00", scope_a, [{
            "external_id": "beijing-job",
            "title": "Python 工程师",
            "company": "示例公司",
            "source": source,
            "url": "https://example.test/jobs/beijing-job",
            "jd_text": "使用 Python、MySQL 和 Redis 开发平台服务。",
            "posted_at": "2026-08-01",
            "crawled_at": "2026-08-18T10:00:00+08:00",
            "keywords": ["Python", "MySQL"],
        }])
        write_snapshot("shanghai-empty.json", "2026-08-20T10:00:00+08:00", scope_b, [])
        # Although this snapshot is earlier than Shanghai's watermark, it is
        # newer within the Beijing scope and must be accepted independently.
        write_snapshot("beijing-empty.json", "2026-08-19T10:00:00+08:00", scope_a, [])
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))

        async with async_session() as db:
            service = ImportService(db)
            await service.import_files(["beijing.json"])
            other_scope = await service.import_files(["shanghai-empty.json"])
            identity = await db.scalar(select(ExternalJobIdentity).where(
                ExternalJobIdentity.external_id == "beijing-job"
            ))
            assert other_scope["closed_jobs"] == 0
            assert identity.lifecycle_status == "active"

            same_scope = await service.import_files(["beijing-empty.json"])
            assert same_scope["closed_jobs"] == 1
            assert identity.lifecycle_status == "closed"


async def test_replayed_snapshot_rejects_changed_manifest_scope(monkeypatch):
    source = "manifest 不可变测试源"
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        snapshot = test_dir / "empty.json"
        snapshot.write_text("[]", encoding="utf-8")
        manifest_path = snapshot.with_name(snapshot.name + ".manifest")

        def write_manifest(scope: dict) -> None:
            scope_payload = json.dumps(
                scope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            manifest_path.write_text(json.dumps({
                "schema_version": "crawler-snapshot-manifest-v1",
                "source": source,
                "snapshot_type": "full",
                "snapshot_complete": True,
                "observed_at": "2026-08-20T10:00:00+08:00",
                "scope": scope,
                "scope_hash": hashlib.sha256(
                    scope_payload.encode("utf-8")
                ).hexdigest(),
                "record_count": 0,
                "payload_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            }, ensure_ascii=False), encoding="utf-8")

        write_manifest({"city": "北京"})
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))
        async with async_session() as db:
            service = ImportService(db)
            await service.import_files(["empty.json"])
            write_manifest({"city": "上海"})
            with pytest.raises(InvalidParameterError, match="manifest 不一致"):
                await service.import_files(["empty.json"])


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
            assert raws[0].normalization_version == "job-title-v5"

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


async def test_import_quarantines_invalid_job_v1(monkeypatch):
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
            result = await ImportService(db).import_files(["test.json"])
            assert result["total"] == 1
            assert result["imported"] == 0
            assert result["quarantined_records"] == 1
            assert await db.scalar(select(func.count(RawJobRecord.id))) == 0
            quarantined = await db.scalar(select(JobImportQuarantine))
            assert quarantined.status == "pending"
            assert quarantined.record_index == 0
            assert "字段不能为空: url" in quarantined.error_codes


async def test_import_quarantines_question_mark_only_source(monkeypatch):
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
            result = await ImportService(db).import_files(["test.json"])
            assert result["quarantined_records"] == 1
            assert await db.scalar(select(func.count(RawJobRecord.id))) == 0


async def test_mixed_full_snapshot_imports_valid_rows_but_disables_absence(monkeypatch):
    source = "隔离混合快照源"
    valid = {
        "external_id": "valid-1", "title": "Python 工程师", "company": "A",
        "source": source, "url": "https://example.test/jobs/valid-1",
        "jd_text": "使用 Python、FastAPI 和 MySQL 开发可靠的平台服务。",
        "posted_at": "2026-08-01", "crawled_at": "2026-08-20T10:00:00+08:00",
        "keywords": ["Python", "FastAPI"],
    }
    invalid = {**valid, "external_id": "invalid-1", "url": "", "title": "坏记录"}
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        snapshot = test_dir / "mixed.json"
        snapshot.write_text(json.dumps([valid, invalid], ensure_ascii=False), encoding="utf-8")
        scope = {"source": source}
        scope_payload = json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        snapshot.with_name(snapshot.name + ".manifest").write_text(json.dumps({
            "schema_version": "crawler-snapshot-manifest-v1", "source": source,
            "snapshot_type": "full", "snapshot_complete": True,
            "observed_at": "2026-08-20T10:00:00+08:00", "scope": scope,
            "scope_hash": hashlib.sha256(scope_payload.encode("utf-8")).hexdigest(),
            "record_count": 2,
            "payload_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        }, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))

        async with async_session() as db:
            result = await ImportService(db).import_files(["mixed.json"])
            source_snapshot = await db.scalar(select(SourceSnapshot))
            assert result["total"] == 2
            assert result["imported"] == 1
            assert result["quarantined_records"] == 1
            assert source_snapshot.snapshot_type == "delta"
            assert result["missing_observations"] == 0
