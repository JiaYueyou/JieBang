from __future__ import annotations

import importlib.util
import hashlib
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


def test_materialize_resume_assets_restores_and_then_preserves(tmp_path: Path) -> None:
    module = _load_module()
    asset_dir = tmp_path / "assets"
    storage_root = tmp_path / "storage"
    asset_dir.mkdir()
    payload = b"competition resume"
    (asset_dir / "resume-01.pdf").write_bytes(payload)
    manifest = {
        "format_version": 1,
        "files": [
            {
                "resume_id": 1,
                "asset_filename": "resume-01.pdf",
                "storage_key": "competition/resume-01.pdf",
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        ],
    }

    first = module.materialize_resume_assets(
        manifest, asset_dir=asset_dir, storage_root=storage_root
    )
    second = module.materialize_resume_assets(
        manifest, asset_dir=asset_dir, storage_root=storage_root
    )

    assert first == {"restored": 1, "preserved": 0, "total": 1}
    assert second == {"restored": 0, "preserved": 1, "total": 1}
    assert (storage_root / "competition" / "resume-01.pdf").read_bytes() == payload


def test_materialize_resume_assets_rejects_tampering(tmp_path: Path) -> None:
    module = _load_module()
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    (asset_dir / "resume-01.pdf").write_bytes(b"tampered")
    manifest = {
        "format_version": 1,
        "files": [
            {
                "resume_id": 1,
                "asset_filename": "resume-01.pdf",
                "storage_key": "competition/resume-01.pdf",
                "size_bytes": 8,
                "sha256": "0" * 64,
            }
        ],
    }

    with pytest.raises(RuntimeError, match="integrity validation"):
        module.materialize_resume_assets(
            manifest, asset_dir=asset_dir, storage_root=tmp_path / "storage"
        )
