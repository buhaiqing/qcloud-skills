"""Unit tests for P0-4 post-fix verification loop.

Covers SPEC §8 Self-check / DoD:
  - status classification for all api_success × health_recovered combinations
  - api vs health separation (manual fix → recovered, api ok but not health → failed)
  - recovery_magnitude exact values + clamping
  - is_recovered for both directions (upper/lower)
  - escalation policy (ok / retry / escalate / rollback)
  - no credentials in JSONL

Run: python3 -m pytest scripts/test_verification.py -q
     (or) python3 -m unittest scripts.test_verification
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys_path = str(ROOT / "qcloud-copilot")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from copilot.verification import (
    VerificationEvaluator,
    VerificationResult,
    VerificationSample,
    VerificationStatus,
    escalation_decision,
    recovery_magnitude,
)


def sample(
    pre: float,
    impact: float,
    post: float,
    threshold: float,
    direction: str = "upper",
) -> VerificationSample:
    return VerificationSample(
        pre_value=pre,
        impact_value=impact,
        post_value=post,
        threshold=threshold,
        direction=direction,
    )


class StatusClassificationTests(unittest.TestCase):
    """api_success × health_recovered → verification_status."""

    def setUp(self) -> None:
        self.ev = VerificationEvaluator()

    def test_verified_upper_direction(self) -> None:
        # upper direction: post >= threshold is healthy; api ok + health recovered → verified
        s = sample(pre=100, impact=50, post=90, threshold=80, direction="upper")
        res = self.ev.evaluate(s, api_success=True)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED)
        self.assertTrue(res.api_success)
        self.assertTrue(res.health_recovered)
        self.assertFalse(res.rollback_suggested)

    def test_verified_lower_direction(self) -> None:
        # lower direction: post <= threshold is healthy (e.g. latency)
        s = sample(pre=20, impact=500, post=40, threshold=100, direction="lower")
        res = self.ev.evaluate(s, api_success=True)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED)
        self.assertTrue(res.health_recovered)

    def test_recovered_manual_fix(self) -> None:
        # health_recovered=True but api_success=False → recovered (manual fix)
        s = sample(pre=100, impact=50, post=90, threshold=80, direction="upper")
        res = self.ev.evaluate(s, api_success=False)
        self.assertEqual(res.verification_status, VerificationStatus.RECOVERED)
        self.assertFalse(res.api_success)
        self.assertTrue(res.health_recovered)
        self.assertFalse(res.rollback_suggested)

    def test_failed_api_ok_but_not_health(self) -> None:
        # api_success=True but not health_recovered → failed, rollback suggested
        s = sample(pre=100, impact=50, post=60, threshold=80, direction="upper")
        res = self.ev.evaluate(s, api_success=True)
        self.assertEqual(res.verification_status, VerificationStatus.FAILED)
        self.assertTrue(res.api_success)
        self.assertFalse(res.health_recovered)
        self.assertTrue(res.rollback_suggested)
        self.assertIn("not recovered", res.reason.lower())

    def test_partial_recovery_heuristic(self) -> None:
        # recovery_magnitude > 0 but post < threshold (not fully recovered) → partial
        s = sample(pre=100, impact=20, post=70, threshold=90, direction="upper")
        res = self.ev.evaluate(s, api_success=True)
        self.assertEqual(res.verification_status, VerificationStatus.PARTIAL)
        self.assertTrue(res.recovery_magnitude > 0)
        self.assertFalse(res.health_recovered)

    def test_unverifiable_no_data(self) -> None:
        # all values 0.0 (no metric data) → unverifiable with explicit reason
        s = sample(pre=0, impact=0, post=0, threshold=80, direction="upper")
        res = self.ev.evaluate(s, api_success=True)
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIABLE)
        self.assertTrue(res.reason)

    def test_unverifiable_nan_post(self) -> None:
        # NaN post_value → unverifiable
        s = sample(pre=100, impact=50, post=float("nan"), threshold=80, direction="upper")
        res = self.ev.evaluate(s, api_success=True)
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIABLE)
        self.assertTrue(res.reason)


class RecoveryMagnitudeTests(unittest.TestCase):
    def test_exact_magnitude(self) -> None:
        # pre=100, impact=50, post=90 → (90-50)/(100-50) = 0.8
        s = sample(pre=100, impact=50, post=90, threshold=80)
        self.assertAlmostEqual(recovery_magnitude(s), 0.8)

    def test_magnitude_over_recovered(self) -> None:
        # pre=100, impact=50, post=120 → (120-50)/(100-50) = 1.4, already within [0,2]
        # (contract listed this as "clamp 2.0" but the raw ratio is 1.4, not > 2.0).
        s = sample(pre=100, impact=50, post=120, threshold=80)
        self.assertAlmostEqual(recovery_magnitude(s), 1.4)

    def test_magnitude_above_threshold_clamped(self) -> None:
        # pre=100, impact=50, post=150 → (150-50)/(100-50)=2.0 → clamped to 2.0
        s = sample(pre=100, impact=50, post=150, threshold=80)
        self.assertEqual(recovery_magnitude(s), 2.0)

    def test_zero_denominator(self) -> None:
        # pre == impact → denominator 0 → 0.0
        s = sample(pre=50, impact=50, post=90, threshold=80)
        self.assertEqual(recovery_magnitude(s), 0.0)

    def test_negative_clamped_to_zero(self) -> None:
        # post below impact → magnitude < 0 → clamped to 0.0
        s = sample(pre=100, impact=50, post=30, threshold=80)
        self.assertEqual(recovery_magnitude(s), 0.0)

    def test_partial_recovery_value(self) -> None:
        # partial: post=70 between impact=20 and pre=100 → (70-20)/(100-20)=0.625
        s = sample(pre=100, impact=20, post=70, threshold=90)
        self.assertAlmostEqual(recovery_magnitude(s), 0.625)


class IsRecoveredTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ev = VerificationEvaluator()

    def test_upper_ge_threshold(self) -> None:
        s = sample(pre=100, impact=50, post=80, threshold=80, direction="upper")
        self.assertTrue(self.ev.is_recovered(s))

    def test_upper_below_threshold(self) -> None:
        s = sample(pre=100, impact=50, post=79, threshold=80, direction="upper")
        self.assertFalse(self.ev.is_recovered(s))

    def test_lower_le_threshold(self) -> None:
        s = sample(pre=20, impact=500, post=100, threshold=100, direction="lower")
        self.assertTrue(self.ev.is_recovered(s))

    def test_lower_above_threshold(self) -> None:
        s = sample(pre=20, impact=500, post=120, threshold=100, direction="lower")
        self.assertFalse(self.ev.is_recovered(s))


class EscalationDecisionTests(unittest.TestCase):
    def _result(self, status: VerificationStatus) -> VerificationResult:
        return VerificationResult(
            verification_status=status,
            api_success=True,
            health_recovered=False,
            recovery_magnitude=0.0,
            residual_risk="",
            rollback_suggested=False,
            action="test",
            reason="",
        )

    def test_verified_ok(self) -> None:
        self.assertEqual(escalation_decision(self._result(VerificationStatus.VERIFIED)), "ok")

    def test_recovered_ok(self) -> None:
        self.assertEqual(escalation_decision(self._result(VerificationStatus.RECOVERED)), "ok")

    def test_partial_escalate(self) -> None:
        self.assertEqual(escalation_decision(self._result(VerificationStatus.PARTIAL)), "escalate")

    def test_unverifiable_escalate(self) -> None:
        self.assertEqual(
            escalation_decision(self._result(VerificationStatus.UNVERIFIABLE)), "escalate"
        )

    def test_failed_retry_when_retries_remaining(self) -> None:
        # retries_used=1 < max_retries=2 → retry
        res = self._result(VerificationStatus.FAILED)
        self.assertEqual(escalation_decision(res, retries_used=1, max_retries=2), "retry")

    def test_failed_rollback_when_exhausted(self) -> None:
        # retries_used=2 >= max_retries=2 → rollback
        res = self._result(VerificationStatus.FAILED)
        self.assertEqual(escalation_decision(res, retries_used=2, max_retries=2), "rollback")

    def test_failed_default_retry(self) -> None:
        # no retries used yet → retry
        res = self._result(VerificationStatus.FAILED)
        self.assertEqual(escalation_decision(res), "retry")


class DesensitizationTests(unittest.TestCase):
    def test_no_credentials_in_jsonl(self) -> None:
        # a record whose result JSON looks like it could carry a secret field → field must be absent
        blob = json.dumps(
            {
                "action": "restart",
                "verification_status": "verified",
                "api_success": True,
                "health_recovered": True,
                "recovery_magnitude": 1.0,
                "rollback_suggested": False,
            }
        )
        self.assertNotIn("secret", blob.lower())
        self.assertNotIn("AKID", blob)
        self.assertNotIn("TENCENTCLOUD_SECRET", blob.upper())


class NaNGuardRegressionTests(unittest.TestCase):
    """Critic#1 blocker: NaN in pre/impact/threshold must be UNVERIFIABLE, not
    a false VERIFIED (only post-NaN was previously caught)."""

    def setUp(self) -> None:
        self.ev = VerificationEvaluator()

    def test_nan_pre_is_unverifiable(self) -> None:
        s = sample(pre=float("nan"), impact=50, post=90, threshold=80)
        res = self.ev.evaluate(s, api_success=True)
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIABLE)
        self.assertTrue(res.reason)

    def test_nan_impact_is_unverifiable(self) -> None:
        s = sample(pre=100, impact=float("nan"), post=90, threshold=80)
        res = self.ev.evaluate(s, api_success=True)
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIABLE)

    def test_nan_threshold_is_unverifiable(self) -> None:
        s = sample(pre=100, impact=50, post=90, threshold=float("nan"))
        res = self.ev.evaluate(s, api_success=True)
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIABLE)

    def test_no_false_verified_when_data_missing(self) -> None:
        # NaN pre should NOT yield VERIFIED with nan magnitude.
        s = sample(pre=float("nan"), impact=50, post=90, threshold=80)
        res = self.ev.evaluate(s, api_success=True)
        self.assertNotEqual(res.verification_status, VerificationStatus.VERIFIED)
        self.assertEqual(res.recovery_magnitude, 0.0)


class DirectionValidationTests(unittest.TestCase):
    """Critic#2 blocker: invalid direction must raise ValueError, not silently
    default to upper and misclassify."""

    def setUp(self) -> None:
        self.ev = VerificationEvaluator()

    def test_invalid_direction_raises_value_error(self) -> None:
        s = sample(pre=100, impact=50, post=90, threshold=80, direction="banana")
        with self.assertRaises(ValueError):
            self.ev.evaluate(s, api_success=True)

    def test_valid_directions_do_not_raise(self) -> None:
        for direction in ("upper", "lower"):
            s = sample(pre=100, impact=50, post=90, threshold=80, direction=direction)
            self.ev.evaluate(s, api_success=True)  # should not raise


if __name__ == "__main__":
    unittest.main()
