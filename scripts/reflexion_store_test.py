#!/usr/bin/env python3
"""Unit tests for reflexion_store.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reflexion_store import (
    MAX_LINES,
    normalize_reflexion_key,
    parse_existing_safe,
    store_failure_pattern,
)


class TestReflexionStore(unittest.TestCase):
    """Test cases for reflexion store operations."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patterns_file = Path(self.temp_dir.name) / "failure-patterns.md"

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_store_new_pattern(self) -> None:
        """Test storing a new pattern creates an entry."""
        result = store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="TerminateInstances",
            error="MissingParameter",
            resolution="Use JSON array format",
            path=self.patterns_file,
        )

        self.assertTrue(result)
        self.assertTrue(self.patterns_file.exists())

        patterns = parse_existing_safe(self.patterns_file)
        key = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        self.assertIn(key, patterns)
        self.assertEqual(patterns[key]["count"], 1)
        self.assertEqual(patterns[key]["fix"], "Use JSON array format")

    def test_dedup_existing_pattern(self) -> None:
        """Test that duplicate patterns are deduplicated and count incremented."""
        # Store first pattern
        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="TerminateInstances",
            error="MissingParameter",
            resolution="Use JSON array format",
            path=self.patterns_file,
        )

        # Store same pattern again
        result = store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="TerminateInstances",
            error="MissingParameter",
            resolution="Different resolution",
            path=self.patterns_file,
        )

        self.assertTrue(result)

        patterns = parse_existing_safe(self.patterns_file)
        key = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        self.assertIn(key, patterns)
        # Count should be incremented
        self.assertEqual(patterns[key]["count"], 2)
        # Fix should NOT change on upsert (preserves original)
        self.assertEqual(patterns[key]["fix"], "Use JSON array format")

    def test_different_patterns_not_deduped(self) -> None:
        """Test that different patterns are stored separately."""
        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="TerminateInstances",
            error="MissingParameter",
            resolution="Fix 1",
            path=self.patterns_file,
        )

        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="RunInstances",
            error="InvalidParameter",
            resolution="Fix 2",
            path=self.patterns_file,
        )

        patterns = parse_existing_safe(self.patterns_file)
        self.assertEqual(len(patterns), 2)

        key1 = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        key2 = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "RunInstances", "InvalidParameter")
        self.assertIn(key1, patterns)
        self.assertIn(key2, patterns)

    def test_line_limit_enforcement(self) -> None:
        """Test that patterns are pruned when exceeding line limit."""
        # Create many patterns to exceed the limit
        for i in range(50):
            store_failure_pattern(
                skill=f"qcloud-skill-{i}-ops",
                command=f"Command{i}",
                error=f"Error{i}",
                resolution=f"Fix{i}",
                path=self.patterns_file,
            )

        # Verify file exists and is under limit
        self.assertTrue(self.patterns_file.exists())
        lines = self.patterns_file.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(lines), MAX_LINES)

    def test_prune_keeps_high_count_patterns(self) -> None:
        """Test that pruning keeps patterns with higher hit counts."""
        # Store pattern with high count (via multiple upserts)
        for _ in range(10):
            store_failure_pattern(
                skill="qcloud-popular-ops",
                command="PopularCommand",
                error="PopularError",
                resolution="PopularFix",
                path=self.patterns_file,
            )

        # Store many low-count patterns
        for i in range(60):
            store_failure_pattern(
                skill=f"qcloud-rare-{i}-ops",
                command=f"RareCommand{i}",
                error=f"RareError{i}",
                resolution=f"RareFix{i}",
                path=self.patterns_file,
            )

        patterns = parse_existing_safe(self.patterns_file)

        # High-count pattern should still exist
        high_count_key = normalize_reflexion_key("runtime", "qcloud-popular-ops", "PopularCommand", "PopularError")
        self.assertIn(high_count_key, patterns)
        self.assertEqual(patterns[high_count_key]["count"], 10)

    def test_category_defaults_to_runtime(self) -> None:
        """Test that new patterns default to 'runtime' category."""
        store_failure_pattern(
            skill="qcloud-test-ops",
            command="TestCommand",
            error="TestError",
            resolution="TestFix",
            path=self.patterns_file,
        )

        patterns = parse_existing_safe(self.patterns_file)
        key = normalize_reflexion_key("runtime", "qcloud-test-ops", "TestCommand", "TestError")
        self.assertEqual(patterns[key]["category"], "runtime")

    def test_update_timestamp_on_upsert(self) -> None:
        """Test that upsert updates the timestamp."""
        import time

        # Store first pattern
        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="Test",
            error="Error",
            resolution="Fix",
            path=self.patterns_file,
        )

        patterns1 = parse_existing_safe(self.patterns_file)
        key = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "Test", "Error")
        first_seen = patterns1[key].get("first_seen")

        # Wait a moment and upsert
        time.sleep(0.01)
        store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="Test",
            error="Error",
            resolution="NewFix",
            path=self.patterns_file,
        )

        patterns2 = parse_existing_safe(self.patterns_file)
        # first_seen should remain unchanged (it's the creation time)
        self.assertEqual(patterns2[key]["first_seen"], first_seen)
        # But count should be updated
        self.assertEqual(patterns2[key]["count"], 2)

    def test_empty_skill_rejected(self) -> None:
        """Test that empty skill is rejected."""
        result = store_failure_pattern(
            skill="",
            command="Test",
            error="Error",
            resolution="Fix",
            path=self.patterns_file,
        )
        self.assertFalse(result)

    def test_empty_error_rejected(self) -> None:
        """Test that empty error is rejected."""
        result = store_failure_pattern(
            skill="qcloud-test-ops",
            command="Test",
            error="",
            resolution="Fix",
            path=self.patterns_file,
        )
        self.assertFalse(result)

    def test_file_created_if_not_exists(self) -> None:
        """Test that file is created if it doesn't exist."""
        non_existent = Path(self.temp_dir.name) / "non_existent" / "failure-patterns.md"

        result = store_failure_pattern(
            skill="qcloud-test-ops",
            command="Test",
            error="Error",
            resolution="Fix",
            path=non_existent,
        )

        self.assertTrue(result)
        self.assertTrue(non_existent.exists())

    def test_normalize_reflexion_key_shape(self) -> None:
        """normalize_reflexion_key emits the 4-tuple (cat, skill, cmd_norm, err)."""
        key = normalize_reflexion_key("Runtime", "Qcloud-CVM-Ops", "TerminateInstances i-abc", "MissingParameter X")
        self.assertEqual(
            key,
            ("runtime", "qcloud-cvm-ops", "terminateinstances", "missingparameter x"),
        )

    def test_key_matches_copilot_sink_shape(self) -> None:
        """Same failure from copilot and GCL must produce an identical key string.

        Fixes L5: the two sinks must dedup instead of double-writing.
        """
        cat, skill, cmd, err = "runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
        gcl_key = normalize_reflexion_key(cat, skill, cmd, err)
        # copilot reflexion.py uses an identical normalize_reflexion_key impl
        copilot_key = normalize_reflexion_key(cat, skill, cmd, err)
        self.assertEqual(gcl_key, copilot_key)
        self.assertEqual(
            ":".join(gcl_key),
            "runtime:qcloud-cvm-ops:terminateinstances:missingparameter",
        )

    def test_dedup_across_category_separates(self) -> None:
        """Different categories yield different keys (no cross-category merge)."""
        k1 = normalize_reflexion_key("runtime", "qcloud-cvm-ops", "X", "Y")
        k2 = normalize_reflexion_key("cli_parameter", "qcloud-cvm-ops", "X", "Y")
        self.assertNotEqual(k1, k2)


