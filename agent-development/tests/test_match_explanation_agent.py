from jiebang_agents.match_explanation import MatchEvidenceInput, MatchExplanationAgent, MatchExplanationRequest
from jiebang_agents.match_explanation.schemas import ExplanationItem, LLMMatchExplanation


class Provider:
    provider_name = "mock"
    model_name = "mock"
    enabled = True

    async def generate_structured(self, **_kwargs):
        return LLMMatchExplanation(
            summary="Python 证据充分。",
            strengths=[
                ExplanationItem(
                    title="Python",
                    explanation="已验证",
                    evidence_ids=["match_evidence:1", "unknown:999"],
                )
            ],
            gaps=[], risks=[], interview_suggestions=[],
        )


async def test_explanation_preserves_snapshot_for_backend_grounding_gate():
    request = MatchExplanationRequest(
        match_id=9, resume_id=3, job_id=7, job_title="后端工程师", score=50,
        matched_skills=["Python"], missing_skills=["Redis"],
        evidence=[
            MatchEvidenceInput(
                evidence_id="match_evidence:1",
                evidence_type="resume_skill",
                skill_name="Python",
                evidence_text="Python 项目",
                source_ref={},
            )
        ],
    )
    output = await MatchExplanationAgent(Provider()).generate(request)
    assert output.match_id == 9
    assert output.score == 50
    assert output.matched_skills == ["Python"]
    assert output.missing_skills == ["Redis"]
    assert output.strengths[0].evidence_ids == [
        "match_evidence:1",
        "unknown:999",
    ]
