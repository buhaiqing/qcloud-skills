#!/usr/bin/env python3
"""Unit tests for Phase 4 runtime router (harness_router)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harness_router  # noqa: E402
import build_skill_registry  # noqa: E402


class HarnessRouterTest(unittest.TestCase):
    def test_router_selects_top1(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
