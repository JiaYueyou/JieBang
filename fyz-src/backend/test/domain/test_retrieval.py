from app.domain.retrieval import (
    HashEmbeddingProvider,
    build_evidence_window,
    build_index_text,
    cosine_similarity,
    lexical_score,
    match_authoritative_labels,
)


async def test_hash_embedding_is_deterministic_and_query_sensitive():
    provider = HashEmbeddingProvider(dimension=64)
    first, second, unrelated = await provider.embed_texts(
        [
            "Python FastAPI 服务开发",
            "Python FastAPI 服务开发",
            "品牌运营与市场活动",
        ]
    )

    assert first == second
    assert cosine_similarity(first, second) == 1
    assert cosine_similarity(first, unrelated) < 1


def test_evidence_window_has_stable_id_and_original_offsets():
    jd_text = "负责 Python 服务开发，熟悉 FastAPI、MySQL 和接口测试。"
    first = build_evidence_window(
        fact_id=12,
        raw_job_record_id=7,
        skill_id=3,
        jd_text=jd_text,
        evidence_text="熟悉 FastAPI",
        skill_name="FastAPI",
    )
    second = build_evidence_window(
        fact_id=12,
        raw_job_record_id=7,
        skill_id=3,
        jd_text=jd_text + " 加分项：Docker。",
        evidence_text="熟悉 FastAPI",
        skill_name="FastAPI",
    )

    assert first.evidence_id == second.evidence_id
    assert first.text in jd_text
    assert first.char_start == 0
    assert first.char_end == len(jd_text)
    assert lexical_score("Python FastAPI", first.text) > 0

    index_text = build_index_text(
        standard_job_name="Python 后端工程师",
        skill_name="FastAPI",
        chunk_text=first.text,
    )
    assert index_text.startswith("Python 后端工程师\nFastAPI\n")


def test_index_text_adds_skill_aliases_and_semantic_context():
    index_text = build_index_text(
        standard_job_name="Java开发工程师",
        skill_name="MyBatis",
        skill_aliases=["mybatis-plus"],
        chunk_text="熟悉主流 Java 开发框架",
    )

    assert "mybatis-plus" in index_text
    assert "持久化层" in index_text
    assert "数据库访问框架" in index_text


def test_authoritative_labels_remove_job_title_before_skill_matching():
    jobs, skills = match_authoritative_labels(
        "Java开发工程师需要掌握哪些 Spring Boot 相关能力",
        standard_jobs={1: "Java开发工程师", 2: "测试工程师"},
        skills={11: "Java", 12: "Spring", 13: "Spring Boot"},
    )

    assert jobs == {1}
    assert skills == {13}


def test_authoritative_labels_use_boundaries_for_short_ascii_skills():
    jobs, skills = match_authoritative_labels(
        "quantum photolithography calibration",
        standard_jobs={1: "系统架构师"},
        skills={6: "C", 9: "C++", 11: "Java"},
    )
    assert jobs == set()
    assert skills == set()

    _, exact_skills = match_authoritative_labels(
        "需要 C++ 和 C 开发能力",
        standard_jobs={},
        skills={6: "C", 9: "C++"},
    )
    assert exact_skills == {6, 9}
