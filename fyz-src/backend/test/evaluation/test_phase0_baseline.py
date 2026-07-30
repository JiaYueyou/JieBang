from app.evaluation.phase0_baseline import (
    build_report,
    collect_relational_baseline,
    rag_decision,
    render_markdown,
)


async def test_relational_baseline_collects_empty_test_database():
    from app.core.database import async_session

    async with async_session() as session:
        result = await collect_relational_baseline(session)

    assert result["connected"] is True
    assert result["dialect"] == "sqlite"
    assert result["counts"]["agent_run"] == 0
    assert result["statuses"]["async_task"] == {}


def test_rag_decision_requires_confirmed_vector_capability():
    no_vector = rag_decision(
        {"connected": True, "vector": {"supported": False}}
    )
    vector = rag_decision(
        {"connected": True, "vector": {"supported": True}}
    )

    assert no_vector["selected_phase1_backend"] == "local_rebuildable_vector_index"
    assert vector["selected_phase1_backend"] == "neo4j_vector_index_pilot"


def test_markdown_report_contains_decision():
    report = build_report(
        git={"head": "abc", "branch": "test", "dirty": False, "changed_entry_count": 0},
        relational={
            "dialect": "sqlite",
            "alembic_revision": None,
            "counts": {"agent_run": 0},
            "statuses": {"agent_run": {}},
            "agent_metrics": [],
            "latest_graph_snapshot": None,
        },
        neo4j={
            "connected": False,
            "server": None,
            "counts": None,
            "vector": {"supported": False, "procedures": [], "functions": []},
        },
    )

    markdown = render_markdown(report)
    assert "# FYZ Phase 0 基线报告" in markdown
    assert "local_rebuildable_vector_index" in markdown
