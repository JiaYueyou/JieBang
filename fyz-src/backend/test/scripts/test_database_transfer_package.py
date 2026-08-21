from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db_transfer_common import (  # noqa: E402
    inspect_snapshot_sql,
    sha256_file,
    sha256_text,
    validate_snapshot_package,
)
import db_transfer_common  # noqa: E402
from export_mysql_snapshot import sanitize_competition_row  # noqa: E402


def test_competition_snapshot_pseudonymizes_resume_identity() -> None:
    columns = ["id", "name", "original_filename", "storage_key", "content_hash"]
    result = sanitize_competition_row(
        "resume", columns, (7, "真实姓名", "真实姓名.pdf", "resumes/private.pdf", "secret")
    )

    assert result[1] == "演示候选人07"
    assert result[2] == "candidate-07.pdf"
    assert result[3] == "competition/resume-07.pdf"
    assert result[4] != "secret"


def test_docker_delivery_includes_snapshot_and_gates_all_writers() -> None:
    repository = Path(__file__).resolve().parents[4]
    dockerignore = (repository / ".dockerignore").read_text(encoding="utf-8")
    compose = (repository / "deploy" / "compose.yml").read_text(encoding="utf-8")

    assert "!fyz-src/backend/scripts/mysql_snapshot.sql" in dockerignore
    assert "!fyz-src/backend/scripts/mysql_snapshot_manifest.json" in dockerignore
    assert "fyz-bootstrap-snapshot:" in compose
    assert compose.count("fyz-bootstrap-snapshot:") >= 5
    assert "FYZ_SNAPSHOT_BOOTSTRAP_MODE" in compose


def _package(tmp_path: Path) -> tuple[Path, Path, Path]:
    sql = tmp_path / "mysql_snapshot.sql"
    sql.write_text(
        "-- JieBang complete MySQL data snapshot (schema is managed by Alembic)\n"
        "-- Alembic revision: 20260809_0020\n"
        "-- Generated statements are one-per-line for the Python importer.\n"
        "DELETE FROM `empty_table`;\n"
        "DELETE FROM `example`;\n"
        "INSERT INTO `example` (`id`, `text`) VALUES "
        "(1, 'parentheses () and VALUES inside text, comma stays quoted'), "
        "(2, 'escaped \\' quote');\n",
        encoding="utf-8",
        newline="\n",
    )
    line = sql.read_text(encoding="utf-8").splitlines()[-1] + "\n"
    empty_hash = hashlib.sha256(b"").hexdigest()
    manifest = {
        "format_version": 3,
        "generated_at": "2026-08-12T00:00:00+00:00",
        "source_database": "test",
        "alembic_revision": "20260809_0020",
        "schema_source": "alembic",
        "data_file": sql.name,
        "table_count": 2,
        "table_names_sha256": sha256_text("empty_table\nexample\n"),
        "table_counts": {"empty_table": 0, "example": 2},
        "table_sha256": {
            "empty_table": empty_hash,
            "example": hashlib.sha256(line.encode("utf-8")).hexdigest(),
        },
        "total_rows": 2,
        "chroma": {"materialization": "test", "indexes": [], "collection_count": 0, "vector_count": 0},
        "neo4j": {"materialization": "test", "latest_snapshot": None},
        "size_bytes": sql.stat().st_size,
        "sha256": sha256_file(sql),
    }
    manifest_path = tmp_path / "mysql_snapshot_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    summary = {
        "format_version": 1,
        "status": "passed",
        "alembic_revision": "20260809_0020",
        "snapshot_sha256": sha256_file(sql),
        "manifest_sha256": sha256_file(manifest_path),
        "table_count": 2,
        "total_rows": 2,
        "checks": {"strict_package_validation": True},
    }
    summary_path = tmp_path / "mysql_snapshot_verification.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return sql, manifest_path, summary_path


def test_validate_snapshot_package_accepts_complete_package(tmp_path: Path) -> None:
    sql, manifest, summary = _package(tmp_path)

    result = validate_snapshot_package(
        sql, manifest, summary, expected_revision="20260809_0020"
    )

    assert result["total_rows"] == 2
    assert inspect_snapshot_sql(sql)["row_counts"] == {"example": 2}


def test_validate_snapshot_package_rejects_sql_tampering(tmp_path: Path) -> None:
    sql, manifest, summary = _package(tmp_path)
    sql.write_text(sql.read_text(encoding="utf-8").replace("(2,", "(3,"), encoding="utf-8")

    with pytest.raises(RuntimeError, match="checksum"):
        validate_snapshot_package(
            sql, manifest, summary, expected_revision="20260809_0020"
        )


def test_validate_snapshot_package_rejects_manifest_count_tampering(tmp_path: Path) -> None:
    sql, manifest_path, summary = _package(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["table_counts"]["example"] = 3
    manifest["total_rows"] = 3
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="row counts differ"):
        validate_snapshot_package(
            sql, manifest_path, summary, expected_revision="20260809_0020"
        )


def test_validate_snapshot_package_rejects_old_revision(tmp_path: Path) -> None:
    sql, manifest, summary = _package(tmp_path)

    with pytest.raises(RuntimeError, match="revision mismatch"):
        validate_snapshot_package(
            sql, manifest, summary, expected_revision="20260801_0017"
        )


def test_validate_snapshot_package_rejects_unsupported_statement(tmp_path: Path) -> None:
    sql, manifest, summary = _package(tmp_path)
    sql.write_text(sql.read_text(encoding="utf-8") + "DROP TABLE `example`;\n", encoding="utf-8")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["size_bytes"] = sql.stat().st_size
    data["sha256"] = sha256_file(sql)
    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    verification = json.loads(summary.read_text(encoding="utf-8"))
    verification["snapshot_sha256"] = sha256_file(sql)
    verification["manifest_sha256"] = sha256_file(manifest)
    summary.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="unsupported SQL"):
        validate_snapshot_package(
            sql, manifest, summary, expected_revision="20260809_0020"
        )


def test_load_manifest_rejects_missing_package_before_alembic_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    missing_sql = tmp_path / "missing.sql"
    missing_manifest = tmp_path / "missing.json"
    head_lookup = Mock()
    monkeypatch.setattr(db_transfer_common, "SNAPSHOT_PATH", missing_sql)
    monkeypatch.setattr(db_transfer_common, "MANIFEST_PATH", missing_manifest)
    monkeypatch.setattr(
        db_transfer_common, "VERIFICATION_PATH", tmp_path / "missing-summary.json"
    )
    monkeypatch.setattr(db_transfer_common, "repository_alembic_head", head_lookup)

    with pytest.raises(RuntimeError, match="incomplete"):
        db_transfer_common.load_manifest()

    head_lookup.assert_not_called()
