import scripts.evaluate_competition_readiness as readiness


def test_competition_readiness_aggregates_offline_gates_and_external_boundary():
    report = readiness.run_competition_evaluation()

    assert report["schema_version"] == "competition-readiness-v2"
    assert {item["name"] for item in report["components"]} == {
        "database_package_head", "l45_offline_stability",
        "crawler_checkpoint_semantics", "graph_analytics_contract",
        "fyz_quality", "data_quality", "standardization",
    }
    assert report["summary"] == {"passed": 7, "failed": 0, "error": 0}
    assert report["release_gate"] is True
    assert any("Neo4j" in item for item in report["external_acceptance_required"])


def test_critical_package_gate_failure_blocks_release(monkeypatch):
    monkeypatch.setattr(
        readiness,
        "_database_package_gate",
        lambda: {"passed": False, "alembic_revision": "20260801_0017"},
    )

    report = readiness.run_competition_evaluation()

    package = next(
        item for item in report["components"]
        if item["name"] == "database_package_head"
    )
    assert package["status"] == "failed"
    assert report["release_gate"] is False
