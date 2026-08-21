"""匹配与简历优化接口契约测试。"""

import pytest
from httpx import AsyncClient

from app.api.v1.match import get_match_service
from app.api.v1.tailor import get_tailor_service
from app.main import app


MATCH_RESULT = {
    "id": 1, "resume_id": 1, "position_id": "position:2",
    "position_name": "后端工程师", "resume_name": "测试简历", "total_score": 85,
    "dimensions": [], "gap_analysis": {}, "suggestions": [], "reasoning_chain": [],
}


class FakeMatchService:
    async def do_match_by_mysql_id(self, user_id, resume_id, position_id): return MATCH_RESULT
    async def batch_match(self, user_id, resume_id, position_ids): return [MATCH_RESULT]
    async def auto_match(self, user_id, resume_id):
        return {"results": [MATCH_RESULT], "total_matched": 1, "data_source": "test"}
    async def get_result(self, resume_id, position_id): return MATCH_RESULT
    async def get_history(self, user_id): return [MATCH_RESULT]


class FakeTailorService:
    async def get_suggestions(self, resume_id, position_id):
        return [{"id": "sg-1", "section": "skills", "suggested": "突出 Python"}]
    async def accept_suggestion(self, resume_id, suggestion_id): return None
    async def apply_all(self, resume_id, suggestion_ids, payload): return 12
    async def optimize_phrase(self, text, style): return ["负责核心接口设计与开发"]
    async def save_as_new(self, resume_id, suggestion_ids, payload): return 13


@pytest.fixture(autouse=True)
def service_overrides():
    app.dependency_overrides[get_match_service] = lambda: FakeMatchService()
    app.dependency_overrides[get_tailor_service] = lambda: FakeTailorService()
    yield
    app.dependency_overrides.pop(get_match_service, None)
    app.dependency_overrides.pop(get_tailor_service, None)


async def test_match_endpoints(client: AsyncClient, auth_headers: dict):
    calls = [
        ("POST", "/api/v1/match", {"resume_id": 1, "position_id": 2}),
        ("POST", "/api/v1/match/batch", {"resume_id": 1, "position_ids": [2, 3]}),
        ("POST", "/api/v1/match/auto/1", None),
        ("GET", "/api/v1/match/result/1/2", None),
        ("GET", "/api/v1/match/history", None),
    ]
    for method, url, body in calls:
        response = await client.request(method, url, json=body, headers=auth_headers)
        assert response.status_code == 200, (url, response.text)
    assert (await client.post("/api/v1/match/batch", json={"resume_id": 1, "position_ids": []}, headers=auth_headers)).status_code == 422


async def test_tailor_endpoints(client: AsyncClient):
    suggestion = {"id": "sg-1", "section": "skills", "suggested": "突出 Python"}
    calls = [
        ("GET", "/api/v1/tailor/suggestions/1/raw-2", None),
        ("POST", "/api/v1/tailor/accept", {"resume_id": 1, "suggestion_id": "sg-1"}),
        ("POST", "/api/v1/tailor/apply-all", {"resume_id": 1, "suggestion_ids": ["sg-1"], "suggestions": [suggestion]}),
        ("POST", "/api/v1/tailor/optimize-phrase", {"text": "做了接口", "style": "professional"}),
        ("POST", "/api/v1/tailor/save-as-new", {"resume_id": 1, "suggestion_ids": ["sg-1"], "suggestions": [suggestion]}),
    ]
    for method, url, body in calls:
        response = await client.request(method, url, json=body)
        assert response.status_code == 200, (url, response.text)
