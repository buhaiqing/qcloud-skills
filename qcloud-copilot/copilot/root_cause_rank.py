"""SLO/business-impact driven root cause ranking (P0-5).

Provides ``BusinessContext``, ``CandidateRootCause``, ``RankResult`` and
``RootCauseRanker`` to sort candidate root causes by a weighted formula over
evidence strength, topology distance, time correlation, business impact and
historical prior, with multiplicative window adjustments for core hours,
release windows and maintenance windows.

See ``docs/superpowers/specs/slo-root-cause-ranking-design.md``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# Customer-tier → impact weight.
TIER_WEIGHTS: dict[str, float] = {
    "platinum": 1.0,
    "gold": 0.8,
    "silver": 0.5,
    "internal": 0.2,
}

# Request rate above which impact from request_rate saturates at 1.0.
RATE_NORMALIZER: float = 1000.0


@dataclass
class BusinessContext:
    """Business context that shapes the impact of a candidate root cause."""

    service: str
    business_chain: str
    customer_tier: str
    request_rate: float
    error_budget_consumed: float
    core_hours: bool = False
    release_window: bool = False
    maintenance_window: bool = False


@dataclass
class CandidateRootCause:
    """A single candidate root cause to be ranked."""

    candidate_id: str
    resource: str
    evidence_strength: float
    topology_distance: int
    time_correlation: float
    historical_prior: float
    business_impact: float | None = None
    priority: float = 0.0


@dataclass
class RankResult:
    """Ranked outcome for one candidate root cause."""

    candidate_id: str
    score: float
    priority: float
    components: dict[str, float] = field(default_factory=dict)
    resource: str = ""


def default_weights() -> dict[str, float]:
    """Default weights for the ranking formula (sum == 1.0)."""
    return {"evidence": 0.35, "topology": 0.2, "time_corr": 0.15, "impact": 0.2, "prior": 0.1}


class RootCauseRanker:
    """Rank candidate root causes by weighted formula + window adjustment."""

    def __init__(
        self,
        *,
        weights: dict[str, float] | None = None,
        window_boost: float = 1.2,
    ) -> None:
        if window_boost <= 0:
            raise ValueError(f"window_boost must be > 0, got {window_boost}")
        if weights is None:
            weights = default_weights()
        else:
            # Partial override expresses RELATIVE importance: unspecified dims
            # default to 0, then the effective set is renormalized so the sum is
            # 1.0 (e.g. {"evidence":2.0,"impact":1.0} → evidence=2/3, impact=1/3).
            # Unknown keys are rejected so a typo never silently drops a term.
            unknown = set(weights) - set(default_weights())
            if unknown:
                raise ValueError(f"unknown weight dims: {sorted(unknown)}")
            effective = {dim: 0.0 for dim in default_weights()}
            effective.update(weights)
            total = sum(effective.values())
            if total <= 0:
                raise ValueError("weights must not be all zero")
            weights = {dim: v / total for dim, v in effective.items()}
        self.weights = weights
        self.window_boost = window_boost

    def impact_score(
        self,
        candidate: CandidateRootCause,
        ctx: BusinessContext,
    ) -> float:
        """Derive business impact in [0, 1] from context (or use override).

        If ``candidate.business_impact`` is set, it is used directly.
        Otherwise compute from customer tier + request rate + error budget,
        averaged, and clamp to [0, 1].
        """
        if candidate.business_impact is not None:
            return min(max(candidate.business_impact, 0.0), 1.0)

        tier = TIER_WEIGHTS.get(ctx.customer_tier, 0.0)
        rate = min(max(ctx.request_rate / RATE_NORMALIZER, 0.0), 1.0)
        budget = min(max(ctx.error_budget_consumed, 0.0), 1.0)
        impact = (tier + rate + budget) / 3.0
        return min(max(impact, 0.0), 1.0)

    def rank(
        self,
        candidates: list[CandidateRootCause],
        ctx: BusinessContext,
    ) -> list[RankResult]:
        """Sort candidates by weighted formula, priority descending. No mutation."""
        results: list[RankResult] = []
        w = self.weights
        for c in candidates:
            # Guard NaN/inf inputs (evidence/time_corr/prior/business_impact
            # must be finite); a NaN score would silently rank garbage and
            # corrupt the output.
            for dim_name, dim_val in (
                ("evidence_strength", c.evidence_strength),
                ("time_correlation", c.time_correlation),
                ("historical_prior", c.historical_prior),
                ("business_impact", c.business_impact),
            ):
                if dim_val is not None and not math.isfinite(dim_val):
                    raise ValueError(
                        f"candidate {c.candidate_id!r}: {dim_name} must be finite, "
                        f"got {dim_val!r}"
                    )
            impact = self.impact_score(c, ctx)
            topology = 1.0 / (1.0 + max(c.topology_distance, 0))
            components = {
                "evidence": w["evidence"] * c.evidence_strength,
                "topology": w["topology"] * topology,
                "time_corr": w["time_corr"] * c.time_correlation,
                "impact": w["impact"] * impact,
                "prior": w["prior"] * c.historical_prior,
            }
            score = sum(components.values())
            priority = self.adjust_priority(score, ctx)
            results.append(RankResult(c.candidate_id, score, priority, components, c.resource))
        results.sort(key=lambda r: r.priority, reverse=True)
        return results

    def adjust_priority(self, score: float, ctx: BusinessContext) -> float:
        """Apply multiplicative window adjustment to ``score``."""
        if ctx.core_hours or ctx.release_window:
            return score * self.window_boost
        if ctx.maintenance_window:
            return score * (1.0 / self.window_boost)
        return score
