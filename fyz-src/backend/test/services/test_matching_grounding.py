"""Phase 3 grounding tests for Match Explanation Agent."""

from sqlalchemy import delete, select

from app.core.database import async_session
from app.models import (
    AgentClaimCitation,
    AgentRun,
    MatchEvidence,
)
from app.services.matching_service import MatchingService
from jiebang_agents.match_explanation.schemas import (
    ExplanationItem,
    LLMMatchExplanation,
)


class _Provider:
    enabled = True
    provider_name = "mock"
    model_name = "mock-match"

    def __init__(
        self,
        output: LLMMatchExplanation | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.output = output
        self.error = error

    async def generate_structured(self, **_kwargs):
        if self.error:
            raise self.error
        return self.output


class _DisabledProvider:
    enabled = False
    provider_name = "disabled"
    model_name = "disabled"


async def _seed_match(
    client,
    auth_headers,
) -> tuple[int, dict[str, int], dict]:
    from test.api.test_jobs import create_job

    await create_job(
        client,
        auth_headers,
        title="Python 工程师",
        skills=["Python", "Redis"],
    )
    uploaded = await client.post(
        "/api/v1/resumes",
        headers=auth_headers,
        files={
            "file": (
                "resume.txt",
                "Python 项目经验".encode(),
                "text/plain",
            )
        },
    )
    match_snapshot = uploaded.json()["data"]["matches"][0]
    match_id = match_snapshot["id"]
    async with async_session() as db:
        rows = list(
            (
                await db.execute(
                    select(MatchEvidence).where(
                        MatchEvidence.match_id == match_id
                    )
                )
            ).scalars()
        )
    return (
        match_id,
        {item.skill_name: item.id for item in rows},
        match_snapshot,
    )


async def test_match_explanation_persists_valid_snapshot_citations(
    client,
    auth_headers,
):
    match_id, evidence_ids, _ = await _seed_match(
        client,
        auth_headers,
    )
    python_ref = f"match_evidence:{evidence_ids['Python']}"
    redis_ref = f"match_evidence:{evidence_ids['Redis']}"
    provider = _Provider(
        LLMMatchExplanation(
            summary="该文本不会直接成为最终 Summary。",
            strengths=[
                ExplanationItem(
                    title="Python",
                    explanation="简历包含 Python 项目经验。",
                    evidence_ids=[python_ref],
                )
            ],
            gaps=[
                ExplanationItem(
                    title="Redis",
                    explanation="岗位要求 Redis，但简历未发现。",
                    evidence_ids=[redis_ref],
                )
            ],
            risks=[
                ExplanationItem(
                    title="Redis",
                    explanation="Redis 技能缺口需要面试核验。",
                    evidence_ids=[redis_ref],
                )
            ],
            interview_suggestions=["模型自由生成的建议不会直接采用"],
        )
    )

    async with async_session() as db:
        result = await MatchingService(
            db,
            llm_provider=provider,
        ).explain(match_id, user_id=1)
        run = await db.get(AgentRun, result.agent_run_id)
        citations = list(
            (
                await db.execute(
                    select(AgentClaimCitation).where(
                        AgentClaimCitation.agent_run_id == result.agent_run_id
                    )
                )
            ).scalars()
        )

    assert result.generation_mode == "llm"
    assert result.summary.startswith("已基于保存证据验证")
    assert [item["title"] for item in result.strengths] == ["Python"]
    assert [item["title"] for item in result.gaps] == ["Redis"]
    assert [item["title"] for item in result.risks] == ["Redis"]
    assert result.interview_suggestions == [
        "围绕 Python 准备可验证的项目案例。"
    ]
    assert run.status == "succeeded"
    assert run.structured_output["fallback_reason"] is None
    assert len(citations) == 3
    assert {item.citation_source_type for item in citations} == {
        "match_evidence"
    }
    assert {item.evidence_id for item in citations} == {None}
    assert {item.citation_ref for item in citations} == {
        str(evidence_ids["Python"]),
        str(evidence_ids["Redis"]),
    }


async def test_match_strength_accepts_saved_skill_anchor_for_legacy_excerpt(
    client,
    auth_headers,
):
    match_id, evidence_ids, _ = await _seed_match(client, auth_headers)
    async with async_session() as db:
        evidence = await db.get(MatchEvidence, evidence_ids["Python"])
        evidence.evidence_text = "参与过后端服务重构项目"
        await db.commit()

    provider = _Provider(
        LLMMatchExplanation(
            summary="技能匹配",
            strengths=[ExplanationItem(
                title="匹配技能：Python",
                explanation="候选人具备岗位要求的 Python 技能。",
                evidence_ids=[f"match_evidence:{evidence_ids['Python']}"],
            )],
            gaps=[],
            risks=[],
            interview_suggestions=[],
        )
    )
    async with async_session() as db:
        result = await MatchingService(db, llm_provider=provider).explain(
            match_id, user_id=1
        )

    assert [item["title"] for item in result.strengths] == ["匹配技能：Python"]


async def test_unknown_citations_trigger_deterministic_template(
    client,
    auth_headers,
):
    match_id, _, match_snapshot = await _seed_match(
        client,
        auth_headers,
    )
    provider = _Provider(
        LLMMatchExplanation(
            summary="伪造结果",
            strengths=[
                ExplanationItem(
                    title="Go",
                    explanation="不存在的 Go 经验。",
                    evidence_ids=["match_evidence:999999"],
                )
            ],
            gaps=[],
            risks=[],
            interview_suggestions=[],
        )
    )

    async with async_session() as db:
        result = await MatchingService(
            db,
            llm_provider=provider,
        ).explain(match_id, user_id=1)
        run = await db.get(AgentRun, result.agent_run_id)
        citations = list(
            (
                await db.execute(
                    select(AgentClaimCitation).where(
                        AgentClaimCitation.agent_run_id == result.agent_run_id
                    )
                )
            ).scalars()
        )

    assert result.generation_mode == "template"
    assert [item["title"] for item in result.strengths] == ["Python"]
    assert [item["title"] for item in result.gaps] == match_snapshot[
        "missing"
    ]
    assert all(item.citation_ref != "999999" for item in citations)
    assert run.status == "degraded"
    assert (
        run.structured_output["fallback_reason"]
        == "insufficient_grounding"
    )
    assert (
        run.structured_output["model_validation"]["claims"][0][
            "reasons"
        ]
        == ["unknown_evidence_id", "insufficient_independent_sources"]
    )
    assert "已使用确定性模板" in " ".join(result.warnings)


async def test_partially_invalid_risk_is_removed_without_rewriting_score(
    client,
    auth_headers,
):
    match_id, evidence_ids, match_snapshot = await _seed_match(
        client,
        auth_headers,
    )
    provider = _Provider(
        LLMMatchExplanation(
            summary="部分有效",
            strengths=[
                ExplanationItem(
                    title="Python",
                    explanation="简历包含 Python 项目经验。",
                    evidence_ids=[
                        f"match_evidence:{evidence_ids['Python']}"
                    ],
                )
            ],
            gaps=[],
            risks=[
                ExplanationItem(
                    title="薪资风险",
                    explanation="模型编造的薪资判断。",
                    evidence_ids=["match_evidence:999999"],
                )
            ],
            interview_suggestions=[],
        )
    )

    async with async_session() as db:
        result = await MatchingService(
            db,
            llm_provider=provider,
        ).explain(match_id, user_id=1)
        run = await db.get(AgentRun, result.agent_run_id)

    assert result.score == match_snapshot["score"]
    assert [item["title"] for item in result.strengths] == ["Python"]
    assert result.risks == []
    assert result.generation_mode == "llm"
    assert run.status == "degraded"
    assert run.structured_output["validation"]["status"] == "partial"
    assert "已过滤" in " ".join(result.warnings)


async def test_no_saved_evidence_returns_explicit_no_answer(
    client,
    auth_headers,
):
    match_id, _, _ = await _seed_match(client, auth_headers)
    async with async_session() as db:
        await db.execute(
            delete(MatchEvidence).where(
                MatchEvidence.match_id == match_id
            )
        )
        await db.commit()

    async with async_session() as db:
        result = await MatchingService(
            db,
            llm_provider=_DisabledProvider(),
        ).explain(match_id, user_id=1)
        run = await db.get(AgentRun, result.agent_run_id)
        citation_count = len(
            list(
                (
                    await db.execute(
                        select(AgentClaimCitation).where(
                            AgentClaimCitation.agent_run_id
                            == result.agent_run_id
                        )
                    )
                ).scalars()
            )
        )

    assert result.generation_mode == "template"
    assert result.strengths == []
    assert result.gaps == []
    assert result.risks == []
    assert result.summary == "当前没有足够的已保存证据生成匹配解释。"
    assert "证据不足" in " ".join(result.warnings)
    assert run.status == "degraded"
    assert citation_count == 0


async def test_llm_failure_records_fallback_reason(
    client,
    auth_headers,
):
    match_id, _, _ = await _seed_match(client, auth_headers)
    async with async_session() as db:
        result = await MatchingService(
            db,
            llm_provider=_Provider(
                error=RuntimeError("mock timeout")
            ),
        ).explain(match_id, user_id=1)
        run = await db.get(AgentRun, result.agent_run_id)

    assert result.generation_mode == "template"
    assert run.status == "degraded"
    assert run.error_code == "RuntimeError"
    assert run.structured_output["fallback_reason"] == "llm_failed"
