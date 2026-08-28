"""Bootstrap the packaged competition snapshot without overwriting live updates."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db_transfer_common import (  # noqa: E402
    connect_mysql,
    current_alembic_revision,
    load_manifest,
)
from app.core.security import hash_password  # noqa: E402

MARKER_PATH = Path(os.getenv("LOCAL_STORAGE_PATH", "/app/storage")) / "competition-snapshot-ready.json"
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
RESUME_ASSET_DIR = DATA_DIR / "competition-resumes"
RESUME_ASSET_MANIFEST_PATH = RESUME_ASSET_DIR / "manifest.json"
LOCK_NAME = "jiebang_competition_snapshot_bootstrap"


def decide_action(
    mode: str,
    *,
    business_rows: int,
    current_revision: str,
    expected_revision: str,
    marker_status: str | None,
) -> str:
    """Return restore/skip or fail closed before any destructive command."""
    if mode == "off":
        return "skip"
    if mode == "force":
        return "restore"
    if mode != "if-empty":
        raise RuntimeError("FYZ_SNAPSHOT_BOOTSTRAP_MODE must be off, if-empty, or force")
    if current_revision != expected_revision:
        raise RuntimeError(
            f"Database revision {current_revision!r} does not match packaged snapshot "
            f"revision {expected_revision!r}."
        )
    if business_rows == 0:
        return "restore"
    if marker_status == "verified":
        return "skip"
    if marker_status == "restoring":
        return "restore"
    raise RuntimeError(
        "Database already contains business data but no matching verified snapshot marker exists. "
        "Refusing to overwrite it; restore the matching storage volume or explicitly use force mode."
    )


def _marker_status(manifest: dict) -> str | None:
    try:
        marker = json.loads(MARKER_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if (
        marker.get("alembic_revision") != manifest.get("alembic_revision")
        or marker.get("snapshot_sha256") != manifest.get("sha256")
    ):
        return None
    status = str(marker.get("status") or "")
    return status if status in {"restoring", "verified"} else None


def _write_marker(manifest: dict, status: str) -> None:
    MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKER_PATH.write_text(
        json.dumps(
            {
                "status": status,
                "alembic_revision": manifest["alembic_revision"],
                "snapshot_sha256": manifest["sha256"],
                "table_count": manifest["table_count"],
                "total_rows": manifest["total_rows"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_resume_asset_manifest(path: Path = RESUME_ASSET_MANIFEST_PATH) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Packaged resume asset manifest is unavailable: {path}") from exc
    if manifest.get("format_version") != 1 or not manifest.get("files"):
        raise RuntimeError("Packaged resume asset manifest is invalid")
    return manifest


def materialize_resume_assets(
    manifest: dict,
    *,
    asset_dir: Path = RESUME_ASSET_DIR,
    storage_root: Path | None = None,
) -> dict[str, int]:
    root = storage_root or MARKER_PATH.parent
    restored = 0
    preserved = 0
    for entry in manifest["files"]:
        source = asset_dir / str(entry["asset_filename"])
        if not source.is_file():
            raise RuntimeError(f"Packaged resume asset is missing: {source.name}")
        expected_size = int(entry["size_bytes"])
        expected_sha256 = str(entry["sha256"])
        if source.stat().st_size != expected_size or _sha256_file(source) != expected_sha256:
            raise RuntimeError(f"Packaged resume asset failed integrity validation: {source.name}")
        storage_key = str(entry["storage_key"]).replace("\\", "/")
        destination = (root / storage_key).resolve()
        resolved_root = root.resolve()
        if resolved_root not in destination.parents:
            raise RuntimeError(f"Packaged resume storage key is invalid: {storage_key}")
        if (
            destination.is_file()
            and destination.stat().st_size == expected_size
            and _sha256_file(destination) == expected_sha256
        ):
            preserved += 1
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp")
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
        restored += 1
    return {"restored": restored, "preserved": preserved, "total": len(manifest["files"])}


async def validate_resume_asset_rows(connection, manifest: dict) -> None:
    expected = {
        str(entry["storage_key"]): (int(entry["resume_id"]), int(entry["size_bytes"]))
        for entry in manifest["files"]
    }
    async with connection.cursor() as cursor:
        await cursor.execute(
            "SELECT id, storage_key, file_size FROM resume "
            "WHERE deleted_at IS NULL ORDER BY id"
        )
        actual = {
            str(storage_key): (int(resume_id), int(file_size))
            for resume_id, storage_key, file_size in await cursor.fetchall()
        }
    if actual != expected:
        raise RuntimeError(
            "Packaged resume assets do not match the active resume rows in the snapshot"
        )


async def restore_resume_assets(connection) -> dict[str, int]:
    manifest = load_resume_asset_manifest()
    await validate_resume_asset_rows(connection, manifest)
    return materialize_resume_assets(manifest)


async def _configure_competition_admin(connection) -> None:
    username = os.getenv("INITIAL_ADMIN_USERNAME", "admin").strip() or "admin"
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    if not password:
        raise RuntimeError(
            "INITIAL_ADMIN_PASSWORD is required so the packaged snapshot has a usable login"
        )
    async with connection.cursor() as cursor:
        await cursor.execute(
            "UPDATE `user` SET password_hash=%s, role='admin' WHERE username=%s",
            (hash_password(password), username),
        )
        if cursor.rowcount != 1:
            raise RuntimeError(
                f"Packaged snapshot does not contain expected administrator {username!r}"
            )
    await connection.commit()


async def bootstrap() -> None:
    manifest = load_manifest()
    if manifest.get("snapshot_profile") != "competition-sanitized-v1":
        raise RuntimeError(
            "Docker bootstrap requires snapshot_profile=competition-sanitized-v1"
        )
    mode = os.getenv("FYZ_SNAPSHOT_BOOTSTRAP_MODE", "if-empty").strip().lower()
    connection = await connect_mysql()
    lock_acquired = False
    try:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT GET_LOCK(%s, 120)", (LOCK_NAME,))
            lock_acquired = bool((await cursor.fetchone())[0])
            if not lock_acquired:
                raise RuntimeError("Timed out waiting for the snapshot bootstrap lock")
            await cursor.execute("SELECT COUNT(*) FROM source_document")
            business_rows = int((await cursor.fetchone())[0])
        revision = await current_alembic_revision(connection)
        action = decide_action(
            mode,
            business_rows=business_rows,
            current_revision=revision,
            expected_revision=str(manifest["alembic_revision"]),
            marker_status=_marker_status(manifest),
        )
        if action == "skip":
            resume_summary = await restore_resume_assets(connection)
            print(
                "Competition snapshot bootstrap skipped: existing verified data is preserved "
                f"(rows={business_rows}, revision={revision}, "
                f"resume_assets={resume_summary['total']})."
            )
            return

        _write_marker(manifest, "restoring")
        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run_database_import.py"), "--replace"],
            cwd=SCRIPTS_DIR.parent,
            check=True,
        )
        await _configure_competition_admin(connection)
        resume_summary = await restore_resume_assets(connection)
        _write_marker(manifest, "verified")
        print(
            f"Competition snapshot is ready: {MARKER_PATH} "
            f"(resume_assets={resume_summary['total']})."
        )
    finally:
        if lock_acquired:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT RELEASE_LOCK(%s)", (LOCK_NAME,))
        connection.close()


def main() -> None:
    asyncio.run(bootstrap())


if __name__ == "__main__":
    main()
