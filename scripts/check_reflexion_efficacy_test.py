#!/usr/bin/env python3
"""Tests for check_reflexion_efficacy.py."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_reflexion_efficacy as crpe


class TestReflexionEfficacyGate(unittest.TestCase):
    """Assert the CI gate for the reflexion memory loop."""

    def _write_thresholds(self, data: dict) -> None:
        (ROOT / "assets" / "shared" / "thresholds.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def _vacuous(self) -> dict:
        """No traces with injection."""
        return {
            "runs_total": 78,
            "runs_with_injection": 0,
            "hint_coverage": 0.0,
            "non_vacuous": False,
            "patterns": {},
        }

    def _non_vacuous(self, n: int = 3) -> dict:
        """n traces carrying ≥1 failure-pattern hint."""
        return {
            "runs_total": 78,
            "runs_with_injection": n,
            "hint_coverage": round(n / 78, 3),
            "non_vacuous": True,
            "patterns": {
                "L3|credential_leak": {
                    "injected_runs": n,
                    "failed_after_injection": 0,
                    "recurred_runs": 0,
                    "prevention_rate": 1.0,
                }
            },
        }

    @patch("subprocess.run")
    def test_vacuous_corpus_exits_1(self, mock_run: unittest.mock.MagicMock) -> None:
        mock_run.return_value.stdout = json.dumps(self._vacuous())
        self._write_thresholds({"reflexion_min_injected_runs": 1})
        with patch.object(crpe, "THRESHOLDS", ROOT / "assets" / "shared" / "thresholds.json"):
            with patch.object(crpe, "load_thresholds", crpe.load_thresholds):
                with patch.object(crpe, "load_efficacy_report", lambda: self._vacuous()):
                    self.assertEqual(crpe.main(), 1)

    @patch("subprocess.run")
    def test_below_threshold_exits_1(self, mock_run: unittest.mock.MagicMock) -> None:
        self._write_thresholds({"reflexion_min_injected_runs": 5})
        with patch.object(crpe, "load_efficacy_report", lambda: self._non_vacuous(3)):
            self.assertEqual(crpe.main(), 1)

    @patch("subprocess.run")
    def test_sufficient_injections_exits_0(self, mock_run: unittest.mock.MagicMock) -> None:
        self._write_thresholds({"reflexion_min_injected_runs": 3})
        with patch.object(crpe, "load_efficacy_report", lambda: self._non_vacuous(5)):
            self.assertEqual(crpe.main(), 0)

    @patch("subprocess.run")
    def test_missing_threshold_key_exits_2(self, mock_run: unittest.mock.MagicMock) -> None:
        self._write_thresholds({})
        with patch.object(crpe, "load_efficacy_report", lambda: self._non_vacuous(5)):
            self.assertEqual(crpe.main(), 2)


if __name__ == "__main__":
    unittest.main()