class TestCount1Survival(unittest.TestCase):
    """Regression: count=1 patterns must survive their first write.

    Previously reflexion_auto_writer.write_trace() called prune_low_frequency(min_count=3)
    BEFORE enforce_line_cap, silently removing brand-new patterns before they were ever
    written. store_failure_pattern() correctly handles capacity via _prune_by_count
    (which only fires when patterns > ~150). The write_trace path now mirrors this.
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.patterns_file = self.temp_path / "failure-patterns.md"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_count1_pattern_survives_first_write(self) -> None:
        """A new pattern with count=1 must persist after its first store_failure_pattern call."""
        result = store_failure_pattern(
            skill="qcloud-cvm-ops",
            command="DescribeInstances",
            error="AuthFailure: SecretId not found",
            resolution="Verify TENCENTCLOUD_SECRET_ID is correct",
            path=self.patterns_file,
        )
        self.assertTrue(result)
        patterns = parse_existing_safe(self.patterns_file)
        self.assertEqual(len(patterns), 1, "count=1 pattern must survive first write")
        first_pattern = next(iter(patterns.values()))
        self.assertEqual(first_pattern["count"], 1)
        self.assertEqual(first_pattern["skill"], "qcloud-cvm-ops")

    def test_write_trace_preserves_count1(self) -> None:
        """write_trace must NOT strip count=1 patterns before writing."""
        import reflexion_auto_writer as raw
        trace = {
            "final": {
                "failure_pattern": {
                    "category": "runtime",
                    "skill": "qcloud-redis-ops",
                    "command": "DescribeInstances",
                    "error": "Resource not found",
                    "fix": "Check resource ID",
                    "count": 1,
                }
            }
        }
        ok = raw.write_trace(trace, patterns_path=self.patterns_file)
        self.assertTrue(ok)
        patterns = parse_existing_safe(self.patterns_file)
        self.assertEqual(len(patterns), 1, "count=1 pattern must survive write_trace")

    def test_write_trace_isolates_tmp_file(self) -> None:
        """patterns_path redirects output away from the production file."""
        import reflexion_auto_writer as raw
        trace = {
            "final": {
                "failure_pattern": {
                    "category": "runtime",
                    "skill": "qcloud-redis-ops",
                    "command": "DescribeInstances",
                    "error": "tmp isolation probe",
                    "fix": "redirect",
                    "count": 1,
                }
            }
        }
        self.assertTrue(raw.write_trace(trace, patterns_path=self.patterns_file))
        self.assertIn("tmp isolation probe", self.patterns_file.read_text(encoding="utf-8"))


class TestDemotionIntegration(unittest.TestCase):
    """P1-2: evicted patterns demote to warm/cold layers instead of being lost."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.hot = self.temp_path / "failure-patterns.md"
        self.warm = self.temp_path / "failure-patterns-warm.md"
        self.cold = self.temp_path / "failure-patterns-cold.md"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_evicted_patterns_demote_to_warm(self) -> None:
        """When hot exceeds limit, lowest-count patterns go to warm."""
        # Override the module-level paths so demotion finds our temp files
        import reflexion_store as rs
        orig_hot = rs._HOT_PATH
        orig_warm = rs._WARM_PATH
        orig_cold = rs._COLD_PATH
        rs._HOT_PATH = self.hot
        rs._WARM_PATH = self.warm
        rs._COLD_PATH = self.cold
        try:
            # Store many patterns to force eviction
            for i in range(160):
                store_failure_pattern(
                    skill="qcloud-popular-ops",
                    command=f"op{i}",
                    error=f"error{i}",
                    resolution=f"fix{i}",
                    path=self.hot,
                )
            # The lowest-count (count=1) patterns should have been demoted to warm
            hot_patterns = parse_existing_safe(self.hot)
            warm_patterns = parse_existing_safe(self.warm) if self.warm.exists() else {}
            self.assertLess(len(hot_patterns), 160, "hot should have been pruned")
            # Demoted patterns should be in warm
            self.assertGreater(len(warm_patterns), 0, "warm should have received demoted patterns")
        finally:
            rs._HOT_PATH = orig_hot
            rs._WARM_PATH = orig_warm
            rs._COLD_PATH = orig_cold




if __name__ == "__main__":
    unittest.main()
