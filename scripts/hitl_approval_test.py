#!/usr/bin/env python3
from __future__ import annotations

import unittest

from harness_safety import plan_hash
from hitl_approval import (
    ApprovalDecision,
    ApprovalTier,
    Decision,
    classify_action,
    request_approval,
)


class ClassifyActionTest(unittest.TestCase):
    def test_non_destructive_auto(self) -> None:
        self.assertEqual(classify_action("DescribeInstances", "critical"), ApprovalTier.AUTO)
        self.assertEqual(classify_action("ListBuckets", "high"), ApprovalTier.AUTO)

    def test_destructive_warning_token_bound(self) -> None:
        self.assertEqual(classify_action("delete bucket my-bucket", "warning"), ApprovalTier.TOKEN_BOUND)
        self.assertEqual(classify_action("terminate instances i-123", "info"), ApprovalTier.TOKEN_BOUND)

    def test_destructive_critical_human_review(self) -> None:
        self.assertEqual(
            classify_action("delete bucket my-bucket", "critical"), ApprovalTier.HUMAN_REVIEW
        )
        self.assertEqual(classify_action("remove instances i-123", "high"), ApprovalTier.HUMAN_REVIEW)

    def test_destructive_case_insensitive_severity(self) -> None:
        self.assertEqual(classify_action("delete bucket x", "HIGH"), ApprovalTier.HUMAN_REVIEW)
        self.assertEqual(classify_action("delete bucket x", "Warning"), ApprovalTier.TOKEN_BOUND)

    def test_destructive_unknown_severity_is_human_review(self) -> None:
        self.assertEqual(classify_action("delete bucket x", "unknown"), ApprovalTier.HUMAN_REVIEW)


class RequestApprovalAutoTest(unittest.TestCase):
    def test_auto_approved_and_logged(self) -> None:
        trace: dict[str, object] = {}
        dec = request_approval("DescribeInstances", "critical", trace, now=5.0)
        self.assertEqual(dec.tier, ApprovalTier.AUTO)
        self.assertEqual(dec.decision, Decision.APPROVED)
        self.assertEqual(dec.approver, "system")
        self.assertEqual(dec.token_hash, "")
        self.assertIsInstance(dec, ApprovalDecision)
        chain = trace["approval_chain"]  # type: ignore[index]
        self.assertEqual(len(chain), 1)  # type: ignore[arg-type]
        self.assertEqual(chain[0]["tier"], "auto")  # type: ignore[index]
        self.assertEqual(chain[0]["decision"], "approved")  # type: ignore[index]
        self.assertEqual(chain[0]["approver"], "system")  # type: ignore[index]

    def test_auto_callable_now(self) -> None:
        trace: dict[str, object] = {}
        dec = request_approval("DescribeInstances", "info", trace, now=lambda: 2.0)
        self.assertEqual(dec.decision, Decision.APPROVED)
        self.assertEqual(dec.timestamp, 2.0)


