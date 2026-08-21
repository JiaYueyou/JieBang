"""岗位浏览接口测试。"""

from httpx import AsyncClient


SAMPLE_JOB = {
    "id": 7, "title": "Python开发", "standardized_title": "Python 后端工程师",
    "stack": "backend", "company": "测试公司", "city": "合肥",
    "salary_text": "15K-25K", "experience_text": "3-5年",
    "education_text": "本科", "keywords": "Python,FastAPI,MySQL",
    "jd_text": "负责平台后端接口开发", "responsibilities": "接口开发",
    "requirements": "熟悉 Python", "posted_at_text": "2026-08-20",
    "std_job_name": "后端工程师",
}


async def test_position_list_detail_and_errors(client: AsyncClient, monkeypatch):
    from app.repositories.raw_job_repository import RawJobRepository

    async def fake_list(self, **kwargs): return [SAMPLE_JOB], 1
    async def fake_get(self, raw_id): return SAMPLE_JOB if raw_id == 7 else None
    monkeypatch.setattr(RawJobRepository, "list_jobs", fake_list)
    monkeypatch.setattr(RawJobRepository, "get_by_id", fake_get)

    listed = await client.get("/api/v1/positions", params={"keyword": "Python", "page": 1})
    assert listed.status_code == 200
    assert listed.json()["data"]["list"][0]["id"] == "raw-7"
    detail = await client.get("/api/v1/positions/raw-7")
    assert detail.status_code == 200
    assert detail.json()["data"]["required_skills"][0]["name"] == "Python"
    assert (await client.get("/api/v1/positions/bad-id")).status_code == 404
    assert (await client.get("/api/v1/positions/raw-x")).status_code == 404
    assert (await client.get("/api/v1/positions/raw-99")).status_code == 404
    assert (await client.get("/api/v1/positions?page=0")).status_code == 422


async def test_position_graph(client: AsyncClient, monkeypatch):
    from app.services.graph_service import GraphService

    async def fake_panorama(self, **kwargs):
        return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}
    monkeypatch.setattr(GraphService, "panorama", fake_panorama)
    response = await client.get("/api/v1/positions/graph", params={"root_tech": "Python"})
    assert response.status_code == 200
