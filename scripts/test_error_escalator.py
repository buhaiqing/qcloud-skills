#!/usr/bin/env python3
"""Unit tests for scripts/error_escalator.py.

Pure stdlib. Run with:
    cd scripts && python3 -m unittest test_error_escalator -v

L5 lesson: assert actual populated values, not just key presence.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from error_escalator import (
    Action,
    ErrorEscalator,
    ErrorRule,
    compute_backoff,
)


def _make_escalator() -> ErrorEscalator:
    esc = ErrorEscalator()
    esc.add_rule(ErrorRule(
        code="InvalidVpc.NotFound", product="cvm", action=Action.HALT,
        delegate_to="qcloud-vpc-ops",
        recovery_hint="Verify VPC exists",
    ))
    esc.add_rule(ErrorRule(
        code="InvalidVpc", product="", action=Action.HALT,
        recovery_hint="VPC error; check VPC state",
    ))
    esc.add_rule(ErrorRule(
        code="RequestLimitExceeded", product="", action=Action.RETRY,
        max_retries=3, backoff_strategy="exponential",
        recovery_hint="Back off and retry",
    ))
    esc.add_rule(ErrorRule(
        code="InternalError", product="", action=Action.RETRY,
        max_retries=3, backoff_seconds=[2, 4, 8], backoff_strategy="fixed",
        recovery_hint="Retry; HALT with RequestId if persists",
    ))
    esc.add_rule(ErrorRule(
        code="InvalidParameter.ImageIdMalformed", product="cvm",
        action=Action.FIX, max_retries=1,
        recovery_hint="Use DescribeImages to find valid images",
    ))
    return esc


class ActionEnumTests(unittest.TestCase):
    """Action enum membership & values."""

    def test_action_values(self):
        self.assertEqual(Action.HALT.value, "HALT")
        self.assertEqual(Action.RETRY.value, "RETRY")
        self.assertEqual(Action.FIX.value, "FIX")
        self.assertEqual(Action.DELEGATE.value, "DELEGATE")

    def test_action_members(self):
        # All four actions must exist; the public enum is the contract.
        members = {a.value for a in Action}
        self.assertEqual(members, {"HALT", "RETRY", "FIX", "DELEGATE"})


class ExactResolveTests(unittest.TestCase):
    """Exact (code, product) match returns the right rule."""

    def test_exact_match_with_specific_product(self):
        esc = _make_escalator()
        rule = esc.resolve("InvalidVpc.NotFound", "cvm")
        self.assertEqual(rule.action, Action.HALT)
        self.assertEqual(rule.delegate_to, "qcloud-vpc-ops")
        self.assertEqual(rule.recovery_hint, "Verify VPC exists")

    def test_unknown_code_safe_default(self):
        esc = _make_escalator()
        rule = esc.resolve("UnknownError.XYZ", "cvm")
        self.assertEqual(rule.action, Action.HALT,
                         "Unknown error codes MUST default to HALT (safe)")
        # Default must carry the original code for downstream reporting
        self.assertEqual(rule.code, "UnknownError.XYZ")

    def test_unknown_code_unknown_product_safe_default(self):
        esc = _make_escalator()
        rule = esc.resolve("TotallyRandom", "made_up_product")
        self.assertEqual(rule.action, Action.HALT)
        self.assertEqual(rule.code, "TotallyRandom")

    def test_empty_escalator_safe_default(self):
        esc = ErrorEscalator()
        rule = esc.resolve("Anything", "any")
        self.assertEqual(rule.action, Action.HALT)


class PrefixResolveTests(unittest.TestCase):
    """Prefix fallback: `InvalidVpc.NotFound` → falls back to `InvalidVpc`."""

    def test_prefix_match_when_exact_misses(self):
        esc = _make_escalator()
        # No exact (InvalidVpc.NotFound, redis) rule, but InvalidVpc prefix
        # rule with empty product matches. action must be HALT (prefix rule).
        rule = esc.resolve("InvalidVpc.NotFound", "redis")
        self.assertEqual(rule.action, Action.HALT)
        self.assertEqual(rule.code, "InvalidVpc")
        self.assertEqual(rule.recovery_hint, "VPC error; check VPC state")

    def test_exact_match_wins_over_prefix(self):
        esc = _make_escalator()
        rule = esc.resolve("InvalidVpc.NotFound", "cvm")
        # Exact (InvalidVpc.NotFound, cvm) rule must beat the InvalidVpc prefix.
        self.assertEqual(rule.code, "InvalidVpc.NotFound")
        self.assertEqual(rule.delegate_to, "qcloud-vpc-ops")

    def test_specific_product_wins_over_wildcard(self):
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(code="AuthFailure", product="", action=Action.RETRY))
        esc.add_rule(ErrorRule(code="AuthFailure", product="cam", action=Action.HALT))
        rule = esc.resolve("AuthFailure", "cam")
        self.assertEqual(rule.action, Action.HALT,
                         "Specific-product rule must win over wildcard")


class BackoffTests(unittest.TestCase):
    """compute_backoff correctness."""

    def test_exponential_attempt_0(self):
        self.assertEqual(compute_backoff("exponential", 0), 1.0)

    def test_exponential_attempt_2(self):
        self.assertEqual(compute_backoff("exponential", 2), 4.0)

    def test_exponential_attempt_5(self):
        self.assertEqual(compute_backoff("exponential", 5), 32.0)

    def test_fixed_default_returns_one(self):
        # Fixed strategy without explicit seconds falls back to 1s.
        self.assertEqual(compute_backoff("fixed", 0), 1.0)

    def test_unknown_strategy_returns_one(self):
        # Unknown strategy must not crash; default 1s is the safe fallback.
        self.assertEqual(compute_backoff("lol", 3), 1.0)


class LoadFromSkillTests(unittest.TestCase):
    """load_from_skill parses SKILL.md and registers rules."""

    def test_load_from_skill_md_with_legacy_table(self):
        # Build a fake skill dir with a minimal SKILL.md containing legacy
        # 3-col error tables.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td)
            (skill_dir / "SKILL.md").write_text(
                "# fake skill\n\n"
                "## RunInstances errors\n\n"
                "| Error Code | Max Retries | Recovery |\n"
                "|------------|-------------|----------|\n"
                "| `InvalidVpc.NotFound` | 0 | HALT. Delegate to qcloud-vpc-ops |\n"
                "| `InternalError` | 3 (2s,4s,8s) | Retry; HALT if persists |\n"
                "| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |\n",
                encoding="utf-8",
            )
            esc = ErrorEscalator()
            count = esc.load_from_skill(skill_dir)
            self.assertGreaterEqual(count, 3,
                                    f"expected ≥3 rules, got {count}")

            rule = esc.resolve("InvalidVpc.NotFound", "")
            self.assertEqual(rule.action, Action.HALT)
            self.assertEqual(rule.delegate_to, "qcloud-vpc-ops")

            rule = esc.resolve("InternalError", "")
            self.assertEqual(rule.action, Action.RETRY)
            self.assertEqual(rule.max_retries, 3)
            self.assertEqual(rule.backoff_seconds, [2, 4, 8])

            rule = esc.resolve("RequestLimitExceeded", "")
            self.assertEqual(rule.action, Action.RETRY)
            self.assertEqual(rule.backoff_strategy, "exponential")


class LoadAllSkillsTests(unittest.TestCase):
    """load_all_skills walks repo_root and aggregates rules."""

    def test_load_all_skills_aggregates(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill_a = root / "qcloud-foo-ops"
            skill_a.mkdir()
            (skill_a / "SKILL.md").write_text(
                "| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |\n"
                "|------------|--------|-------------|---------|-------------|---------------|\n"
                "| `FooError` | HALT | 0 | — | — | foo broke |\n",
                encoding="utf-8",
            )
            skill_b = root / "qcloud-bar-ops"
            skill_b.mkdir()
            (skill_b / "SKILL.md").write_text(
                "| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |\n"
                "|------------|--------|-------------|---------|-------------|---------------|\n"
                "| `BarError` | RETRY | 3 | exponential | — | back off |\n",
                encoding="utf-8",
            )
            esc = ErrorEscalator()
            count = esc.load_all_skills(root)
            self.assertGreaterEqual(count, 2)
            self.assertEqual(esc.resolve("FooError", "").action, Action.HALT)
            self.assertEqual(esc.resolve("BarError", "").action, Action.RETRY)


class EmptyCodeTests(unittest.TestCase):
    """Empty / whitespace inputs are safe."""

    def test_empty_code_safe_default(self):
        esc = _make_escalator()
        rule = esc.resolve("", "cvm")
        self.assertEqual(rule.action, Action.HALT)

    def test_whitespace_code_safe_default(self):
        esc = _make_escalator()
        rule = esc.resolve("   ", "cvm")
        self.assertEqual(rule.action, Action.HALT)


if __name__ == "__main__":
    unittest.main()