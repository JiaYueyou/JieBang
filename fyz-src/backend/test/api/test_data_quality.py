import json
import tempfile
from pathlib import Path

from sqlalchemy import select

import app.services.import_service as import_module
from app.core.database import async_session
from app.models import RawJobRecord


async def _import_quality_record(client, auth_headers, monkeypatch) -> int:
    payload = [
        {
            "title": "Python 开发工程师",
            "company": "示例公司",
            "source": "示例来源",
            "url": "https://example.test/jobs/quality-1",
            "jd_text": "负责 Python 服务开发、MySQL 数据建模、FastAPI 接口维护和线上问题排查。",
            "posted_at": "2026-07-20",
            "crawled_at": "2026-07-29T10:00:00+08:00",
            "keywords": ["Python", "MySQL", "FastAPI"],
        }
    ]
    with tempfile.TemporaryDirectory(dir="test") as directory:
        root = Path(directory)
        (root / "quality.json").write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(import_module, "DATA_DIR", str(root))
        monkeypatch.setattr(import_module, "ALLOWED_FILES", {"quality.json"})
        response = await client.post(
            "/api/v1/data-imports/jobs",
            headers=auth_headers,
            json={"files": ["quality.json"]},
        )
        assert response.status_code == 200
    async with async_session() as db:
        record = await db.scalar(select(RawJobRecord))
        return record.id


async def test_admin_lists_excludes_and_restores_quality_record(
    client,
    auth_headers,
    monkeypatch,
):
    record_id = await _import_quality_record(client, auth_headers, monkeypatch)

    listed = await client.get(
        "/api/v1/admin/data-quality/records",
        headers=auth_headers,
        params={"quality_status": "accepted"},
    )
    assert listed.status_code == 200
    data = listed.json()["data"]
    assert data["summary"]["total"] == 1
    assert data["items"][0]["id"] == record_id

    excluded = await client.patch(
        f"/api/v1/admin/data-quality/records/{record_id}",
        headers=auth_headers,
        json={"action": "exclude", "reason": "人工确认来源内容异常"},
    )
    assert excluded.status_code == 200
    assert excluded.json()["data"]["is_excluded"] is True

    restored = await client.patch(
        f"/api/v1/admin/data-quality/records/{record_id}",
        headers=auth_headers,
        json={"action": "restore"},
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["is_excluded"] is False


async def test_non_admin_cannot_manage_data_quality(
    client,
    auth_headers,
    monkeypatch,
):
    await _import_quality_record(client, auth_headers, monkeypatch)
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "normal", "password": "user123"},
    )
    headers = {
        "Authorization": f"Bearer {login.json()['data']['access_token']}"
    }

    response = await client.get(
        "/api/v1/admin/data-quality/records",
        headers=headers,
    )
    assert response.status_code == 403
