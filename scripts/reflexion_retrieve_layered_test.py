#!/usr/bin/env python3
"""Unit tests for P0-B layered reflexion_retrieve.py.

Covers:
  T1: load_all_layers reads hot/warm/cold
  T2: cross-layer dedup: hot key preferred over warm/cold
  T3: _score_pattern skill match → base=3.0
  T4: _score_pattern command match only → base=2.0
  T5: _score_pattern no match → None (filtered)
  T6: composite score >= 2.0 threshold filter
  T7: load_failure_patterns layered mode returns top_n
  T8: load_failure_patterns --layer flag returns single layer
"""

import sys
import unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
import reflexion_retrieve as rr


_TODAY = date.today().strftime("%Y-%m-%d")


def pattern(skill="cvm", command="Run", error="Err", count=1,
            last_seen=None, severity="minor"):
    return {
        "category": "runtime",
        "skill": skill,
        "command": command,
        "error": error,
        "fix": "Fix it",
        "count": count,
        "severity": severity,
        "first_seen": _TODAY,
        "last_seen": last_seen or _TODAY,
        "reusable": True,
    }


class TestLoadAllLayers(unittest.TestCase):

    def test_load_all_layers_with_empty_warm_cold(self):
        """Missing warm/cold files return empty dicts."""
        # load_all_layers now lives in _failure_pattern_store
        from _failure_pattern_store import load_all_layers as _load_all_layers
        hot, warm, cold = _load_all_layers()
        # hot may have existing data; warm/cold should be empty if files missing
        self.assertIsInstance(hot, dict)
        self.assertEqual(warm, {})
        self.assertEqual(cold, {})


