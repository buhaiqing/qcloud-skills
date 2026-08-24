#!/usr/bin/env python3
"""Tests for autonomy_policy — Phase 3.4 governance framework."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parents[1])
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from autonomy_policy import (
    LEVEL_0,
    LEVEL_1,
    LEVEL_2,
    LEVEL_3,
    AutonomyDecision,
    AutonomyPolicy,
    AutonomyRule,
    evaluate_autonomy,
)


class AutonomyPolicyTests(unittest.TestCase):
    """Core tests for AutonomyPolicy.evaluate()."""

    # ------------------------------------------------------------------
    # Level 0 — all destructive need token, everything else auto-confirms
    # ------------------------------------------------------------------

    def test_level_0_destructive_needs_token(self) -> None:
        decision = LEVEL_0.evaluate(
            operation="TerminateInstances",
            risk_level="LOW",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "human_token")

    def test_level_0_non_destructive_auto_confirm(self) -> None:
        decision = LEVEL_0.evaluate(
            operation="DescribeInstances",
            risk_level="LOW",
            is_destructive=False,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "auto_confirm")

    def test_level_0_destructive_critical_needs_token(self) -> None:
        decision = LEVEL_0.evaluate(
            operation="DeleteAllInstances",
            risk_level="CRITICAL",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "human_token")

    # ------------------------------------------------------------------
    # Level 1 — LOW auto, MEDIUM critic, HIGH/CRITICAL human
    # ------------------------------------------------------------------

    def test_level_1_low_auto_confirm(self) -> None:
        decision = LEVEL_1.evaluate(
            operation="DescribeInstances",
            risk_level="LOW",
            is_destructive=False,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "auto_confirm")

    def test_level_1_medium_critic_review(self) -> None:
        decision = LEVEL_1.evaluate(
            operation="ModifyInstanceType",
            risk_level="MEDIUM",
            is_destructive=False,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "critic_review")

    def test_level_1_high_human_token(self) -> None:
        decision = LEVEL_1.evaluate(
            operation="TerminateInstances",
            risk_level="HIGH",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "human_token")

    def test_level_1_critical_human_token(self) -> None:
        decision = LEVEL_1.evaluate(
            operation="DeleteAllResources",
            risk_level="CRITICAL",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "human_token")

    # ------------------------------------------------------------------
    # Level 2 — LOW/MEDIUM auto, HIGH critic, CRITICAL approval
    # ------------------------------------------------------------------

    def test_level_2_low_auto_confirm(self) -> None:
        decision = LEVEL_2.evaluate(
            operation="DescribeInstances",
            risk_level="LOW",
            is_destructive=False,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "auto_confirm")

    def test_level_2_medium_auto_confirm(self) -> None:
        decision = LEVEL_2.evaluate(
            operation="ModifyInstanceType",
            risk_level="MEDIUM",
            is_destructive=False,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "auto_confirm")

    def test_level_2_high_critic_review(self) -> None:
        decision = LEVEL_2.evaluate(
            operation="TerminateInstances",
            risk_level="HIGH",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "critic_review")

    def test_level_2_critical_human_approval(self) -> None:
        decision = LEVEL_2.evaluate(
            operation="DeleteVpc",
            risk_level="CRITICAL",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "human_approval")

    # ------------------------------------------------------------------
    # Level 3 — only CRITICAL needs approval, cross-system always token
    # ------------------------------------------------------------------

    def test_level_3_low_auto_confirm(self) -> None:
        decision = LEVEL_3.evaluate(
            operation="DescribeInstances",
            risk_level="LOW",
            is_destructive=False,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "auto_confirm")

    def test_level_3_medium_auto_confirm(self) -> None:
        decision = LEVEL_3.evaluate(
            operation="ModifyInstanceType",
            risk_level="MEDIUM",
            is_destructive=False,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "auto_confirm")

    def test_level_3_high_auto_confirm(self) -> None:
        decision = LEVEL_3.evaluate(
            operation="TerminateInstances",
            risk_level="HIGH",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "auto_confirm")

    def test_level_3_critical_human_approval(self) -> None:
        decision = LEVEL_3.evaluate(
            operation="DeleteVpc",
            risk_level="CRITICAL",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "human_approval")

    def test_level_3_cross_system_always_token(self) -> None:
        decision = LEVEL_3.evaluate(
            operation="CopyImageToAnotherRegion",
            risk_level="LOW",
            is_destructive=False,
            is_cross_system=True,
        )
        self.assertEqual(decision.action_taken, "human_token")

    # ------------------------------------------------------------------
    # Cross-system at Level 2 — always needs token
    # ------------------------------------------------------------------

    def test_level_2_cross_system_low_risk_needs_token(self) -> None:
        decision = LEVEL_2.evaluate(
            operation="CopyImageToAnotherRegion",
            risk_level="LOW",
            is_destructive=False,
            is_cross_system=True,
        )
        self.assertEqual(decision.action_taken, "human_token")

    def test_level_2_cross_system_high_risk_still_token(self) -> None:
        decision = LEVEL_2.evaluate(
            operation="CopyImageToAnotherRegion",
            risk_level="HIGH",
            is_destructive=False,
            is_cross_system=True,
        )
        # cross_system rule is ordered before risk_level rules in LEVEL_2
        self.assertEqual(decision.action_taken, "human_token")

    # ------------------------------------------------------------------
    # Condition parsing
    # ------------------------------------------------------------------

    def test_condition_risk_level_equals(self) -> None:
        decision = LEVEL_1.evaluate(
            operation="DescribeInstances",
            risk_level="LOW",
            is_destructive=False,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "auto_confirm")
        self.assertIsNotNone(decision.matched_rule)
        self.assertEqual(decision.matched_rule.condition, "risk_level == 'LOW'")

    def test_condition_risk_level_in(self) -> None:
        decision = LEVEL_2.evaluate(
            operation="DescribeInstances",
            risk_level="MEDIUM",
            is_destructive=False,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "auto_confirm")
        self.assertIsNotNone(decision.matched_rule)
        self.assertIn("in", decision.matched_rule.condition)

    def test_condition_is_destructive_bare(self) -> None:
        decision = LEVEL_0.evaluate(
            operation="TerminateInstances",
            risk_level="LOW",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(decision.action_taken, "human_token")
        self.assertEqual(decision.matched_rule.condition, "is_destructive")

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def test_rate_limiting_blocks_after_threshold(self) -> None:
        limited_policy = AutonomyPolicy(
            level=0,
            description="Rate-limited policy",
            rules=[
                AutonomyRule(
                    condition="is_destructive",
                    action="human_token",
                    scope=["*"],
                    max_decisions_per_hour=2,
                    require_audit=True,
                ),
                AutonomyRule(
                    condition="else",
                    action="auto_confirm",
                    scope=["*"],
                    require_audit=False,
                ),
            ],
        )
        # Make 2 decisions — both should succeed (human_token)
        for _ in range(2):
            d = limited_policy.evaluate(
                operation="DeleteBucket",
                risk_level="CRITICAL",
                is_destructive=True,
                is_cross_system=False,
            )
            self.assertEqual(d.action_taken, "human_token")

        # 3rd decision should be rate-limited → human_token via rate-limit fallback
        d = limited_policy.evaluate(
            operation="DeleteBucket",
            risk_level="CRITICAL",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertEqual(d.action_taken, "human_token")
        self.assertIn("rate limit", d.rationale.lower())

    def test_rate_limiting_allows_after_window_cleared(self) -> None:
        limited_policy = AutonomyPolicy(
            level=0,
            description="Rate-limited policy",
            rules=[
                AutonomyRule(
                    condition="is_destructive",
                    action="human_token",
                    scope=["*"],
                    max_decisions_per_hour=1,
                    require_audit=True,
                ),
                AutonomyRule(
                    condition="else",
                    action="auto_confirm",
                    scope=["*"],
                    require_audit=False,
                ),
            ],
        )
        # First call
        limited_policy.evaluate(
            operation="DeleteBucket",
            risk_level="CRITICAL",
            is_destructive=True,
            is_cross_system=False,
        )
        # Simulate time passing by clearing the clock
        limited_policy._decision_clock.clear()
        # Next call should not be rate-limited
        d = limited_policy.evaluate(
            operation="DeleteBucket",
            risk_level="CRITICAL",
            is_destructive=True,
            is_cross_system=False,
        )
        self.assertNotIn("rate limit", d.rationale.lower())

    # ------------------------------------------------------------------
    # evaluate_autonomy convenience function
    # ------------------------------------------------------------------

    def test_evaluate_autonomy_level_0(self) -> None:
        result = evaluate_autonomy(
            operation="TerminateInstances",
            risk_level="CRITICAL",
            is_destructive=True,
            is_cross_system=False,
            level=0,
        )
        self.assertEqual(result, "human_token")

    def test_evaluate_autonomy_level_2_medium(self) -> None:
        result = evaluate_autonomy(
            operation="ModifyInstanceType",
            risk_level="MEDIUM",
            is_destructive=False,
            is_cross_system=False,
            level=2,
        )
        self.assertEqual(result, "auto_confirm")

    def test_evaluate_autonomy_unknown_level_defaults_to_0(self) -> None:
        result = evaluate_autonomy(
            operation="TerminateInstances",
            risk_level="LOW",
            is_destructive=True,
            is_cross_system=False,
            level=99,
        )
        self.assertEqual(result, "human_token")  # LEVEL_0 destructive rule


class AutonomyDecisionTests(unittest.TestCase):
    """Tests for AutonomyDecision dataclass."""

    def test_decision_has_all_fields(self) -> None:
        rule = AutonomyRule(
            condition="risk_level == 'LOW'",
            action="auto_confirm",
            scope=["*"],
        )
        decision = AutonomyDecision(
            action_taken="auto_confirm",
            matched_rule=rule,
            rationale="test rationale",
        )
        self.assertEqual(decision.action_taken, "auto_confirm")
        self.assertEqual(decision.matched_rule, rule)
        self.assertEqual(decision.rationale, "test rationale")


if __name__ == "__main__":
    unittest.main()
