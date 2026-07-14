from jiebang_agents.career_planning import CareerPlanCandidate, CareerPlanningAgent
from jiebang_agents.career_planning.schemas import (
    LLMCareerAnalysis,
    LLMRecommendation,
    LearningStep,
    ResumeProfile,
)


class DisabledProvider:
    provider_name = "disabled"
    model_name = "none"
    enabled = False


class FakeProvider:
    provider_name = "fake"
    model_name = "fake-structured"
    enabled = True

    def __init__(self, output):
        self.output = output

    async def generate_structured(self, **_kwargs):
        return self.output


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


async def test_model_plan_is_limited_to_each_roles_real_gaps():
    candidates = [
        CareerPlanCandidate(
            job_id=1,
            job="大模型应用开发",
            current_match=40,
            after_match=80,
            recommend_score=40,
            existing=["Python"],
            gaps=["Transformer", "RAG"],
        ),
        CareerPlanCandidate(
            job_id=2,
            job="Python数据分析",
            current_match=40,
            after_match=80,
            recommend_score=40,
            existing=["Python"],
            gaps=["SPSS", "Origin"],
        ),
    ]
    provider = FakeProvider(LLMCareerAnalysis(
        resume_profile=ResumeProfile(),
        recommendations=[
            LLMRecommendation(
                job_id=1,
                learning_plan=[
                    LearningStep(skill="Python", time="1 周", difficulty="easy"),
                    LearningStep(skill="Transformer架构深入", time="2 周", difficulty="hard"),
                    LearningStep(skill="Kubernetes基础", time="1 周", difficulty="medium"),
                ],
                suggested_project="通用练习项目",
                total_time="4 周",
            ),
            LLMRecommendation(
                job_id=2,
                learning_plan=[
                    LearningStep(skill="SPSS实践", time="2 周", difficulty="medium"),
                    LearningStep(skill="Python", time="1 周", difficulty="easy"),
                ],
                suggested_project="通用练习项目",
                total_time="3 周",
            ),
        ],
    ))

    output = await CareerPlanningAgent(provider).generate(
        resume_text="Python 项目经验",
        skills=["Python"],
        enterprise_tech="",
        candidates=candidates,
        time_budget_weeks=8,
    )

    first, second = output.recommendations
    assert [step.skill for step in first.learning_plan] == ["Transformer", "RAG"]
    assert [step.skill for step in second.learning_plan] == ["SPSS", "Origin"]
    assert first.suggested_project != second.suggested_project
    assert "Python数据分析" in second.suggested_project
