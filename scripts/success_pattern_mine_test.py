#!/usr/bin/env python3
"""Unit tests for success_pattern_mine.py.

Covers:
  T1: substitution merge — same key from pending updates hot count++/last_hit/avg_iter
  T2: warm revive       — key in warm within 30 days → moved back to hot
  T3: silence hot       — hot over limit → oldest last_hit demoted to warm
  T4: silence warm     — warm over limit → oldest last_hit archived to cold
  T5: cold hard cap    — cold over limit → lowest count pruned
  V1: self_verify detects duplicate keys across layers
  V2: self_verify detects capacity breach
  V3: self_verify detects key in two layers simultaneously
  V4: self_verify detects missing required fields
  V5: self_verify detects invalid last_hit format
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from success_pattern_mine import (  # noqa: F401
    SuccessEntry,
    HOT_LIMIT, WARM_LIMIT, COLD_LIMIT,
    merge_batch, self_verify, make_key,
    load_pending, write_pending_with_lock,
    full_scan,   # used by TestFullScan
)

# Shared sig that matches from_pending("tccli cvm RunInstances")[:80]
_PENDING_CMD = "tccli cvm RunInstances"
_PENDING_SIG = _PENDING_CMD  # [:80] of itself
_PENDING_OP = "RunInstances"

# Use today's date for recency_decay = 1.0 in most tests
_TODAY = date.today().strftime("%Y-%m-%d")


def e(skill="cvm", op=None, sig=None, cmd=None,
       iter_=1, count=1, first=None, last=None):
    op = op or _PENDING_OP
    sig = sig or _PENDING_SIG
    cmd = cmd or _PENDING_CMD
    return SuccessEntry(
        skill=skill, operation=op, command_signature=sig,
        full_command=cmd, iter=iter_, count=count,
        first_hit=first or _TODAY, last_hit=last or _TODAY,
        scores={}, avg_iter=float(iter_),
    )


class TestSubstitutionMerge(unittest.TestCase):

    def test_same_key_count_increment(self):
        """Pending with same key increments count and updates last_hit."""
        pending = [{
            "skill": "cvm", "operation": _PENDING_OP,
            "command": _PENDING_CMD,
            "iter": 1, "scores": {}, "timestamp": f"{_TODAY}T00:00:00",
        }]
        hot = {make_key(e(count=5, last=_TODAY)): e(count=5, last=_TODAY)}
        warm, cold = {}, {}
        h, _, _ = merge_batch(pending, hot, warm, cold)
        key = make_key(e())
        self.assertEqual(h[key].count, 6)
        self.assertEqual(h[key].last_hit, _TODAY)

    def test_avg_iter_weighted_update(self):
        """avg_iter is updated as weighted average."""
        pending = [{
            "skill": "cvm", "operation": _PENDING_OP,
            "command": _PENDING_CMD,
            "iter": 3, "scores": {}, "timestamp": f"{_TODAY}T00:00:00",
        }]
        hot = {make_key(e()): e(iter_=1, count=1, last=_TODAY)}
        warm, cold = {}, {}
        h, _, _ = merge_batch(pending, hot, warm, cold)
        key = make_key(e())
        # avg = (1*1 + 3*1) / 2 = 2.0
        self.assertAlmostEqual(h[key].avg_iter, 2.0)

    def test_new_key_appended_to_hot(self):
        """Pending with new key is appended to hot."""
        pending = [{
            "skill": "cvm", "operation": "StopInstances",
            "command": "tccli cvm StopInstances",
            "iter": 1, "scores": {}, "timestamp": f"{_TODAY}T00:00:00",
        }]
        hot, warm, cold = {}, {}, {}
        h, _, _ = merge_batch(pending, hot, warm, cold)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[list(h.keys())[0]].operation, "StopInstances")


class TestWarmRevive(unittest.TestCase):

    def test_revive_within_30_days(self):
        """Key in warm revived to hot when pending arrives within 30 days."""
        pending = [{
            "skill": "cvm", "operation": _PENDING_OP,
            "command": _PENDING_CMD,
            "iter": 1, "scores": {}, "timestamp": f"{_TODAY}T00:00:00",
        }]
        key = make_key(e())
        hot = {}
        warm = {key: e(count=3, last=_TODAY)}  # warm entry from today
        cold = {}
        h, w, _ = merge_batch(pending, hot, warm, cold)
        self.assertIn(key, h)
        self.assertNotIn(key, w)
        self.assertEqual(h[key].count, 4)

    def test_no_revive_beyond_30_days(self):
        """Key in warm NOT revived when gap > 30 days (new entry created in hot)."""
        pending = [{
            "skill": "cvm", "operation": _PENDING_OP,
            "command": _PENDING_CMD,
            "iter": 1, "scores": {}, "timestamp": f"{_TODAY}T00:00:00",
        }]
        hot = {}
        # Warm entry 45 days ago → beyond 30-day revive window
        old_date = (date.today().replace(day=1) -
                    __import__('datetime').timedelta(days=45)).strftime("%Y-%m-%d")
        warm = {make_key(e()): e(count=3, last=old_date)}
        cold = {}
        h, w, _ = merge_batch(pending, hot, warm, cold)
        # Warm entry stays in warm (stale)
        self.assertIn(make_key(e()), w)
        # But hot gets a new entry (count=1)
        self.assertEqual(len(h), 1)


class TestSilenceEviction(unittest.TestCase):

    def test_hot_over_limit_evicts_oldest(self):
        """Hot over HOT_LIMIT: oldest last_hit entries demoted to warm."""
        hot = {}
        for i in range(HOT_LIMIT + 2):
            key = f"(cvm, Run, cmd{i:03d})"
            # Create entries with clearly ordered dates
            month = 6 if i < HOT_LIMIT else 5
            day = 1 + i
            last = f"2025-{month:02d}-{day:02d}"
            hot[key] = e(skill="cvm", op="Run", sig=f"cmd{i:03d}",
                          count=1, last=last)
        pending, warm, cold = [], {}, {}
        h, w, _ = merge_batch(pending, hot, warm, cold)
        self.assertEqual(len(h), HOT_LIMIT)
        self.assertEqual(len(w), 2)

    def test_warm_over_limit_evicts_oldest(self):
        """Warm over WARM_LIMIT: oldest last_hit entries archived to cold."""
        warm = {}
        for i in range(WARM_LIMIT + 2):
            key = f"(cvm, Run, cmd{i:03d})"
            month = 6 if i < WARM_LIMIT else 5
            day = 1 + i
            last = f"2025-{month:02d}-{day:02d}"
            warm[key] = e(skill="cvm", op="Run", sig=f"cmd{i:03d}",
                           count=1, last=last)
        pending, hot, cold = [], {}, {}
        _, w, c = merge_batch(pending, hot, warm, cold)
        self.assertEqual(len(w), WARM_LIMIT)
        self.assertEqual(len(c), 2)


class TestColdHardCap(unittest.TestCase):

    def test_cold_prunes_lowest_count(self):
        """Cold over COLD_LIMIT: lowest count entries are pruned."""
        cold = {}
        for i in range(COLD_LIMIT + 5):
            key = f"(cvm, Run, cmd{i:03d})"
            cold[key] = e(skill="cvm", op="Run", sig=f"cmd{i:03d}",
                           count=100 - i)  # cmd000: count=100, cmdXXX: count=lowest
        pending, hot, warm = [], {}, {}
        _, _, c = merge_batch(pending, hot, warm, cold)
        self.assertEqual(len(c), COLD_LIMIT)
        # Highest count entries (cmd000..cmdXXX sorted desc) should remain
        self.assertEqual(c["(cvm, Run, cmd000)"].count, 100)


class TestSelfVerify(unittest.TestCase):

    def test_v1_duplicate_keys(self):
        hot = {make_key(e()): e()}
        warm = {make_key(e()): e()}  # duplicate
        errors = self_verify(hot, warm, {})
        self.assertTrue(any("V1" in e for e in errors))

    def test_v2_hot_exceeds_limit(self):
        hot = {f"key{i}": e() for i in range(HOT_LIMIT + 1)}
        errors = self_verify(hot, {}, {})
        self.assertTrue(any("V2" in e for e in errors))

    def test_v3_key_in_two_layers(self):
        entry = e()
        hot = {make_key(entry): entry}
        warm = {make_key(entry): entry}
        errors = self_verify(hot, warm, {})
        self.assertTrue(any("V3" in e for e in errors))

    def test_v4_missing_required_field(self):
        hot = {make_key(e()): e()}
        hot[make_key(e())].count = None
        errors = self_verify(hot, {}, {})
        self.assertTrue(any("V4" in e for e in errors))

    def test_v5_invalid_last_hit_format(self):
        hot = {make_key(e()): e()}
        hot[make_key(e())].last_hit = "not-a-date"
        errors = self_verify(hot, {}, {})
        self.assertTrue(any("V5" in e for e in errors))

    def test_pass_legitimate_layers(self):
        hot = {make_key(e(skill="cvm")): e(skill="cvm")}
        warm = {make_key(e(skill="redis")): e(skill="redis")}
        cold = {make_key(e(skill="cdb")): e(skill="cdb")}
        errors = self_verify(hot, warm, cold)
        self.assertEqual(errors, [])


class TestMakeKey(unittest.TestCase):

    def test_key_is_skill_op_sig(self):
        entry = e(skill="cvm", op="Run", sig="tccli cvm Run")
        self.assertEqual(make_key(entry), ("cvm", "Run", "tccli cvm Run"))


class TestWritePending(unittest.TestCase):

    def test_write_and_load_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "pending.jsonl"
            entry = {
                "skill": "cvm", "operation": "Run",
                "command": "tccli cvm RunInstances",
                "iter": 1, "scores": {}, "timestamp": f"{_TODAY}T00:00:00",
            }
            write_pending_with_lock(p, entry)
            loaded = load_pending(p)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["skill"], "cvm")


if __name__ == "__main__":
    unittest.main(verbosity=2)
