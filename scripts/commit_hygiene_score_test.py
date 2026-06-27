#!/usr/bin/env python3
"""Unit tests for scripts/commit_hygiene_score.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import commit_hygiene_score as chs  # noqa: E402


def _rec(verdict: str, products: list[str] | None = None) -> dict:
    return {
        "commit": "abc",
        "ts": "2026-06-27T00:00:00Z",
        "verdict": verdict,
        "products": products or [],
        "files_modified": 0,
        "files_added": 0,
        "reason": "",
    }


class M1Tests(unittest.TestCase):
    def test_red_line_stop_is_violation(self) -> None:
        self.assertTrue(chs.is_m1_violation(_rec("red-line-stop")))

    def test_ok_is_not_violation(self) -> None:
        self.assertFalse(chs.is_m1_violation(_rec("ok")))

    def test_partial_is_not_violation(self) -> None:
        # Partial = uncertainty, not a red line. Only counts toward M2.
        self.assertFalse(chs.is_m1_violation(_rec("partial")))


class M2Tests(unittest.TestCase):
    def test_partial_counts_as_rollback(self) -> None:
        self.assertTrue(chs.is_m2_rollback(_rec("partial")))

    def test_ok_does_not_count(self) -> None:
        self.assertFalse(chs.is_m2_rollback(_rec("ok")))

    def test_red_line_stop_counts_as_rollback_too(self) -> None:
        # A red-line-stop is both M1 and M2 (operator-paused commit).
        self.assertTrue(chs.is_m2_rollback(_rec("red-line-stop")))


class ScoreWindowTests(unittest.TestCase):
    def test_empty_window(self) -> None:
        m = chs.score_window([])
        self.assertEqual(m["m1_violations"], 0)
        self.assertEqual(m["m2_total"], 0)
        self.assertEqual(m["m2_rollback"], 0)
        self.assertEqual(m["m2_rate"], 0.0)

    def test_all_ok(self) -> None:
        records = [_rec("ok"), _rec("ok"), _rec("ok")]
        m = chs.score_window(records)
        self.assertEqual(m, {"m1_violations": 0, "m2_total": 3, "m2_rollback": 0, "m2_rate": 0.0})

    def test_one_red_line_in_window(self) -> None:
        records = [_rec("ok"), _rec("red-line-stop"), _rec("ok")]
        m = chs.score_window(records)
        self.assertEqual(m["m1_violations"], 1)
        self.assertEqual(m["m2_rollback"], 1)  # only the red-line-stop
        self.assertEqual(m["m2_total"], 3)

    def test_partial_mixed(self) -> None:
        # 5 records: 1 partial, 4 ok → M2 rate = 0.2 (at threshold)
        records = [_rec("partial")] + [_rec("ok")] * 4
        m = chs.score_window(records)
        self.assertEqual(m["m1_violations"], 0)
        self.assertEqual(m["m2_rollback"], 1)
        self.assertEqual(m["m2_total"], 5)
        self.assertEqual(m["m2_rate"], 0.2)


class RecommendTests(unittest.TestCase):
    def test_observe_when_too_few_commits(self) -> None:
        m = chs.score_window([_rec("ok")] * 3)
        self.assertEqual(chs.recommend(m, min_commits=5), "observe")

    def test_promote_when_clean(self) -> None:
        m = chs.score_window([_rec("ok")] * 5)
        self.assertEqual(chs.recommend(m, min_commits=5), "promote")

    def test_promote_when_at_threshold(self) -> None:
        # 1 partial in 5 → 0.2 rate → promote (≤ 0.20)
        records = [_rec("partial")] + [_rec("ok")] * 4
        m = chs.score_window(records)
        self.assertEqual(chs.recommend(m, min_commits=5), "promote")

    def test_extend_when_over_threshold(self) -> None:
        # 2 partial in 5 → 0.4 rate → extend
        records = [_rec("partial")] * 2 + [_rec("ok")] * 3
        m = chs.score_window(records)
        self.assertEqual(chs.recommend(m, min_commits=5), "extend")

    def test_rollback_on_any_m1(self) -> None:
        records = [_rec("red-line-stop")] + [_rec("ok")] * 5
        m = chs.score_window(records)
        self.assertEqual(chs.recommend(m, min_commits=5), "rollback")


if __name__ == "__main__":
    unittest.main()