#!/usr/bin/env python3
"""Unit tests for P0-B layered failure_pattern_extract.

Tests the three-layer hot/warm/cold storage upgrade:
  T1: substitution merge  — same (skill, command, error) key increments count + updates last_seen
  T2: warm revive       — key in warm + gap ≤ 30 days → moved back to hot
  T3: silence hot       — hot over 200 → oldest last_seen demoted to warm
  T4: silence warm     — warm over 500 → oldest last_seen archived to cold
  T5: cold cap         — cold over 2000 → lowest count pruned
  V1: self_verify detects duplicate keys across layers
  V2: self_verify detects capacity breach
  V3: self_verify detects key in two layers simultaneously
  V4: self_verify detects missing required fields
  V5: self_verify detects invalid last_seen format
  E1: emit_layer produces valid markdown
  E2: save_layer round-trip (write then parse back)
"""

import sys
import unittest
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
import failure_pattern_extract as fpe


_TODAY = date.today().strftime("%Y-%m-%d")


def fp(skill="cvm", command="Run", error="MissingParam", count=1, last_seen=None, severity="minor"):
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


class TestSubstitution(unittest.TestCase):

    def test_same_key_count_increment(self):
        new = [fp(skill="cvm", command="Run", error="Err", count=1)]
        hot = {("cvm", "Run", "Err"): fp(count=5, last_seen=_TODAY)}
        warm, cold = {}, {}
        h, w, c = fpe.merge_failure_batch(new, hot, warm, cold)
        self.assertEqual(h[("cvm", "Run", "Err")]["count"], 6)
        self.assertEqual(h[("cvm", "Run", "Err")]["last_seen"], _TODAY)

    def test_new_key_appended_to_hot(self):
        new = [fp(skill="cvm", command="Stop", error="Err2")]
        hot, warm, cold = {}, {}, {}
        h, _, _ = fpe.merge_failure_batch(new, hot, warm, cold)
        self.assertEqual(len(h), 1)


class TestWarmRevive(unittest.TestCase):

    def test_revive_within_30_days(self):
        new = [fp(skill="cvm", command="Run", error="Err")]
        hot = {}
        warm = {("cvm", "Run", "Err"): fp(count=3, last_seen=_TODAY)}
        cold = {}
        h, w, _ = fpe.merge_failure_batch(new, hot, warm, cold)
        self.assertIn(("cvm", "Run", "Err"), h)
        self.assertNotIn(("cvm", "Run", "Err"), w)
        self.assertEqual(h[("cvm", "Run", "Err")]["count"], 4)

    def test_no_revive_beyond_30_days(self):
        old_date = (date.today() - timedelta(days=45)).strftime("%Y-%m-%d")
        new = [fp(skill="cvm", command="Run", error="Err")]
        hot = {}
        warm = {("cvm", "Run", "Err"): fp(count=3, last_seen=old_date)}
        cold = {}
        h, w, _ = fpe.merge_failure_batch(new, hot, warm, cold)
        # Stays in warm, hot gets new entry
        self.assertIn(("cvm", "Run", "Err"), w)
        self.assertEqual(len(h), 1)


class TestSilenceEviction(unittest.TestCase):

    def test_hot_over_limit_evicts_oldest(self):
        hot = {}
        for i in range(fpe.HOT_LIMIT + 2):
            key = ("cvm", f"cmd{i:03d}", f"Err{i}")
            # Alternate between recent and old
            last = _TODAY if i < fpe.HOT_LIMIT else (date.today() - timedelta(days=60)).strftime("%Y-%m-%d")
            hot[key] = fp(skill="cvm", command=f"cmd{i:03d}", error=f"Err{i}", count=1, last_seen=last)
        new, warm, cold = [], {}, {}
        h, w, _ = fpe.merge_failure_batch(new, hot, warm, cold)
        self.assertEqual(len(h), fpe.HOT_LIMIT)
        self.assertEqual(len(w), 2)

    def test_warm_over_limit_evicts_oldest(self):
        warm = {}
        for i in range(fpe.WARM_LIMIT + 2):
            key = ("cvm", f"cmd{i:03d}", f"Err{i}")
            last = _TODAY if i < fpe.WARM_LIMIT else (date.today() - timedelta(days=120)).strftime("%Y-%m-%d")
            warm[key] = fp(skill="cvm", command=f"cmd{i:03d}", error=f"Err{i}", count=1, last_seen=last)
        new, hot, cold = [], {}, {}
        _, w, c = fpe.merge_failure_batch(new, hot, warm, cold)
        self.assertEqual(len(w), fpe.WARM_LIMIT)
        self.assertEqual(len(c), 2)


