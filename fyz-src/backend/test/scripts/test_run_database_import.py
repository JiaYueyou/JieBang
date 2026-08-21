from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
MODULE_PATH = SCRIPTS_DIR / "run_database_import.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_database_import_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_failure_spawns_no_target_side_process(monkeypatch) -> None:
    module = _load_module()
    process_runner = Mock()
    target_connection = Mock()
    import db_transfer_common

    monkeypatch.setattr(module.subprocess, "run", process_runner)
    monkeypatch.setattr(db_transfer_common, "connect_mysql", target_connection)
    monkeypatch.setattr(
        module,
        "load_manifest",
        Mock(side_effect=RuntimeError("snapshot verification summary is missing")),
    )
    monkeypatch.setattr(sys, "argv", [str(MODULE_PATH), "--replace"])

    with pytest.raises(RuntimeError, match="verification summary is missing"):
        module.main()

    process_runner.assert_not_called()
    target_connection.assert_not_called()


def test_preflight_completes_before_first_subprocess(monkeypatch) -> None:
    module = _load_module()
    events: list[str] = []
    monkeypatch.setattr(
        module,
        "load_manifest",
        lambda: events.append("preflight")
        or {
            "alembic_revision": "20260809_0020",
            "table_count": 42,
            "total_rows": 41667,
        },
    )

    def fake_run(command, **kwargs):
        events.append(Path(command[1]).name)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", [str(MODULE_PATH), "--replace"])

    module.main()

    assert events == [
        "preflight",
        "01_prepare_mysql_schema.py",
        "02_import_mysql_snapshot.py",
        "restore_chroma_from_mysql.py",
        "03_rebuild_neo4j.py",
        "04_verify_database_import.py",
    ]


def test_powershell_entry_delegates_to_preflighted_orchestrator() -> None:
    script = (SCRIPTS_DIR / "Import-TeamDatabase.ps1").read_text(encoding="utf-8")

    assert '"run_database_import.py"' in script
    assert "01_prepare_mysql_schema.py" not in script
    assert "02_import_mysql_snapshot.py" not in script
