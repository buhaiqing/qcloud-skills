"""P0-4 Post-fix verification loop (SPEC: post-fix-verification-design.md).

Read-only verification layer for mutation actions. Distinguishes *API success*
(after a fix action returns 0) from *health recovery* (business/health metric
returns to its recovery threshold). Produces a `VerificationResult` with status,
recovery magnitude, residual risk and a rollback suggestion, plus an escalation
policy mapping a result to ``ok`` / ``retry`` / ``escalate`` / ``rollback``.

Pure functions / dataclasses — no mutation of inputs, replayable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class VerificationStatus(str, Enum):
    VERIFIED = "verified"          # api_success and health_recovered
    RECOVERED = "recovered"        # health_recovered regardless of api_success (e.g. manual fix)
    PARTIAL = "partial"            # some metrics recovered, not fully
    FAILED = "failed"              # not recovered; retry or rollback
    UNVERIFIABLE = "unverifiable"  # missing metric data, cannot verify (explicit reason)


@dataclass
class VerificationResult:
    verification_status: VerificationStatus
    api_success: bool
    health_recovered: bool
    recovery_magnitude: float
    residual_risk: str
    rollback_suggested: bool
    action: str
    reason: str


@dataclass
class VerificationSample:
    pre_value: float              # baseline before the incident
    impact_value: float           # value during the incident / peak
    post_value: float             # value after the fix
    threshold: float              # recovery threshold (health floor or ceiling)
    direction: str = "upper"      # "upper" (>= threshold is healthy) | "lower" (<= threshold is healthy)
    stable_window_min: int = 15   # minutes post must stay recovered to count as recovered
    unit: str = ""


def recovery_magnitude(sample: VerificationSample) -> float:
    """Fraction of recovery: (post - impact) / (pre - impact), clamped to [0.0, 2.0].

    Same formula for both directions (magnitude is a relative improvement toward
    the pre-incident baseline). Uncomputable (zero denominator) → 0.0.
    """
    denominator = sample.pre_value - sample.impact_value
    if denominator == 0:
        return 0.0
    magnitude = (sample.post_value - sample.impact_value) / denominator
    return min(max(magnitude, 0.0), 2.0)


class VerificationEvaluator:
    """Judges whether a fix actually recovered a health metric."""

    def is_recovered(self, sample: VerificationSample) -> bool:
        """True when post_value is inside the healthy region per direction.

        ``upper`` (e.g. availability): healthy when post_value >= threshold.
        ``lower`` (e.g. latency/error rate): healthy when post_value <= threshold.
        """
        if sample.direction == "lower":
            return sample.post_value <= sample.threshold
        return sample.post_value >= sample.threshold

    @staticmethod
    def _closer_to_health(sample: VerificationSample) -> bool:
        """True when post_value is nearer the recovery threshold than the impact value.

        Used to distinguish ``partial`` (moving toward health) from ``failed``
        (still closer to the degraded impact point).
        """
        return abs(sample.post_value - sample.threshold) < abs(
            sample.post_value - sample.impact_value
        )

    def evaluate(self, sample: VerificationSample, *, api_success: bool) -> VerificationResult:
        """Combine api_success + health metrics into a VerificationResult. Does not mutate."""
        action = getattr(sample, "action", "")
        if sample.direction not in ("upper", "lower"):
            raise ValueError(
                f"invalid direction: {sample.direction!r} (expected 'upper' or 'lower')"
            )
        # No usable metric data → cannot verify. NaN in ANY of pre/impact/post/
        # threshold (not just post) means missing data → UNVERIFIABLE, not a
        # false VERIFIED/FAILED verdict.
        vals = (sample.pre_value, sample.impact_value, sample.post_value, sample.threshold)
        if any(math.isnan(v) for v in vals) or (
            sample.pre_value == 0.0 and sample.impact_value == 0.0 and sample.post_value == 0.0
        ):
            return VerificationResult(
                verification_status=VerificationStatus.UNVERIFIABLE,
                api_success=api_success,
                health_recovered=False,
                recovery_magnitude=0.0,
                residual_risk="cannot assess residual risk; metric data missing",
                rollback_suggested=False,
                action=action,
                reason=(
                    "missing metric data: NaN in pre/impact/post/threshold or all zero; "
                    "cannot verify recovery"
                ),
            )

        health_recovered = self.is_recovered(sample)
        magnitude = recovery_magnitude(sample)

        if health_recovered and api_success:
            status = VerificationStatus.VERIFIED
            residual_risk = "metrics recovered within threshold; residual risk low"
            reason = "api_success and health_recovered; post within recovery threshold"
        elif health_recovered and not api_success:
            status = VerificationStatus.RECOVERED
            residual_risk = "health recovered (possibly manual fix); residual risk low"
            reason = "health_recovered despite api_success=False (e.g. manual fix)"
        elif not health_recovered and self._closer_to_health(sample):
            # Post is nearer the health threshold than the impact value → partial recovery.
            status = VerificationStatus.PARTIAL
            residual_risk = "partial recovery; residual risk moderate"
            reason = (
                "health not fully recovered but post closer to recovery threshold "
                "than to impact value; partial recovery"
            )
        elif not health_recovered:
            status = VerificationStatus.FAILED
            residual_risk = "metrics not recovered; residual risk high"
            reason = "metrics not recovered; post outside recovery threshold"
        else:  # pragma: no cover - defensive; all combos handled above
            status = VerificationStatus.FAILED
            residual_risk = "metrics not recovered; residual risk high"
            reason = "unexpected evaluation state"

        return VerificationResult(
            verification_status=status,
            api_success=api_success,
            health_recovered=health_recovered,
            recovery_magnitude=magnitude,
            residual_risk=residual_risk,
            rollback_suggested=status == VerificationStatus.FAILED,
            action=action,
            reason=reason,
        )


def escalation_decision(
    result: VerificationResult,
    *,
    max_retries: int = 2,
    retries_used: int = 0,
) -> str:
    """Map a VerificationResult to an escalation action.

    - VERIFIED / RECOVERED → ``ok``
    - PARTIAL / UNVERIFIABLE → ``escalate``
    - FAILED → ``retry`` while retries remain, else ``rollback``
    """
    status = result.verification_status
    if status in (VerificationStatus.VERIFIED, VerificationStatus.RECOVERED):
        return "ok"
    if status in (VerificationStatus.PARTIAL, VerificationStatus.UNVERIFIABLE):
        return "escalate"
    if status == VerificationStatus.FAILED:
        return "retry" if retries_used < max_retries else "rollback"
    return "escalate"  # pragma: no cover - defensive
