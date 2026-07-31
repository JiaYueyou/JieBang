from app.providers.vector_store import ChromaVectorStore


async def test_chroma_vector_store_persists_vectors_and_applies_metadata():
    store = ChromaVectorStore(mode="ephemeral")
    version = "test-chroma-vector-store"
    base_metadata = {
        "namespace": "jiebang",
        "index_version": version,
        "standard_job_id": 1,
        "source_platform": "测试来源",
        "quality_score": 0.9,
        "verification_status": "human_approved",
        "posted_at_epoch": 0,
        "near_duplicate_group_id": "",
    }

    collection_name = await store.sync_index(
        index_version=version,
        dimension=3,
        records=[
            {
                "evidence_id": "ev-java",
                "embedding": [1.0, 0.0, 0.0],
                "document": "Java 服务开发",
                "metadata": {**base_metadata, "skill_id": 11},
            },
            {
                "evidence_id": "ev-python",
                "embedding": [0.0, 1.0, 0.0],
                "document": "Python 服务开发",
                "metadata": {**base_metadata, "skill_id": 12},
            },
        ],
    )
    scores = await store.query(
        index_version=version,
        embedding=[1.0, 0.0, 0.0],
        limit=5,
        where={
            "$and": [
                {"skill_id": {"$in": [11]}},
                {"quality_score": {"$gte": 0.5}},
            ]
        },
    )

    assert collection_name.startswith("jiebang-evidence-")
    assert scores == {"ev-java": 1.0}
