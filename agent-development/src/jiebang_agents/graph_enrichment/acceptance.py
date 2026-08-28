"""Deterministic L4/L5 output acceptance checks used by tests and load runs."""

import math
from dataclasses import asdict, dataclass, field

from jiebang_agents.graph_enrichment.schemas import (
    GraphEnrichmentOutput,
    SkillGraphCompletionInput,
)


@dataclass(frozen=True)
class L45AcceptanceReport:
    passed: bool
    issue_codes: list[str] = field(default_factory=list)
    tech_point_count: int = 0
    knowledge_point_count: int = 0
    minimum_confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def nearest_rank_percentile(values: list[int | float], percentile: float) -> int | float:
    """Return the nearest-rank percentile (rank = ceil(P * N))."""
    if not values:
        raise ValueError("values must not be empty")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def evaluate_l45_output(
    request: SkillGraphCompletionInput,
    output: GraphEnrichmentOutput,
    *,
    minimum_confidence: float = 0.75,
) -> L45AcceptanceReport:
    """Apply release-level structural and evidence gates without model calls."""
    issues: set[str] = set()
    known_ids = {item.evidence_id for item in request.evidence}
    tech_names: set[str] = set()
    knowledge_names: set[tuple[str, str]] = set()
    knowledge_count = 0

    if not output.tech_points:
        issues.add("missing_l4")
    for point in output.tech_points:
        point_key = point.name.strip().casefold()
        if point_key in tech_names:
            issues.add("duplicate_l4")
        tech_names.add(point_key)
        _check_claim(
            point.confidence,
            point.evidence_ids,
            known_ids,
            minimum_confidence,
            issues,
        )
        if not point.knowledge_points:
            issues.add("missing_l5_for_l4")
        for knowledge in point.knowledge_points:
            knowledge_count += 1
            knowledge_key = (point_key, knowledge.name.strip().casefold())
            if knowledge_key in knowledge_names:
                issues.add("duplicate_l5")
            knowledge_names.add(knowledge_key)
            _check_claim(
                knowledge.confidence,
                knowledge.evidence_ids,
                known_ids,
                minimum_confidence,
                issues,
            )

    return L45AcceptanceReport(
        passed=not issues,
        issue_codes=sorted(issues),
        tech_point_count=len(output.tech_points),
        knowledge_point_count=knowledge_count,
        minimum_confidence=minimum_confidence,
    )


def _check_claim(
    confidence: float,
    evidence_ids: list[str],
    known_ids: set[str],
    minimum_confidence: float,
    issues: set[str],
) -> None:
    citations = {value for value in evidence_ids if value}
    if confidence < minimum_confidence:
        issues.add("low_confidence_claim")
    if len(citations) < 2:
        issues.add("insufficient_citations")
    if citations - known_ids:
        issues.add("unknown_citation")
