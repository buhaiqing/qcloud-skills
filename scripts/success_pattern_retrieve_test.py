#!/usr/bin/env python3
"""Unit tests for success_pattern_retrieve.py.

Covers:
  T1: severity_weight(1)=3.0, (2)=2.0, (3)=1.0
  T2: recency_decay: none/unknown/empty → 1.0
  T3: composite score = base × severity × decay
  T4: skill mismatch → score=0
  T5: retrieve with top_n truncation
  T6: empty store → empty list
"""

import sys
import unittest
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from success_pattern_retrieve import (
    SuccessEntry,
    _severity_weight, recency_decay, compute_composite,
    retrieve_success_patterns,
)


class TestSeverityWeight(unittest.TestCase):

    def test_iter_1_is_3(self):
        self.assertEqual(_severity_weight(1), 3.0)

    def test_iter_2_is_2(self):
        self.assertEqual(_severity_weight(2), 2.0)

    def test_iter_3_is_1(self):
        self.assertEqual(_severity_weight(3), 1.0)

    def test_none_defaults_to_1(self):
        self.assertEqual(_severity_weight(None), 3.0)


class TestRecencyDecay(unittest.TestCase):

    def test_none_returns_1(self):
        self.assertEqual(recency_decay(None), 1.0)

    def test_empty_returns_1(self):
        self.assertEqual(recency_decay(""), 1.0)

    def test_invalid_format_returns_1(self):
        self.assertEqual(recency_decay("not-a-date"), 1.0)


class TestComputeComposite(unittest.TestCase):

    def test_iter1_skill_match_max_score(self):
        """iter=1 + skill match = 3.0 * 3.0 * 1.0 = 9.0 (today = decay=1.0)"""
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        entry = SuccessEntry(
            skill="cvm", operation="Run", command_signature="tccli cvm Run",
            full_command="", iter=1, count=1,
            first_hit=today, last_hit=today,
            scores={}, avg_iter=1.0,
        )
        score = compute_composite(entry, "cvm", None)
        self.assertAlmostEqual(score, 9.0)

    def test_iter3_skill_match_lower_score(self):
        """iter=3 → severity=1.0 → 3.0 * 1.0 * 1.0 = 3.0"""
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        entry = SuccessEntry(
            skill="cvm", operation="Run", command_signature="tccli cvm Run",
            full_command="", iter=3, count=1,
            first_hit=today, last_hit=today,
            scores={}, avg_iter=3.0,
        )
        score = compute_composite(entry, "cvm", None)
        self.assertAlmostEqual(score, 3.0)

    def test_operation_match_boosts_base(self):
        """skill+op match gives higher base than skill-only."""
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        entry = SuccessEntry(
            skill="cvm", operation="Run", command_signature="tccli cvm Run",
            full_command="", iter=1, count=1,
            first_hit=today, last_hit=today,
            scores={}, avg_iter=1.0,
        )
        score_op = compute_composite(entry, "cvm", "Run")
        score_other = compute_composite(entry, "cvm", "Stop")
        self.assertGreater(score_op, score_other)

    def test_skill_mismatch_returns_zero(self):
        """skill doesn't match → base=0 → score=0"""
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        entry = SuccessEntry(
            skill="redis", operation="Run", command_signature="tccli redis Run",
            full_command="", iter=1, count=1,
            first_hit=today, last_hit=today,
            scores={}, avg_iter=1.0,
        )
        score = compute_composite(entry, "cvm", None)
        self.assertEqual(score, 0.0)


class TestRetrieve(unittest.TestCase):

    def test_returns_n_results(self):
        """With ≥3 entries, retrieve returns top_n."""
        import success_pattern_retrieve as sr
        orig_h = sr.HOT_PATH
        orig_w = sr.WARM_PATH
        orig_c = sr.COLD_PATH

        with tempfile.TemporaryDirectory() as tmpdir:
            for name, path in [
                ("success-patterns.md", sr.HOT_PATH),
                ("success-patterns-warm.md", sr.WARM_PATH),
                ("success-patterns-cold.md", sr.COLD_PATH),
            ]:
                p = Path(tmpdir) / name
                p.write_text("# Success Patterns\n", encoding="utf-8")
            sr.HOT_PATH = Path(tmpdir) / "success-patterns.md"
            sr.WARM_PATH = Path(tmpdir) / "success-patterns-warm.md"
            sr.COLD_PATH = Path(tmpdir) / "success-patterns-cold.md"

            # Write 3 entries to hot
            from datetime import date
            today = date.today().strftime("%Y-%m-%d")
            sr.HOT_PATH.write_text(
                "# Success Patterns\n\n"
                "| Skill | Operation | CommandSignature | FullCommand | Iter | Count | FirstHit | LastHit | Scores | AvgIter |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                f"| `cvm` | `Run` | `tccli cvm Run1` | `` | 1 | 3 | {today} | {today} | {{}} | 1.0 |\n"
                f"| `cvm` | `Run` | `tccli cvm Run2` | `` | 1 | 2 | {today} | {today} | {{}} | 1.0 |\n"
                f"| `cvm` | `Run` | `tccli cvm Run3` | `` | 1 | 1 | {today} | {today} | {{}} | 1.0 |\n",
                encoding="utf-8",
            )
            try:
                results = retrieve_success_patterns("cvm", top_n=2)
                self.assertEqual(len(results), 2)
                # sorted by score desc = count desc
                self.assertEqual(results[0]["command_signature"], "tccli cvm Run1")
                self.assertEqual(results[1]["command_signature"], "tccli cvm Run2")
            finally:
                sr.HOT_PATH = orig_h
                sr.WARM_PATH = orig_w
                sr.COLD_PATH = orig_c

    def test_empty_store_returns_empty(self):
        """No patterns → returns empty list."""
        import success_pattern_retrieve as sr
        orig_h = sr.HOT_PATH
        orig_w = sr.WARM_PATH
        orig_c = sr.COLD_PATH

        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["success-patterns.md", "success-patterns-warm.md", "success-patterns-cold.md"]:
                (Path(tmpdir) / name).write_text("# Success Patterns\n", encoding="utf-8")
            sr.HOT_PATH = Path(tmpdir) / "success-patterns.md"
            sr.WARM_PATH = Path(tmpdir) / "success-patterns-warm.md"
            sr.COLD_PATH = Path(tmpdir) / "success-patterns-cold.md"
            try:
                results = retrieve_success_patterns("cvm")
                self.assertEqual(results, [])
            finally:
                sr.HOT_PATH = orig_h
                sr.WARM_PATH = orig_w
                sr.COLD_PATH = orig_c


if __name__ == "__main__":
    unittest.main(verbosity=2)
