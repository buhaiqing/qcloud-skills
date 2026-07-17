#!/usr/bin/env python3
"""Unit tests for reflexion_store.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


from reflexion_store import (
    store_failure_pattern,
    MAX_LINES,
    parse_existing_safe,
    normalize_reflexion_key,
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


if __name__ == "__main__":
    unittest.main()
