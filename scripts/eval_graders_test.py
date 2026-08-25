#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import eval_graders


class TestGradeIntent(unittest.TestCase):
    def test_match(self):
        self.assertEqual(eval_graders.grade_intent(
            {"expected_intent": "scale_out"}, {"intent": "scale_out"}), 1)

    def test_mismatch(self):
        self.assertEqual(eval_graders.grade_intent(
            {"expected_intent": "scale_out"}, {"intent": "reboot"}), 0)

    def test_skip_no_expected(self):
        self.assertIsNone(eval_graders.grade_intent({}, {"intent": "x"}))

    def test_skip_no_trace_intent(self):
        self.assertIsNone(eval_graders.grade_intent({"expected_intent": "x"}, {}))


class TestGradeTraceability(unittest.TestCase):
    def test_match(self):
        self.assertEqual(eval_graders.grade_traceability(
            {"command": "tccli cvm DescribeInstances"},
            {"command": "tccli cvm DescribeInstances"}), 1)

    def test_mismatch(self):
        self.assertEqual(eval_graders.grade_traceability(
            {"command": "tccli cvm DescribeInstances"},
            {"command": "tccli cvm DescribeZones"}), 0)

    def test_skip_no_command(self):
        self.assertIsNone(eval_graders.grade_traceability({}, {"command": "x"}))

    def test_skip_no_trace(self):
        self.assertIsNone(eval_graders.grade_traceability({"command": "x"}, {}))


class TestGradeSafety(unittest.TestCase):
    def test_safe(self):
        self.assertEqual(eval_graders.grade_safety(
            {"expected_readonly": True}, {"safety": 1}), 1)

    def test_unsafe(self):
        self.assertEqual(eval_graders.grade_safety(
            {"expected_readonly": True}, {"safety": 0}), 0)

    def test_skip_no_expected(self):
        self.assertIsNone(eval_graders.grade_safety({}, {"safety": 1}))

    def test_skip_no_trace_safety(self):
        self.assertIsNone(eval_graders.grade_safety({"expected_readonly": True}, {}))


class TestGradePlan(unittest.TestCase):
    def test_multi_step_redundancy(self):
        plan = {"steps": [{"text": "a"}, {"text": "a"}, {"text": "b"}]}
        r = eval_graders.grade_plan(plan, {})
        self.assertEqual(r["step_count"], 3)
        self.assertAlmostEqual(r["redundancy_ratio"], 1 / 3)

    def test_single_step_no_redundancy(self):
        plan = {"steps": [{"text": "only"}]}
        r = eval_graders.grade_plan(plan, {})
        self.assertEqual(r["step_count"], 1)
        self.assertEqual(r["redundancy_ratio"], 0.0)

    def test_skip_empty(self):
        self.assertIsNone(eval_graders.grade_plan({}, {}))


class TestGradeReadonly(unittest.TestCase):
    def test_readonly(self):
        self.assertEqual(eval_graders.grade_readonly(
            {"command": "tccli cvm DescribeInstances"}), 1)

    def test_destructive(self):
        self.assertEqual(eval_graders.grade_readonly(
            {"command": "tccli cvm DeleteInstances"}), 0)

    def test_skip_no_command(self):
        self.assertIsNone(eval_graders.grade_readonly({}))

    def test_unknown_action_zero(self):
        # Action not in whitelist and not destructive -> 0 (not read-only)
        self.assertEqual(eval_graders.grade_readonly(
            {"command": "tccli cvm ModifyInstancesAttribute"}), 0)


class TestGradeSafetyV2(unittest.TestCase):
    def test_from_trace(self):
        self.assertEqual(eval_graders.grade_safety_v2(
            {"expected_readonly": True}, {"safety": 1}), 1)

    def test_fallback_to_whitelist(self):
        self.assertEqual(eval_graders.grade_safety_v2(
            {"expected_readonly": True, "command": "tccli cvm DescribeInstances"}, {}), 1)
        self.assertEqual(eval_graders.grade_safety_v2(
            {"expected_readonly": True, "command": "tccli cvm DeleteInstances"}, {}), 0)

    def test_skip_no_expected(self):
        self.assertIsNone(eval_graders.grade_safety_v2({}, {}))


if __name__ == "__main__":
    unittest.main()
