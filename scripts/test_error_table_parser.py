#!/usr/bin/env python3
"""Unit tests for scripts/error_table_parser.py.

Pure stdlib. Run with:
    cd scripts && python3 -m unittest test_error_table_parser -v

L5 lesson: assert actual populated values, not just key presence.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from error_escalator import Action
from error_table_parser import parse_error_table

STANDARD_TABLE = """\
| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |
|------------|--------|-------------|---------|-------------|---------------|
| `InvalidVpc.NotFound` | HALT | 0 | — | qcloud-vpc-ops | Verify VPC exists |
| `RequestLimitExceeded` | RETRY | 3 | exponential | — | Back off and retry |
| `InternalError` | RETRY | 3 | 2s,4s,8s | — | Escalate with RequestId |
| `InvalidParameter.ImageIdMalformed` | FIX | 1 | — | — | Use DescribeImages |
"""

LEGACY_3COL_TABLE = """\
| Error Code | Max Retries | Recovery |
|------------|-------------|----------|
| `InvalidVpc.NotFound` | 0 | HALT. Delegate to qcloud-vpc-ops |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT if persists |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
"""

LEGACY_5COL_TABLE = """\
| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
"""


class StandardFormatTests(unittest.TestCase):
    """6-col standard format → all fields populated."""

    def test_extracts_all_rules(self):
        rules = parse_error_table(STANDARD_TABLE)
        self.assertEqual(len(rules), 4,
                         f"expected 4 rules from 4-row table, got {len(rules)}")

    def test_action_halt(self):
        rules = parse_error_table(STANDARD_TABLE)
        rule = next(r for r in rules if r.code == "InvalidVpc.NotFound")
        self.assertEqual(rule.action, Action.HALT)
        self.assertEqual(rule.delegate_to, "qcloud-vpc-ops")
        self.assertEqual(rule.max_retries, 0)

    def test_action_retry_exponential(self):
        rules = parse_error_table(STANDARD_TABLE)
        rule = next(r for r in rules if r.code == "RequestLimitExceeded")
        self.assertEqual(rule.action, Action.RETRY)
        self.assertEqual(rule.max_retries, 3)
        self.assertEqual(rule.backoff_strategy, "exponential")

    def test_action_retry_with_explicit_seconds(self):
        rules = parse_error_table(STANDARD_TABLE)
        rule = next(r for r in rules if r.code == "InternalError")
        self.assertEqual(rule.action, Action.RETRY)
        self.assertEqual(rule.max_retries, 3)
        self.assertEqual(rule.backoff_seconds, [2, 4, 8])

    def test_action_fix(self):
        rules = parse_error_table(STANDARD_TABLE)
        rule = next(r for r in rules if r.code == "InvalidParameter.ImageIdMalformed")
        self.assertEqual(rule.action, Action.FIX)
        self.assertEqual(rule.max_retries, 1)


class LegacyFormatTests(unittest.TestCase):
    """3-5 col legacy format → Action inferred from Recovery text."""

    def test_legacy_3col_halt_with_delegate(self):
        rules = parse_error_table(LEGACY_3COL_TABLE)
        rule = next(r for r in rules if r.code == "InvalidVpc.NotFound")
        self.assertEqual(rule.action, Action.HALT)
        self.assertEqual(rule.delegate_to, "qcloud-vpc-ops")
        self.assertEqual(rule.max_retries, 0)

    def test_legacy_3col_retry_with_seconds(self):
        rules = parse_error_table(LEGACY_3COL_TABLE)
        rule = next(r for r in rules if r.code == "InternalError")
        self.assertEqual(rule.action, Action.RETRY)
        self.assertEqual(rule.max_retries, 3)
        self.assertEqual(rule.backoff_seconds, [2, 4, 8])

    def test_legacy_3col_retry_exponential(self):
        rules = parse_error_table(LEGACY_3COL_TABLE)
        rule = next(r for r in rules if r.code == "RequestLimitExceeded")
        self.assertEqual(rule.action, Action.RETRY)
        self.assertEqual(rule.backoff_strategy, "exponential")

    def test_legacy_5col(self):
        rules = parse_error_table(LEGACY_5COL_TABLE)
        self.assertGreaterEqual(len(rules), 2,
                                "5-col legacy table should still parse rows")
        rule = next(r for r in rules if r.code == "InternalError")
        self.assertEqual(rule.action, Action.RETRY)
        self.assertEqual(rule.max_retries, 3)


class EmptyAndEdgeCaseTests(unittest.TestCase):
    """Empty input & non-table text."""

    def test_empty_string_returns_empty(self):
        self.assertEqual(parse_error_table(""), [])

    def test_no_tables_returns_empty(self):
        text = "# Just a heading\n\nSome prose, no tables.\n"
        self.assertEqual(parse_error_table(text), [])

    def test_skips_separator_rows(self):
        # A row of just dashes is not data
        text = "| --- | --- |\n"
        self.assertEqual(parse_error_table(text), [])

    def test_mixed_tables_standard_then_legacy(self):
        text = STANDARD_TABLE + "\nAnd later:\n\n" + LEGACY_3COL_TABLE
        rules = parse_error_table(text)
        # Standard = 4, legacy = 3 → 7 total
        self.assertEqual(len(rules), 7)
        codes = {r.code for r in rules}
        self.assertIn("InvalidVpc.NotFound", codes)
        self.assertIn("InternalError", codes)


class RealWorldTests(unittest.TestCase):
    """Pull real error tables from a skill dir if available (smoke test)."""

    def test_parse_cvm_runinstances_errors(self):
        # Real CVM SKILL.md line range (best-effort: skip if file missing)
        skill = Path(__file__).resolve().parents[1] / "qcloud-cvm-ops" / "SKILL.md"
        if not skill.exists():
            self.skipTest("qcloud-cvm-ops/SKILL.md not on disk")
        rules = parse_error_table(skill.read_text(encoding="utf-8"))
        # Must pick up at least the InternalError + RequestLimitExceeded rows
        codes = {r.code for r in rules}
        self.assertIn("InternalError", codes)
        self.assertIn("RequestLimitExceeded", codes)
        # And they must be RETRY
        for r in rules:
            if r.code in ("InternalError", "RequestLimitExceeded"):
                self.assertEqual(r.action, Action.RETRY,
                                 f"{r.code} should be RETRY, got {r.action}")


if __name__ == "__main__":
    unittest.main()