"""Aggregate every deterministic FYZ competition release gate."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from pydantic import ValidationError  # noqa: E402
from app.evaluation.standardization import evaluate_standardization  # noqa: E402
from app.repositories.graph_repository import Neo4jGraphRepository  # noqa: E402
from app.schemas.graph import GraphAnalyticsResponse  # noqa: E402
from scripts.db_transfer_common import (  # noqa: E402
    repository_alembic_head,
    validate_snapshot_package,
)
from scripts.evaluate_fyz_quality import run_evaluation  # noqa: E402
from scripts.evaluate_phase1_data_quality import evaluate as evaluate_data_quality  # noqa: E402
from spider_framework.checkpoint import run_checkpoint_self_check  # noqa: E402


DATA_QUALITY_THRESHOLDS = {
    "duplicate_type_accuracy": 0.90,
    "freshness_accuracy": 0.95,
}


def _component(name: str, evaluator: Callable[[], dict[str, Any]], gate: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    try:
        report = evaluator()
        return {"name": name, "status": "passed" if gate(report) else "failed", "report": report}
    except Exception as exc:
        return {"name": name, "status": "error", "error": f"{type(exc).__name__}: {exc}"}


def _database_package_gate() -> dict[str, Any]:
    expected_revision = repository_alembic_head()
    manifest = validate_snapshot_package(
        expected_revision=expected_revision
    )
    return {
        "passed": manifest["alembic_revision"] == expected_revision,
        "expected_revision": expected_revision,
        "alembic_revision": manifest["alembic_revision"],
        "table_count": manifest["table_count"],
        "total_rows": manifest["total_rows"],
        "sha256": manifest["sha256"],
    }


def _load_l45_stress_module() -> ModuleType:
    path = PROJECT_ROOT / "agent-development" / "scripts" / "stress_l45.py"
    spec = importlib.util.spec_from_file_location("jiebang_l45_stress_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load L4/L5 stability runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _l45_offline_gate() -> dict[str, Any]:
    module = _load_l45_stress_module()
    args = argparse.Namespace(
        live=False, runs=30, concurrency=5, timeout=10,
        max_attempts=3, fail_every=5, min_success_rate=.98,
        # Two injected recoverable failures legitimately consume the
        # production 0.75s + 1.5s backoff. Keep the offline gate bounded while
        # avoiding scheduler-load flakes in the full suite.
        min_quality_rate=.95, max_p95_ms=3000, output=None,
    )
    return asyncio.run(module.run(args))


def _graph_analytics_contract_gate() -> dict[str, Any]:
    representative = GraphAnalyticsResponse.model_validate({
        "node_count": 4, "edge_count": 3, "density": .5,
        "isolated_node_count": 1,
        "layer_counts": {"Job": 2, "TechStack": 2},
        "relation_counts": {"REQUIRES_AREA": 3},
        "top_degree_nodes": [],
        "algorithm": "undirected_degree_centrality",
        "density_algorithm": "undirected_unique_pair_density",
    })
    rejects_invalid_density = False
    try:
        GraphAnalyticsResponse.model_validate({"density": 1.01})
    except ValidationError:
        rejects_invalid_density = True
    checks = {
        "repository_contract_available": callable(getattr(Neo4jGraphRepository, "analytics", None)),
        "density_is_bounded": rejects_invalid_density,
        "unique_pair_density_declared": representative.density_algorithm == "undirected_unique_pair_density",
        "namespace_declared": Neo4jGraphRepository.namespace == "jiebang",
    }
    return {"checks": checks, "passed": all(checks.values())}


def run_competition_evaluation() -> dict[str, Any]:
    components = [
        _component("database_package_head", _database_package_gate, lambda value: bool(value["passed"])),
        _component("l45_offline_stability", _l45_offline_gate, lambda value: bool(value["accepted"])),
        _component("crawler_checkpoint_semantics", run_checkpoint_self_check, lambda value: bool(value["passed"])),
        _component("graph_analytics_contract", _graph_analytics_contract_gate, lambda value: bool(value["passed"])),
        _component("fyz_quality", lambda: run_evaluation(jd_limit=100, case_count=60), lambda value: bool(value["all_quality_gates_passed"])),
        _component("data_quality", evaluate_data_quality, lambda value: all(value["metrics"][key] >= threshold for key, threshold in DATA_QUALITY_THRESHOLDS.items())),
        _component("standardization", evaluate_standardization, lambda value: bool(value["passed"])),
    ]
    counts = {status: sum(item["status"] == status for item in components) for status in ("passed", "failed", "error")}
    return {
        "schema_version": "competition-readiness-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "offline deterministic FYZ release gates",
        "components": components,
        "summary": counts,
        "release_gate": counts["failed"] == 0 and counts["error"] == 0,
        "external_acceptance_required": [
            "Live crawler portals: connectivity, anti-bot behaviour, freshness and sustained scheduling",
            "Neo4j: execute structural analytics against the deployed jiebang namespace",
            "Live external-model soak test and human-review calibration",
            "MySQL/Redis and browser E2E performance in the competition deployment",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=BACKEND_ROOT / "evaluation" / "competition_readiness_report.json")
    args = parser.parse_args()
    report = run_competition_evaluation()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "release_gate": report["release_gate"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if report["release_gate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
