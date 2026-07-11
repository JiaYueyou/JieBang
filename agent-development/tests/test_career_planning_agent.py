from jiebang_agents.career_planning import CareerPlanCandidate, CareerPlanningAgent


class DisabledProvider:
    provider_name = "disabled"
    model_name = "none"
    enabled = False


async def test_template_plan_preserves_deterministic_job_and_scores():
    candidate = CareerPlanCandidate(
        job_id=7,
        job="平台工程师",
        current_match=50,
        after_match=80,
        recommend_score=58,
        existing=["Python"],
        gaps=["FastAPI", "Redis"],
        internal=True,
    )

    output = await CareerPlanningAgent(DisabledProvider()).generate(
        resume_text="Python 项目经验",
        skills=["Python"],
        enterprise_tech="FastAPI, Redis",
        candidates=[candidate],
        time_budget_weeks=8,
    )

    row = output.recommendations[0]
    assert row.job_id == 7
    assert row.current_match == 50
    assert row.after_match == 80
    assert [step.skill for step in row.learning_plan] == ["FastAPI", "Redis"]
