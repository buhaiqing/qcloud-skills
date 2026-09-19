#!/usr/bin/env python3
"""Unit tests for Phase 4 runtime router (harness_router)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_skill_registry
import harness_router

# Two-skill registry where each skill is matched by distinct tokens, so the
# owning-skill ground truth is unambiguous (no alphabetical tie-break involved).
TWO_SKILLS = {
    "skills": [
        {"name": "qcloud-cvm-ops", "intent_keywords": ["RunCvmInstance"]},
        {"name": "qcloud-cdb-ops", "intent_keywords": ["DescribeDbCluster"]},
    ]
}


class HarnessRouterTest(unittest.TestCase):
    def test_router_selects_top1_in_memory(self) -> None:
        registry = {
            "skills": [
                {
                    "name": "qcloud-cvm-ops",
                    "cli_applicability": "dual-path",
                    "description": "CVM `DescribeInstances` `RunInstances`",
                    "intent_keywords": ["DescribeInstances", "RunInstances"],
                    "path": "qcloud-cvm-ops",
                    "delegate_to": "",
                },
                {
                    "name": "qcloud-cdb-ops",
                    "cli_applicability": "dual-path",
                    "description": "CDB `DescribeDBInstances`",
                    "intent_keywords": ["DescribeDBInstances"],
                    "path": "qcloud-cdb-ops",
                    "delegate_to": "",
                },
            ]
        }
        result = harness_router.select_top1(registry, "describe my CVM instances")
        self.assertEqual(result["top1_skill"], "qcloud-cvm-ops")

    def test_router_selects_cvm_on_real_registry(self) -> None:
        """L5/L6: prove the algorithm ranks cvm first for a clear cvm query
        (token-overlap on 'describe'+'instances'), not just that it returns
        *a* name. Guards against vacuous ranking. The companion confusion-matrix
        test asserts the metric is meaningfully > 0 across the full eval set."""
        registry = build_skill_registry.build()
        top = harness_router.select_top1(registry, "describe my CVM instances")["top1_skill"]
        self.assertEqual(top, "qcloud-cvm-ops", f"clear cvm query -> {top}")

    def test_confusion_matrix_from_eval_queries(self) -> None:
        registry = build_skill_registry.build()
        eval_path = ROOT / "qcloud-cvm-ops" / "assets" / "eval_queries.json"
        if not eval_path.exists():
            self.skipTest(f"eval fixture missing: {eval_path}")
        eval_queries = json.loads(eval_path.read_text())
        result = harness_router.confusion_matrix(registry, eval_queries, "qcloud-cvm-ops")
        for key in ("top1_accuracy", "misdelegation", "fallback"):
            self.assertIn(key, result)
            self.assertIsInstance(result[key], float)
            self.assertGreaterEqual(result[key], 0.0)
            self.assertLessEqual(result[key], 1.0)
        # L5/L6: the matrix must be meaningful, not vacuous zeros. cvm's own
        # positive eval queries should route to cvm (top1_accuracy > 0).
        self.assertGreater(
            result["top1_accuracy"], 0.0,
            "cvm positive queries must route to cvm (non-vacuous accuracy)",
        )

    # --- ground truth is the owning skill, not a per-item `intent` key ---

    def test_confusion_matrix_without_intent_field_is_not_constant(self) -> None:
        """L5/L8: 29 of 31 eval_queries.json carry no `intent` key. The metric
        must still measure something (previously it was a structural 0.0)."""
        eval_queries = [
            {"query": "run cvm instance", "should_trigger": True},
            {"query": "cvm instance please", "should_trigger": True},
            {"query": "describe db cluster", "should_trigger": False},
        ]
        self.assertFalse(any("intent" in q for q in eval_queries))
        result = harness_router.confusion_matrix(TWO_SKILLS, eval_queries, "qcloud-cvm-ops")
        self.assertEqual(result["top1_accuracy"], 1.0)  # both positives land on cvm
        self.assertEqual(result["misdelegation"], 0.0)  # the negative lands on cdb

    def test_unmatched_query_returns_empty_top1(self) -> None:
        """L6: no silent alphabet fallback — an unmatched query routes nowhere
        rather than to whichever skill sorts first."""
        result = harness_router.select_top1(TWO_SKILLS, "write me a poem")
        self.assertEqual(result["top1_skill"], "")
        self.assertEqual(result["score"], 0)
        # The old bug returned the alphabetically-first skill here.
        self.assertNotEqual(result["top1_skill"], "qcloud-cdb-ops")
        self.assertEqual(result["candidates"], ["qcloud-cvm-ops", "qcloud-cdb-ops"])

    def test_negative_query_matching_owner_counts_as_misdelegation(self) -> None:
        """A negative query that DOES route to the owning skill is a false
        positive and must be counted as misdelegation."""
        eval_queries = [
            {"query": "run cvm instance", "should_trigger": True},
            {"query": "cvm instance for my blog", "should_trigger": False},
            {"query": "cvm instance again", "should_trigger": False},
        ]
        result = harness_router.confusion_matrix(TWO_SKILLS, eval_queries, "qcloud-cvm-ops")
        self.assertEqual(result["top1_accuracy"], 1.0)
        self.assertEqual(result["misdelegation"], 1.0)


if __name__ == "__main__":
    unittest.main()