class TestColdCap(unittest.TestCase):

    def test_cold_prunes_lowest_count(self):
        cold = {}
        for i in range(fpe.COLD_LIMIT + 5):
            key = ("cvm", f"cmd{i:03d}", f"Err{i}")
            cold[key] = fp(skill="cvm", command=f"cmd{i:03d}", error=f"Err{i}",
                             count=100 - i)  # cmd000: count=100, highest
        new, hot, warm = [], {}, {}
        _, _, c = fpe.merge_failure_batch(new, hot, warm, cold)
        self.assertEqual(len(c), fpe.COLD_LIMIT)
        self.assertEqual(c[("cvm", "cmd000", "Err0")]["count"], 100)


class TestSelfVerify(unittest.TestCase):

    def test_v1_duplicate_keys(self):
        key = ("cvm", "Run", "Err")
        hot = {key: fp()}
        warm = {key: fp()}
        errors = fpe.self_verify_failure(hot, warm, {})
        self.assertTrue(any("V1" in e for e in errors))

    def test_v2_hot_exceeds_limit(self):
        hot = {f"k{i}": fp() for i in range(fpe.HOT_LIMIT + 1)}
        errors = fpe.self_verify_failure(hot, {}, {})
        self.assertTrue(any("V2" in e for e in errors))
        self.assertTrue(any("hot" in e for e in errors))

    def test_v2_warm_exceeds_limit(self):
        warm = {f"k{i}": fp() for i in range(fpe.WARM_LIMIT + 1)}
        errors = fpe.self_verify_failure({}, warm, {})
        self.assertTrue(any("V2" in e for e in errors))
        self.assertTrue(any("warm" in e for e in errors))

    def test_v2_cold_exceeds_limit(self):
        cold = {f"k{i}": fp() for i in range(fpe.COLD_LIMIT + 1)}
        errors = fpe.self_verify_failure({}, {}, cold)
        self.assertTrue(any("V2" in e for e in errors))
        self.assertTrue(any("cold" in e for e in errors))

    def test_v3_key_in_two_layers(self):
        key = ("cvm", "Run", "Err")
        entry = fp()
        hot = {key: entry}
        warm = {key: entry}
        errors = fpe.self_verify_failure(hot, warm, {})
        self.assertTrue(any("V3" in e for e in errors))

    def test_v4_missing_required_field(self):
        hot = {("cvm", "Run", "Err"): fp()}
        hot[("cvm", "Run", "Err")]["count"] = None
        errors = fpe.self_verify_failure(hot, {}, {})
        self.assertTrue(any("V4" in e for e in errors))

    def test_v5_invalid_last_seen(self):
        hot = {("cvm", "Run", "Err"): fp()}
        hot[("cvm", "Run", "Err")]["last_seen"] = "not-a-date"
        errors = fpe.self_verify_failure(hot, {}, {})
        self.assertTrue(any("V5" in e for e in errors))

    def test_pass_legitimate_layers(self):
        hot = {("cvm", "Run", "Err"): fp()}
        warm = {("redis", "Run", "Err"): fp()}
        cold = {("cdb", "Run", "Err"): fp()}
        errors = fpe.self_verify_failure(hot, warm, cold)
        self.assertEqual(errors, [])


class TestEmitLayer(unittest.TestCase):

    def test_emit_layer_empty(self):
        lines = fpe.emit_layer({}, "Hot Layer")
        joined = "\n".join(lines)
        self.assertIn("Hot Layer", joined)
        self.assertIn("Total hits", joined)

    def test_emit_layer_produces_valid_markdown(self):
        patterns = {
            ("cvm", "Run", "Err"): fp(skill="cvm", command="Run", error="Err", count=3),
        }
        lines = fpe.emit_layer(patterns, "Hot Layer")
        joined = "\n".join(lines)
        self.assertTrue(joined.startswith("# Failure Patterns"))
        self.assertIn("Skill", joined)
        self.assertIn("`cvm`", joined)
        self.assertIn("Err", joined)
        self.assertIn("Hot Layer", joined)

    def test_save_and_parse_roundtrip(self):
        import tempfile
        patterns = {
            ("cvm", "Run", "Err"): fp(skill="cvm", command="Run", error="Err", count=3, last_seen=_TODAY),
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "failure-patterns.md"
            fpe.save_layer(p, patterns, "Hot Layer")
            loaded = fpe.parse_existing(p)
            self.assertEqual(len(loaded), 1)
            key = list(loaded.keys())[0]
            self.assertEqual(key[0], "cvm")
            self.assertEqual(loaded[key]["count"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