class TestScorePattern(unittest.TestCase):

    def test_skill_match_base_3(self):
        p = pattern(skill="cvm", command="Run", error="Err")
        result = rr._score_pattern(p, "cvm", None)
        self.assertIsNotNone(result)
        # base=3.0, severity=minor(1.0), decay=1.0(today) → 3.0
        self.assertAlmostEqual(result[0], 3.0)

    def test_severity_critical_gives_9_score(self):
        """severity=critical (weight=3.0) + skill match (base=3.0) + today (decay=1.0) = 9.0"""
        p = pattern(skill="cvm", command="Run", error="Err", severity="critical")
        result = rr._score_pattern(p, "cvm", None)
        self.assertAlmostEqual(result[0], 9.0)

    def test_severity_major_gives_6_score(self):
        """severity=major (weight=2.0) + skill match (base=3.0) + today = 6.0"""
        p = pattern(skill="cvm", command="Run", error="Err", severity="major")
        result = rr._score_pattern(p, "cvm", None)
        self.assertAlmostEqual(result[0], 6.0)

    def test_decay_7_to_30_days(self):
        """7-30 days: decay=0.7. base=3.0 * severity=minor(1.0) * 0.7 = 2.1 >= 2.0 ✓"""
        import datetime
        date_15_days_ago = (datetime.date.today() - datetime.timedelta(days=15)).strftime("%Y-%m-%d")
        p = pattern(skill="cvm", command="Run", error="Err", last_seen=date_15_days_ago)
        result = rr._score_pattern(p, "cvm", None)
        self.assertAlmostEqual(result[0], 2.1)

    def test_decay_30_to_90_days(self):
        """30-90 days: decay=0.3. base=3.0 * 1.0 * 0.3 = 0.9 < 2.0 → filtered"""
        import datetime
        date_60_days_ago = (datetime.date.today() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
        p = pattern(skill="cvm", command="Run", error="Err", last_seen=date_60_days_ago)
        result = rr._score_pattern(p, "cvm", None)
        self.assertIsNone(result)  # 0.9 < 2.0 threshold

    def test_recency_decay_none_returns_1(self):
        """last_seen=None → decay=1.0 (treat as recent)"""
        p = pattern(skill="cvm", command="Run", error="Err", last_seen=None)
        result = rr._score_pattern(p, "cvm", None)
        self.assertAlmostEqual(result[0], 3.0)  # base=3.0 * 1.0 * 1.0

    def test_command_only_base_2(self):
        p = pattern(skill="other", command="Run", error="Err")
        result = rr._score_pattern(p, "cvm", "Run")
        self.assertIsNotNone(result)
        # base=2.0, severity=minor(1.0), decay=1.0 → 2.0
        self.assertAlmostEqual(result[0], 2.0)

    def test_no_match_returns_none(self):
        p = pattern(skill="other", command="Other", error="Err")
        result = rr._score_pattern(p, "cvm", None)
        self.assertIsNone(result)

    def test_composite_below_threshold_filtered(self):
        """composite < 2.0 should be filtered out."""
        # Create pattern with base=2.0, severity=minor(1.0), but >90 days old → decay=0.1
        # 2.0 * 1.0 * 0.1 = 0.2 < 2.0 → filtered
        old_date = (date.today() - __import__('datetime').timedelta(days=100)).strftime("%Y-%m-%d")
        p = pattern(skill="other", command="Run", error="Err",
                    last_seen=old_date)
        result = rr._score_pattern(p, "cvm", "Run")
        self.assertIsNone(result)  # composite=0.2 < 2.0 threshold


class TestCrossLayerDedup(unittest.TestCase):

    def test_hot_preferred_over_warm(self):
        """Same key in hot and warm → hot entry returned."""
        key = ("cvm", "Run", "Err")
        hot = {key: pattern(skill="cvm", command="Run", error="Err", count=5)}
        warm = {key: pattern(skill="cvm", command="Run", error="Err", count=2)}
        cold = {}

        with patch.object(rr, 'load_all_layers', return_value=(hot, warm, cold)):
            results = rr.load_failure_patterns("cvm", top_n=10)
        # hot entry should appear (count=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 5)

    def test_hot_preferred_over_cold(self):
        """Same key in hot and cold → hot entry returned."""
        key = ("cvm", "Run", "Err")
        hot = {key: pattern(skill="cvm", command="Run", error="Err", count=5)}
        warm = {}
        cold = {key: pattern(skill="cvm", command="Run", error="Err", count=10)}

        with patch.object(rr, 'load_all_layers', return_value=(hot, warm, cold)):
            results = rr.load_failure_patterns("cvm", top_n=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 5)  # hot, not cold

    def test_warm_entry_returned_when_not_in_hot(self):
        """Key only in warm → warm entry returned."""
        hot = {}
        warm = {("cvm", "Run", "Err"): pattern(skill="cvm", command="Run", error="Err", count=3)}
        cold = {}

        with patch.object(rr, 'load_all_layers', return_value=(hot, warm, cold)):
            results = rr.load_failure_patterns("cvm", top_n=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 3)

    def test_warm_preferred_over_cold(self):
        """Same key in warm and cold (not in hot) → warm entry returned."""
        key = ("cvm", "Run", "Err")
        hot = {}
        warm = {key: pattern(skill="cvm", command="Run", error="Err", count=5)}
        cold = {key: pattern(skill="cvm", command="Run", error="Err", count=2)}

        with patch.object(rr, 'load_all_layers', return_value=(hot, warm, cold)):
            results = rr.load_failure_patterns("cvm", top_n=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["count"], 5)  # warm, not cold

    def test_top_n_truncation(self):
        """More than top_n results → only top_n returned."""
        hot = {f"k{i}": pattern(skill="cvm", command=f"cmd{i}", error=f"Err{i}",
                                 count=10-i) for i in range(5)}
        warm, cold = {}, {}

        with patch.object(rr, 'load_all_layers', return_value=(hot, warm, cold)):
            results = rr.load_failure_patterns("cvm", top_n=3)
        self.assertEqual(len(results), 3)
        # Sorted by score desc (score=3.0 for all skill matches), then count desc
        self.assertGreaterEqual(results[0]["count"], results[1]["count"])


class TestLayerFlag(unittest.TestCase):

    def test_layer_flag_reads_directly(self):
        """--layer flag reads directly from the specified layer path (not load_all_layers)."""
        # When layer is set, it reads layer_path directly, not load_all_layers.
        # Verify the code path uses the correct path.
        with patch.object(rr, 'parse_existing', return_value={}):
            results = rr.load_failure_patterns("cvm", top_n=10, layer="warm")
            self.assertEqual(len(results), 0)  # mocked to empty


if __name__ == "__main__":
    unittest.main(verbosity=2)
