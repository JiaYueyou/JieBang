from types import SimpleNamespace

from app.api.v1.positions import (
    _parse_keywords_to_skills, _row_to_detail, _row_to_response, _stack_to_category,
)
from app.services.match_service import (
    MatchService, _education_meets, _extract_skills_from_text,
    _parse_education_requirement, _skill_names_match,
)


def test_position_response_mapping_and_keyword_limit():
    assert _stack_to_category("ai") == "new"
    assert _stack_to_category("backend") == "existing"
    skills = _parse_keywords_to_skills("Python, FastAPI, MySQL, Redis, Git, Docker, Linux, SQL, ignored")
    assert len(skills) == 8
    row = {
        "id": 7, "standardized_title": "Python Engineer", "title": "Backend Developer",
        "stack": "ai", "jd_text": "A" * 151, "company": "Test", "city": "Beijing",
        "salary_text": "20K", "experience_text": "3 years", "education_text": "Bachelor",
        "keywords": "Python,FastAPI", "responsibilities": "Build APIs",
        "requirements": "Python", "posted_at_text": "2026-01", "std_job_name": "Engineer",
    }
    summary = _row_to_response(row)
    assert summary["id"] == "raw-7"
    assert summary["summary"].endswith("...")
    detail = _row_to_detail(row)
    assert detail["original_title"] == "Backend Developer"
    assert detail["requirements_text"] == "Python"


def test_match_text_and_education_helpers():
    skills = _extract_skills_from_text("Python FastAPI Docker Kubernetes Redis")
    assert {item.lower() for item in skills} >= {"python", "fastapi", "docker", "kubernetes", "redis"}
    assert _extract_skills_from_text("") == []
    assert _skill_names_match("Python", "python")
    assert not _skill_names_match("", "Python")
    assert _parse_education_requirement("") == ""
    assert _education_meets("", "") is True


def test_match_job_normalizers(db_session):
    service = MatchService(db_session)
    raw = service._normalize_raw_job({
        "id": 1, "standardized_title": "Backend", "requirements": "Python FastAPI",
        "jd_text": "Docker", "keywords": "Python,Redis", "education_text": "",
        "stack": "backend",
    })
    assert raw["source"] == "raw_job_record"
    assert "Python" in raw["all_skills"]

    neo = service._normalize_neo4j_job({
        "id": "job:1", "name": "AI Engineer", "description": "",
        "skills": ["Python"], "tech_points": ["RAG"], "knowledge_points": ["Embedding"],
    })
    assert set(neo["all_skills"]) == {"Python", "RAG", "Embedding"}

    position = SimpleNamespace(
        id=2, name="Backend", summary="Build services", responsibilities=["APIs"]
    )
    mysql = service._normalize_mysql_job(position, [
        {"name": "Python", "kind": "required"}, {"name": "Docker", "kind": "preferred"},
    ])
    assert mysql["required_skills"] == ["Python"]
    assert mysql["preferred_skills"] == ["Docker"]

    resume = SimpleNamespace(education_list=[{"degree": ""}, {"degree": "unknown"}])
    assert service._get_resume_highest_education(resume) == ""

