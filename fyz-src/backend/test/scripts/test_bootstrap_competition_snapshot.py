from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "bootstrap_competition_snapshot.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("bootstrap_competition_snapshot_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_if_empty_restores_packaged_snapshot() -> None:
    module = _load_module()
    assert module.decide_action(
        "if-empty", business_rows=0, current_revision="0025",
        expected_revision="0025", marker_status=None,
    ) == "restore"


def test_matching_verified_snapshot_preserves_incremental_data() -> None:
    module = _load_module()
    assert module.decide_action(
        "if-empty", business_rows=4683, current_revision="0025",
        expected_revision="0025", marker_status="verified",
    ) == "skip"


def test_nonempty_unverified_database_is_never_overwritten_implicitly() -> None:
    module = _load_module()
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        module.decide_action(
            "if-empty", business_rows=1, current_revision="0025",
            expected_revision="0025", marker_status=None,
        )


def test_matching_incomplete_bootstrap_is_safely_retryable() -> None:
    module = _load_module()
    assert module.decide_action(
        "if-empty", business_rows=4683, current_revision="0025",
        expected_revision="0025", marker_status="restoring",
    ) == "restore"
