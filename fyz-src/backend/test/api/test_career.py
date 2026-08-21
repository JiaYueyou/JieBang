from app.services.career_service import CareerService
from app.services.resume_parser import ResumeParser
from test.api.test_internal_transfer import position_payload


class DisabledCareerProvider:
    provider_name = "disabled"
    model_name = "none"
    enabled = False


async def test_career_analysis_requires_authentication(client):
    response = await client.post("/api/v1/career/analyses", json={"skill_text": "Python"})
    assert response.status_code == 401


async def test_resume_text_extraction_and_degraded_career_plan(client, auth_headers):
    extracted = await client.post(
        "/api/v1/career/resume-extractions",
        headers=auth_headers,
        files={"file": ("resume.md", "三年 Python 与 FastAPI 项目经验".encode("utf-8"), "text/markdown")},
    )
    assert extracted.status_code == 200
    resume_text = extracted.json()["data"]["text"]
    created = await client.post(
        "/api/v1/internal-transfer/positions",
        headers=auth_headers,
        json={
            **position_payload(),
            "title": "Python 平台工程师",
            "required_skills": ["Python", "FastAPI", "Redis"],
            "trainable_skills": [],
        },
    )
    job = created.json()["data"]
    await client.put(
        f"/api/v1/internal-transfer/positions/{job['id']}/status",
        headers=auth_headers,
        json={"status": "pending_approval"},
    )
    await client.put(
        f"/api/v1/internal-transfer/positions/{job['id']}/status",
        headers=auth_headers,
        json={"status": "open"},
    )

    response = await client.post(
        "/api/v1/career/analyses",
        headers=auth_headers,
        json={
            "skill_text": "Python, FastAPI",
            "resume_text": resume_text,
            "enterprise_tech": "Redis",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    row = data["recommendations"][0]
    assert row["job_id"] == job["id"]
    assert row["current_match"] == 67
    assert row["internal"] is True
    assert row["learning_plan"][0]["skill"] == "Redis"
    run = await client.get(f"/api/v1/agents/runs/{data['agent_run_id']}", headers=auth_headers)
    assert run.json()["data"]["status"] == "degraded"


async def test_resume_image_extraction_endpoint_uses_ocr(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        ResumeParser,
        "_ocr_image",
        lambda self, content: "AI 工程师\nPython FastAPI Docker",
    )

    response = await client.post(
        "/api/v1/career/resume-extractions",
        headers=auth_headers,
        files={"file": ("resume.jpeg", b"image", "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["text"] == "AI 工程师\nPython FastAPI Docker"
    assert any("OCR" in warning for warning in data["warnings"])


async def test_career_analysis_rejects_empty_input(client, auth_headers):
    response = await client.post("/api/v1/career/analyses", headers=auth_headers, json={})
    assert response.status_code == 422


def test_declared_skills_preserve_free_text_and_cover_equivalent_job_requirements():
    service = CareerService(None, llm_provider=DisabledCareerProvider())

    skills = service._extract_declared_skills(
        "Python，Transformer，LangChain，NLP，机器学习，大模型分布式部署，Claude Code"
    )

    assert "Python" in skills
    assert "Transformer" in skills
    assert "Claude Code" in skills
    assert "大模型分布式部署" in skills
    assert service._skill_is_covered("Transformer", skills)
    assert service._skill_is_covered("自然语言处理", skills)
    assert service._skill_is_covered("有Claude Code使用经验", skills)
    assert service._skill_is_covered("了解分布式训练或模型部署", skills)
    assert not service._skill_is_covered("熟悉大模型微调（LoRA等）", skills)
