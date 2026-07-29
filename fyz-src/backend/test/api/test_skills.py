"""技能库、岗位抽取和任务 API 测试。"""

import json
import tempfile
from pathlib import Path

import app.services.import_service as import_module


async def _create_job(client, headers):
    response = await client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "title": "Python AI 应用工程师",
            "department": "AI 研发部",
            "level": "senior",
            "responsibilities": ["使用 Python 和 FastAPI 开发 RAG 服务"],
            "requirements": ["熟悉 PostgreSQL、Redis，Docker 经验优先"],
            "jd_text": "使用 LangChain 构建大模型应用",
            "status": "open",
        },
    )
    return response.json()["data"]


async def test_extract_job_skills_and_query_library(client, auth_headers):
    job = await _create_job(client, auth_headers)
    extracted = await client.post(
        f"/api/v1/jobs/{job['id']}/extract-skills", headers=auth_headers
    )
    assert extracted.status_code == 200
    data = extracted.json()["data"]
    assert data["llm_enrichment"] is False
    names = {fact["skill_name"] for fact in data["facts"]}
    assert {"Python", "FastAPI", "RAG", "PostgreSQL", "Redis", "Docker", "LangChain"} <= names
    assert all(fact["verification_status"] == "unverified" for fact in data["facts"])

    facts = await client.get(
        f"/api/v1/jobs/{job['id']}/skill-facts", headers=auth_headers
    )
    assert len(facts.json()["data"]) == len(data["facts"])
    skills = await client.get(
        "/api/v1/skills?keyword=Python", headers=auth_headers
    )
    assert skills.json()["meta"]["total"] == 1
    assert skills.json()["data"][0]["canonical_key"] == "python"

    versions = await client.get(
        f"/api/v1/jobs/{job['id']}/versions", headers=auth_headers
    )
    assert versions.json()["data"][0]["change_reason"] == "技能抽取更新"


async def test_import_task_eager_mode_and_status(client, auth_headers, monkeypatch):
    payload = [{
        "title": "测试工程师", "company": "测试公司", "source": "测试来源",
        "url": "https://test/1", "jd_text": "熟悉 Python、pytest 和 MySQL",
        "posted_at": "2026-07-20", "crawled_at": "2026-07-29T10:00:00",
        "keywords": ["Python", "pytest", "MySQL"],
    }]
    with tempfile.TemporaryDirectory(dir="test") as directory:
        test_dir = Path(directory)
        (test_dir / "test.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr(import_module, "DATA_DIR", str(test_dir))
        monkeypatch.setattr(import_module, "ALLOWED_FILES", {"test.json"})
        response = await client.post(
            "/api/v1/data-imports/jobs",
            headers=auth_headers,
            json={"files": ["test.json"]},
        )
        assert response.status_code == 200
        task = response.json()["data"]
        assert task["status"] == "succeeded"
        assert task["progress"] == 100
        queried = await client.get(
            f"/api/v1/tasks/{task['task_id']}", headers=auth_headers
        )
        assert queried.json()["data"]["result"]["imported"] == 1


async def test_import_rejects_unknown_file(client, auth_headers):
    response = await client.post(
        "/api/v1/data-imports/jobs",
        headers=auth_headers,
        json={"files": ["../../secret.json"]},
    )
    assert response.status_code == 422
    assert response.json()["code"] == 40003
