#!/usr/bin/env python3
"""Tests for reflexion_retrieve.py — TDD approach.

Run: python3 -m unittest reflexion_retrieve_test -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reflexion_retrieve import load_failure_patterns, format_for_injection, _mask_credentials


class TestReflexionRetrieve(unittest.TestCase):
    """Test cases for reflexion memory retrieval."""

    def _create_fixture_file(self, temp_dir: Path, content: str) -> Path:
        """Create a temporary fixture file with the given content."""
        fixture_path = temp_dir / "failure-patterns.md"
        fixture_path.write_text(content, encoding="utf-8")
        return fixture_path

    def _get_fixture_content(self) -> str:
        """Return base fixture content with proper table format."""
        return """# Failure Patterns — Reflexion Memory

## 1. CLI Parameter Errors

| Skill | Command | Error Pattern | Fix | Count | Reusable | First Seen |
|-------|---------|---------------|-----|-------|----------|------------|
| `qcloud-cvm-ops` | `TerminateInstances` | MissingParameter | Use JSON array | 5 | true | 2024-01 |
| `qcloud-redis-ops` | `DestroyInstances` | MissingParameter | Use InstanceIds | 3 | true | 2024-01 |
| `qcloud-cdb-ops` | `IsolateDBInstance` | InvalidParameter | Check format | 2 | true | 2024-02 |

## 2. Skill Generation Issues

| Skill | Command | Error Pattern | Fix | Count | Reusable | First Seen |
|-------|---------|---------------|-----|-------|----------|------------|
| `qcloud-cos-ops` | `DeleteBucket` | InvalidParameterValue | Lowercase only | 4 | true | 2024-01 |
"""

    def test_exact_skill_ranking(self) -> None:
        """Test (a): exact-skill ranking — target skill pattern should be first."""
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._create_fixture_file(Path(tmp), self._get_fixture_content())

            # Query for qcloud-cvm-ops patterns
            result = load_failure_patterns("qcloud-cvm-ops", path=fixture, top_n=3)

            # Should return the CVM pattern first
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["skill"], "qcloud-cvm-ops")
            self.assertEqual(result[0]["command"], "TerminateInstances")
            self.assertEqual(result[0]["count"], 5)

    def test_command_substring_fallback(self) -> None:
        """Test (b): command-substring fallback — match when command appears in error."""
        content = """# Failure Patterns — Reflexion Memory

## 1. CLI Parameter Errors

| Skill | Command | Error Pattern | Fix | Count | Reusable | First Seen |
|-------|---------|---------------|-----|-------|----------|------------|
| `qcloud-cvm-ops` | `DescribeInstances` | Zone format error in DescribeInstances call | Use ap-guangzhou | 3 | true | 2024-01 |
| `qcloud-redis-ops` | `DestroyInstances` | MissingParameter | Use InstanceIds | 2 | true | 2024-01 |
"""
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._create_fixture_file(Path(tmp), content)

            # Query with command="DescribeInstances" — should match row where error contains it
            result = load_failure_patterns("qcloud-cvm-ops", command="DescribeInstances", path=fixture, top_n=3)

            # Should return the pattern (score 2 because command matches in error)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["skill"], "qcloud-cvm-ops")
            self.assertIn("DescribeInstances", result[0]["error"])

    def test_top_n_truncation(self) -> None:
        """Test (c): top_n truncation — only return top_n results."""
        content = """# Failure Patterns — Reflexion Memory

## 1. CLI Parameter Errors

| Skill | Command | Error Pattern | Fix | Count | Reusable | First Seen |
|-------|---------|---------------|-----|-------|----------|------------|
| `qcloud-cvm-ops` | `RunInstances` | InvalidParameter | Fix 1 | 10 | true | 2024-01 |
| `qcloud-cvm-ops` | `TerminateInstances` | MissingParameter | Fix 2 | 9 | true | 2024-01 |
| `qcloud-cvm-ops` | `DescribeInstances` | InvalidParameterValue | Fix 3 | 8 | true | 2024-01 |
| `qcloud-cvm-ops` | `StartInstances` | LimitExceeded | Fix 4 | 7 | true | 2024-01 |
| `qcloud-cvm-ops` | `StopInstances` | ResourceNotFound | Fix 5 | 6 | true | 2024-01 |
"""
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._create_fixture_file(Path(tmp), content)

            # Query with top_n=3 — should return only 3
            result = load_failure_patterns("qcloud-cvm-ops", path=fixture, top_n=3)

            self.assertEqual(len(result), 3)
            # Should be sorted by count desc, so highest counts first
            self.assertEqual(result[0]["count"], 10)
            self.assertEqual(result[1]["count"], 9)
            self.assertEqual(result[2]["count"], 8)

    def test_credential_masking(self) -> None:
        """Test (d): credential masking — secrets should be replaced with <masked>."""
        content = """# Failure Patterns — Reflexion Memory

## 1. CLI Parameter Errors

| Skill | Command | Error Pattern | Fix | Count | Reusable | First Seen |
|-------|---------|---------------|-----|-------|----------|------------|
| `qcloud-cvm-ops` | `AuthFailure` | SecretKey=FakeValue123456789012345 | Use env vars | 5 | true | 2024-01 |
"""
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._create_fixture_file(Path(tmp), content)

            result = load_failure_patterns("qcloud-cvm-ops", path=fixture, top_n=3)
            self.assertEqual(len(result), 1)

            # Format for injection should mask credentials
            formatted = format_for_injection(result)

            self.assertIn("<masked>", formatted)
            self.assertNotIn("FakeValue123456789012345", formatted)

    def test_empty_result(self) -> None:
        """Test (e): empty — no matching skill should return [] and format returns ""."""
        content = """# Failure Patterns — Reflexion Memory

## 1. CLI Parameter Errors

| Skill | Command | Error Pattern | Fix | Count | Reusable | First Seen |
|-------|---------|---------------|-----|-------|----------|------------|
| `qcloud-cvm-ops` | `TerminateInstances` | MissingParameter | Fix | 5 | true | 2024-01 |
"""
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._create_fixture_file(Path(tmp), content)

            # Query for non-existent skill
            result = load_failure_patterns("qcloud-nonexistent-ops", path=fixture, top_n=3)

            self.assertEqual(result, [])

            # Format should return empty string, not None
            formatted = format_for_injection(result)
            self.assertEqual(formatted, "")

    def test_mask_credentials_function(self) -> None:
        """Test _mask_credentials directly with various secret patterns."""
        # Test SecretKey pattern
        text1 = "Error: SecretKey=REPLACEME_REPLACE_REPLACE_REPLACE"
        self.assertIn("<masked>", _mask_credentials(text1))
        self.assertNotIn("REPLACEME", _mask_credentials(text1))

        text2 = "secret_key=FAKE_KEY_REPLACE_REPLACE_REPLACE_REPLACE"
        self.assertIn("<masked>", _mask_credentials(text2))

        text3 = "password=SuperSecret123!"
        self.assertIn("<masked>", _mask_credentials(text3))


if __name__ == "__main__":
    unittest.main()
