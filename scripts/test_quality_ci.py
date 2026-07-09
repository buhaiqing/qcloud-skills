#!/usr/bin/env python3
"""Tests for quality score CI integration in validate_local.py."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from validate_local import (
    _compute_quality_score,
    _determine_upgrade_signal,
    _generate_recommendations,
    run_quality_score,
)


class TestComputeQualityScore(unittest.TestCase):
    def test_empty_report_returns_100(self) -> None:
        report: dict = {"by_skill": {}, "total_executions": 0}
        self.assertEqual(_compute_quality_score(report), 100.0)

    def test_perfect_score(self) -> None:
        report = {
            "by_skill": {
                "skill-a": {
                    "pass": 10,
                    "dimensions_avg": {d: 1.0 for d in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]},
                }
            },
            "total_executions": 10,
        }
        self.assertEqual(_compute_quality_score(report), 100.0)

    def test_mixed_score(self) -> None:
        report = {
            "by_skill": {
                "skill-a": {
                    "pass": 5,
                    "dimensions_avg": {"correctness": 0.5, "safety": 0.5, "idempotency": 0.5, "traceability": 0.5, "spec_compliance": 0.5},
                }
            },
            "total_executions": 10,
        }
        score = _compute_quality_score(report)
        self.assertAlmostEqual(score, 50.0, places=1)


class TestDetermineUpgradeSignal(unittest.TestCase):
    def test_no_upgrade_skills_returns_none(self) -> None:
        report = {
            "upgrade_signal": [],
            "by_skill": {"skill-a": {}},
        }
        self.assertEqual(_determine_upgrade_signal(report), "none")

    def test_one_of_four_returns_major(self) -> None:
        report = {
            "upgrade_signal": ["skill-a"],
            "by_skill": {"skill-a": {}, "skill-b": {}, "skill-c": {}, "skill-d": {}},
        }
        self.assertEqual(_determine_upgrade_signal(report), "major")

    def test_one_of_three_returns_major(self) -> None:
        report = {
            "upgrade_signal": ["skill-a"],
            "by_skill": {"skill-a": {}, "skill-b": {}, "skill-c": {}},
        }
        self.assertEqual(_determine_upgrade_signal(report), "major")

    def test_one_of_two_returns_critical(self) -> None:
        report = {
            "upgrade_signal": ["skill-a"],
            "by_skill": {"skill-a": {}, "skill-b": {}},
        }
        self.assertEqual(_determine_upgrade_signal(report), "critical")

    def test_half_returns_critical(self) -> None:
        report = {
            "upgrade_signal": ["skill-a", "skill-b"],
            "by_skill": {"skill-a": {}, "skill-b": {}, "skill-c": {}, "skill-d": {}},
        }
        self.assertEqual(_determine_upgrade_signal(report), "critical")

    def test_more_than_half_returns_critical(self) -> None:
        report = {
            "upgrade_signal": ["skill-a", "skill-b", "skill-c"],
            "by_skill": {"skill-a": {}, "skill-b": {}, "skill-c": {}, "skill-d": {}},
        }
        self.assertEqual(_determine_upgrade_signal(report), "critical")


class TestGenerateRecommendations(unittest.TestCase):
    def test_empty_upgrade_list_returns_empty(self) -> None:
        report = {"upgrade_signal": [], "by_skill": {}}
        self.assertEqual(_generate_recommendations(report), [])

    def test_low_pass_rate_generates_recommendation(self) -> None:
        report = {
            "upgrade_signal": ["skill-a"],
            "by_skill": {"skill-a": {"pass_rate": 0.5, "dimensions_avg": {}}},
        }
        recs = _generate_recommendations(report)
        self.assertEqual(len(recs), 1)
        self.assertIn("improve pass rate", recs[0])

    def test_low_dimension_generates_recommendation(self) -> None:
        report = {
            "upgrade_signal": ["skill-a"],
            "by_skill": {"skill-a": {"pass_rate": 1.0, "dimensions_avg": {"correctness": 0.5}}},
        }
        recs = _generate_recommendations(report)
        self.assertEqual(len(recs), 1)
        self.assertIn("strengthen dimensions", recs[0])
        self.assertIn("correctness", recs[0])


class TestRunQualityScore(unittest.TestCase):
    def test_failed_subprocess_returns_critical(self) -> None:
        mock_result = Mock(returncode=1, stderr="error")
        with patch("validate_local.subprocess.run", return_value=mock_result):
            result = run_quality_score(Path("/tmp"))
        self.assertEqual(result["upgrade_signal"], "critical")
        self.assertEqual(result["quality_score"], 0.0)

    def test_invalid_json_returns_critical(self) -> None:
        mock_result = Mock(returncode=0, stdout="not json")
        with patch("validate_local.subprocess.run", return_value=mock_result):
            result = run_quality_score(Path("/tmp"))
        self.assertEqual(result["upgrade_signal"], "critical")

    def test_valid_json_returns_transformed(self) -> None:
        report = {
            "by_skill": {"skill-a": {"pass": 10, "dimensions_avg": {d: 1.0 for d in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]}}},
            "total_executions": 10,
            "upgrade_signal": [],
        }
        mock_result = Mock(returncode=0, stdout=json.dumps(report))
        with patch("validate_local.subprocess.run", return_value=mock_result):
            result = run_quality_score(Path("/tmp"))
        self.assertEqual(result["upgrade_signal"], "none")
        self.assertEqual(result["quality_score"], 100.0)
        self.assertEqual(result["recommendations"], [])


if __name__ == "__main__":
    unittest.main()
