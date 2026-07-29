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


async def test_admin_reviews_skill_facts_with_audit_trail(client, auth_headers):
    job = await _create_job(client, auth_headers)
    extracted = await client.post(
        f"/api/v1/jobs/{job['id']}/extract-skills",
        headers=auth_headers,
    )
    facts = extracted.json()["data"]["facts"]
    assert len(facts) >= 2

    queue = await client.get(
        "/api/v1/skills/facts/reviews",
        headers=auth_headers,
        params={"status": "unverified", "page_size": 100},
    )
    assert queue.status_code == 200
    queue_data = queue.json()
    assert queue_data["meta"]["total"] == len(facts)
    assert queue_data["data"]["summary"]["unverified"] == len(facts)
    assert queue_data["data"]["items"][0]["source"] == "内部岗位"

    normal_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "normal", "password": "user123"},
    )
    normal_headers = {
        "Authorization": f"Bearer {normal_login.json()['data']['access_token']}"
    }
    forbidden = await client.patch(
        f"/api/v1/skills/facts/{facts[0]['id']}/review",
        headers=normal_headers,
        json={"decision": "verified", "note": "证据充分"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == 40300

    verified = await client.patch(
        f"/api/v1/skills/facts/{facts[0]['id']}/review",
        headers=auth_headers,
        json={"decision": "verified", "note": "岗位原文直接要求"},
    )
    assert verified.status_code == 200
    verified_data = verified.json()["data"]
    assert verified_data["verification_status"] == "verified"
    assert verified_data["reviewer_name"] == "admin"
    assert verified_data["review_note"] == "岗位原文直接要求"
    assert verified_data["reviewed_at"]

    rejected_without_note = await client.patch(
        f"/api/v1/skills/facts/{facts[1]['id']}/review",
        headers=auth_headers,
        json={"decision": "rejected"},
    )
    assert rejected_without_note.status_code == 422

    rejected = await client.patch(
        f"/api/v1/skills/facts/{facts[1]['id']}/review",
        headers=auth_headers,
        json={"decision": "rejected", "note": "证据只描述业务场景"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["verification_status"] == "rejected"

    repeated = await client.patch(
        f"/api/v1/skills/facts/{facts[0]['id']}/review",
        headers=auth_headers,
        json={"decision": "rejected", "note": "重复决策"},
    )
    assert repeated.status_code == 422
    assert repeated.json()["code"] == 40003

    reviewed = await client.get(
        "/api/v1/skills/facts/reviews",
        headers=auth_headers,
        params={"status": "verified", "keyword": verified_data["skill_name"]},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["items"][0]["id"] == facts[0]["id"]
    assert reviewed.json()["data"]["summary"]["verified"] == 1
    assert reviewed.json()["data"]["summary"]["rejected"] == 1
