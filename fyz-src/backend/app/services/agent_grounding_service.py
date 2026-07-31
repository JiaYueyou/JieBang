"""Shared post-generation grounding gate for evidence-backed Agent claims."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentClaimCitation, MatchEvidence
from app.schemas.retrieval import RetrievedEvidence

_ASCII_TOKEN = re.compile(r"[a-z0-9][a-z0-9+#._-]+")
_CJK_BLOCK = re.compile(r"[\u3400-\u9fff]+")


@dataclass(frozen=True)
class GroundedClaim:
    """A generated statement and the Evidence IDs claimed to support it."""

    claim_id: str
    claim_type: str
    claim_text: str
    anchor_text: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class GroundingEvidence:
    """Normalized citation source used by the shared validation engine."""

    citation_id: str
    citation_source_type: str
    citation_ref: str
    text: str
    platform: str
    quality_score: float
    verification_status: str
    posted_at: datetime | None
    evidence_chunk_id: str | None = None
    source_metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ClaimGroundingResult:
    claim_id: str
    accepted: bool
    grounding_score: float
    evidence_ids: tuple[str, ...]
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass
class AgentGroundingReport:
    results: list[ClaimGroundingResult] = field(default_factory=list)

    @property
    def accepted_claim_ids(self) -> set[str]:
        return {item.claim_id for item in self.results if item.accepted}

    @property
    def accepted_count(self) -> int:
        return len(self.accepted_claim_ids)

    @property
    def rejected_count(self) -> int:
        return len(self.results) - self.accepted_count

    def to_dict(self) -> dict:
        return {
            "status": (
                "passed"
                if self.results and self.rejected_count == 0
                else "partial"
                if self.accepted_count
                else "rejected"
            ),
            "accepted_claim_count": self.accepted_count,
            "rejected_claim_count": self.rejected_count,
            "claims": [
                {
                    "claim_id": item.claim_id,
                    "accepted": item.accepted,
                    "grounding_score": item.grounding_score,
                    "evidence_ids": list(item.evidence_ids),
                    "reasons": list(item.reasons),
                    "warnings": list(item.warnings),
                }
                for item in self.results
            ],
        }


class AgentGroundingService:
    """Validate citations and persist only claims that pass the grounding gate."""

    allowed_verification_statuses = {
        "human_approved",
        "machine_validated",
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate_and_persist(
        self,
        *,
        agent_run_id: str,
        claims: list[GroundedClaim],
        evidence: list[RetrievedEvidence],
        minimum_sources: int = 1,
        minimum_quality_score: float = 0.55,
        maximum_age_days: int = 1095,
        minimum_semantic_score: float = 0.12,
    ) -> AgentGroundingReport:
        normalized = [
            GroundingEvidence(
                citation_id=item.evidence_id,
                citation_source_type="evidence_chunk",
                citation_ref=item.evidence_id,
                text=item.chunk_text,
                platform=item.source_platform,
                quality_score=float(item.quality_score),
                verification_status=item.verification_status,
                posted_at=item.posted_at,
                evidence_chunk_id=item.evidence_id,
                source_metadata={
                    "source_document_id": item.source_document_id,
                    "raw_job_record_id": item.raw_job_record_id,
                    "standard_job_id": item.standard_job_id,
                    "skill_id": item.skill_id,
                    "source_platform": item.source_platform,
                    "index_version": item.index_version,
                },
            )
            for item in evidence
        ]
        return await self._validate_and_persist(
            agent_run_id=agent_run_id,
            claims=claims,
            evidence=normalized,
            minimum_sources=minimum_sources,
            minimum_quality_score=minimum_quality_score,
            maximum_age_days=maximum_age_days,
            minimum_semantic_score=minimum_semantic_score,
            allowed_verification_statuses=(
                self.allowed_verification_statuses
            ),
            warn_unknown_time=True,
        )

    async def validate_match_and_persist(
        self,
        *,
        agent_run_id: str,
        claims: list[GroundedClaim],
        evidence: list[MatchEvidence],
        minimum_semantic_score: float = 0.12,
    ) -> AgentGroundingReport:
        """Validate claims against the immutable saved match snapshot."""

        normalized = [
            GroundingEvidence(
                citation_id=f"match_evidence:{item.id}",
                citation_source_type="match_evidence",
                citation_ref=str(item.id),
                text=item.evidence_text,
                platform=item.evidence_type,
                quality_score=1.0,
                verification_status="saved_snapshot",
                posted_at=None,
                source_metadata={
                    "match_evidence_id": item.id,
                    "match_id": item.match_id,
                    "evidence_type": item.evidence_type,
                    "skill_name": item.skill_name,
                    "source_ref": item.source_ref,
                },
            )
            for item in evidence
        ]
        return await self._validate_and_persist(
            agent_run_id=agent_run_id,
            claims=claims,
            evidence=normalized,
            minimum_sources=1,
            minimum_quality_score=0,
            maximum_age_days=None,
            minimum_semantic_score=minimum_semantic_score,
            allowed_verification_statuses={"saved_snapshot"},
            warn_unknown_time=False,
        )

    async def _validate_and_persist(
        self,
        *,
        agent_run_id: str,
        claims: list[GroundedClaim],
        evidence: list[GroundingEvidence],
        minimum_sources: int,
        minimum_quality_score: float,
        maximum_age_days: int | None,
        minimum_semantic_score: float,
        allowed_verification_statuses: set[str],
        warn_unknown_time: bool,
    ) -> AgentGroundingReport:
        evidence_by_id = {
            item.citation_id: item for item in evidence
        }
        report = AgentGroundingReport()

        # The operation is idempotent for a retried Agent run.
        await self.db.execute(
            delete(AgentClaimCitation).where(
                AgentClaimCitation.agent_run_id == agent_run_id
            )
        )

        for claim in claims:
            unique_ids = tuple(dict.fromkeys(claim.evidence_ids))
            reasons: list[str] = []
            warnings: list[str] = []
            cited = [
                evidence_by_id[evidence_id]
                for evidence_id in unique_ids
                if evidence_id in evidence_by_id
            ]
            missing_ids = [
                evidence_id
                for evidence_id in unique_ids
                if evidence_id not in evidence_by_id
            ]

            if not unique_ids:
                reasons.append("missing_citation")
            if missing_ids:
                reasons.append("unknown_evidence_id")
            if any(
                item.verification_status
                not in allowed_verification_statuses
                for item in cited
            ):
                reasons.append("unverified_evidence")
            if any(
                float(item.quality_score) < minimum_quality_score
                for item in cited
            ):
                reasons.append("low_quality_evidence")

            stale_ids = (
                [
                    item.citation_id
                    for item in cited
                    if self._is_stale(
                        item.posted_at,
                        maximum_age_days,
                    )
                ]
                if maximum_age_days is not None
                else []
            )
            if stale_ids:
                reasons.append("stale_evidence")
            if (
                warn_unknown_time
                and cited
                and any(item.posted_at is None for item in cited)
            ):
                warnings.append("evidence_time_unknown")

            source_count = len(
                {item.platform.strip().casefold() for item in cited}
            )
            if source_count < minimum_sources:
                reasons.append("insufficient_independent_sources")

            semantic_scores = [
                semantic_grounding_score(
                    claim.anchor_text,
                    claim.claim_text,
                    item.text,
                )
                for item in cited
            ]
            grounding_score = min(semantic_scores, default=0.0)
            if cited and grounding_score < minimum_semantic_score:
                reasons.append("semantic_mismatch")

            accepted = not reasons
            result = ClaimGroundingResult(
                claim_id=claim.claim_id,
                accepted=accepted,
                grounding_score=round(grounding_score, 6),
                evidence_ids=unique_ids,
                reasons=tuple(dict.fromkeys(reasons)),
                warnings=tuple(dict.fromkeys(warnings)),
            )
            report.results.append(result)
            if not accepted:
                continue

            self.db.add_all(
                [
                    AgentClaimCitation(
                        agent_run_id=agent_run_id,
                        claim_id=claim.claim_id,
                        claim_type=claim.claim_type,
                        claim_text=claim.claim_text,
                        evidence_id=item.evidence_chunk_id,
                        citation_source_type=(
                            item.citation_source_type
                        ),
                        citation_ref=item.citation_ref,
                        source_metadata=item.source_metadata,
                        grounding_score=result.grounding_score,
                        validation_status="machine_validated",
                    )
                    for item in cited
                ]
            )

        await self.db.flush()
        return report

    @staticmethod
    def _is_stale(
        posted_at: datetime | None,
        maximum_age_days: int | None,
    ) -> bool:
        if posted_at is None or maximum_age_days is None:
            return False
        normalized = posted_at
        if normalized.tzinfo is not None:
            normalized = normalized.astimezone(timezone.utc).replace(
                tzinfo=None
            )
        return datetime.utcnow() - normalized > timedelta(
            days=maximum_age_days
        )


def semantic_grounding_score(
    anchor_text: str,
    claim_text: str,
    evidence_text: str,
) -> float:
    """Return a deterministic lexical-semantic support score in ``[0, 1]``.

    The gate intentionally avoids a second model call. Exact normalized anchor
    matches receive full credit; otherwise ASCII terms and CJK bi/tri-grams
    provide a conservative, reproducible overlap signal.
    """

    anchor = _compact(anchor_text)
    evidence = _compact(evidence_text)
    if anchor and anchor in evidence:
        return 1.0

    claim_tokens = _support_tokens(claim_text)
    evidence_tokens = _support_tokens(evidence_text)
    if not claim_tokens or not evidence_tokens:
        return 0.0
    overlap = claim_tokens & evidence_tokens
    return min(1.0, len(overlap) / max(1, len(claim_tokens)))


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value.casefold())


def _support_tokens(value: str) -> set[str]:
    normalized = value.casefold()
    tokens = set(_ASCII_TOKEN.findall(normalized))
    for block in _CJK_BLOCK.findall(normalized):
        for size in (2, 3):
            tokens.update(
                block[index : index + size]
                for index in range(max(0, len(block) - size + 1))
            )
    return tokens