class RequestApprovalTokenBoundTest(unittest.TestCase):
    def test_valid_token_approved(self) -> None:
        plan = "delete bucket my-bucket"
        token = plan_hash(plan)
        trace: dict[str, object] = {}
        dec = request_approval(plan, "warning", trace, now=5.0, human_token=token)
        self.assertEqual(dec.tier, ApprovalTier.TOKEN_BOUND)
        self.assertEqual(dec.decision, Decision.APPROVED)
        self.assertEqual(dec.approver, "human-token")
        self.assertEqual(dec.token_hash, token)
        chain = trace["approval_chain"]  # type: ignore[index]
        self.assertEqual(chain[0]["token_hash"], token)  # type: ignore[index]

    def test_invalid_token_denied(self) -> None:
        plan = "delete bucket my-bucket"
        trace: dict[str, object] = {}
        dec = request_approval(plan, "warning", trace, now=5.0, human_token="bad-token")
        self.assertEqual(dec.decision, Decision.DENIED)
        self.assertEqual(trace["approval_chain"][0]["decision"], "denied")  # type: ignore[index]

    def test_missing_token_denied(self) -> None:
        plan = "delete bucket my-bucket"
        trace: dict[str, object] = {}
        dec = request_approval(plan, "warning", trace, now=5.0)
        self.assertEqual(dec.decision, Decision.DENIED)

    def test_timeout_degraded_no_token(self) -> None:
        plan = "delete bucket my-bucket"
        trace: dict[str, object] = {}
        dec = request_approval(plan, "warning", trace, now=100.0, timeout_s=30.0)
        self.assertEqual(dec.decision, Decision.TIMEOUT_DEGRADED)

    def test_timeout_degraded_invalid_token(self) -> None:
        plan = "delete bucket my-bucket"
        trace: dict[str, object] = {}
        dec = request_approval(plan, "warning", trace, now=100.0, timeout_s=30.0, human_token="bad")
        self.assertEqual(dec.decision, Decision.TIMEOUT_DEGRADED)

    def test_valid_token_wins_even_after_timeout(self) -> None:
        plan = "delete bucket my-bucket"
        token = plan_hash(plan)
        trace: dict[str, object] = {}
        dec = request_approval(plan, "warning", trace, now=100.0, timeout_s=30.0, human_token=token)
        self.assertEqual(dec.decision, Decision.APPROVED)


class RequestApprovalHumanReviewTest(unittest.TestCase):
    def test_with_approver_approved(self) -> None:
        plan = "delete bucket my-bucket"
        trace: dict[str, object] = {}
        dec = request_approval(plan, "critical", trace, now=5.0, human_approver="alice")
        self.assertEqual(dec.tier, ApprovalTier.HUMAN_REVIEW)
        self.assertEqual(dec.decision, Decision.APPROVED)
        self.assertEqual(dec.approver, "alice")
        self.assertEqual(trace["approval_chain"][0]["approver"], "alice")  # type: ignore[index]

    def test_without_approver_denied(self) -> None:
        plan = "delete bucket my-bucket"
        trace: dict[str, object] = {}
        dec = request_approval(plan, "critical", trace, now=5.0)
        self.assertEqual(dec.decision, Decision.DENIED)

    def test_empty_approver_denied(self) -> None:
        plan = "delete bucket my-bucket"
        trace: dict[str, object] = {}
        dec = request_approval(plan, "high", trace, now=5.0, human_approver="   ")
        self.assertEqual(dec.decision, Decision.DENIED)

    def test_timeout_degraded(self) -> None:
        plan = "delete bucket my-bucket"
        trace: dict[str, object] = {}
        dec = request_approval(plan, "critical", trace, now=100.0, timeout_s=30.0)
        self.assertEqual(dec.decision, Decision.TIMEOUT_DEGRADED)

    def test_approver_wins_after_timeout(self) -> None:
        plan = "delete bucket my-bucket"
        trace: dict[str, object] = {}
        dec = request_approval(plan, "critical", trace, now=100.0, timeout_s=30.0, human_approver="bob")
        self.assertEqual(dec.decision, Decision.APPROVED)


class TraceAppendTest(unittest.TestCase):
    def test_every_decision_logged_and_chain_grows(self) -> None:
        trace: dict[str, object] = {}
        request_approval("DescribeInstances", "info", trace, now=1.0)
        request_approval("delete bucket x", "warning", trace, now=2.0)
        request_approval("delete bucket x", "critical", trace, now=3.0, human_approver="alice")
        chain = trace["approval_chain"]  # type: ignore[index]
        self.assertEqual(len(chain), 3)  # type: ignore[arg-type]
        self.assertEqual(chain[0]["tier"], "auto")  # type: ignore[index]
        self.assertEqual(chain[1]["tier"], "token_bound")  # type: ignore[index]
        self.assertEqual(chain[2]["tier"], "human_review")  # type: ignore[index]
        for entry in chain:  # type: ignore[union-attr]
            self.assertIn("timestamp", entry)
            self.assertIn("reason", entry)
            self.assertIn("decision", entry)


if __name__ == "__main__":
    unittest.main()
