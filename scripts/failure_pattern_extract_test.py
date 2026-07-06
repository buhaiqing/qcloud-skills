#!/usr/bin/env python3
"""Unit tests for failure_pattern_extract.py — stdlib only."""

import json
import tempfile
import unittest
from pathlib import Path

# Import from the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent))
import failure_pattern_extract as fpe


class TestParseExisting(unittest.TestCase):
    """Tests for parse_existing() — markdown table parsing."""

    def _make_file(self, content: str) -> Path:
        p = Path(tempfile.mktemp(suffix=".md"))
        p.write_text(content, encoding="utf-8")
        return p

    def test_empty_file(self):
        p = self._make_file("")
        result = fpe.parse_existing(p)
        self.assertEqual(result, {})

    def test_no_section_headers(self):
        p = self._make_file("# Random doc\nSome text without tables.")
        result = fpe.parse_existing(p)
        self.assertEqual(result, {})

    def test_parses_single_pattern(self):
        content = (
            "## 1. CLI Parameter Errors\n\n"
            "| Skill | Command | Error Pattern | Fix | Count |\n"
            "|---|---|---|---|---|\n"
            "| `qcloud-cvm-ops` | `RunInstances` | `InvalidParameter` | Fix args | 3 |\n"
        )
        p = self._make_file(content)
        result = fpe.parse_existing(p)
        self.assertEqual(len(result), 1)
        key = ("qcloud-cvm-ops", "RunInstances", "InvalidParameter")
        self.assertIn(key, result)
        self.assertEqual(result[key]["category"], "cli_parameter")
        self.assertEqual(result[key]["count"], 3)

    def test_skips_non_category_sections(self):
        content = (
            "## Usage Guidelines\n\n"
            "Some guide text with | pipes | in it |\n"
        )
        p = self._make_file(content)
        result = fpe.parse_existing(p)
        self.assertEqual(result, {})

    def test_deduplicates_by_skill_command_error(self):
        content = (
            "## 1. CLI Parameter Errors\n\n"
            "| Skill | Command | Error Pattern | Fix | Count |\n"
            "|---|---|---|---|---|\n"
            "| `qcloud-redis-ops` | `DestroyInstances` | `MissingParameter` | Add InstanceIds | 5 |\n"
        )
        p = self._make_file(content)
        result = fpe.parse_existing(p)
        key = ("qcloud-redis-ops", "DestroyInstances", "MissingParameter")
        self.assertIn(key, result)
        self.assertEqual(result[key]["count"], 5)


class TestCollectTraces(unittest.TestCase):
    """Tests for collect_traces() — glob + time filter."""

    def test_glob_no_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit = root / "audit-results"
            audit.mkdir()
            (audit / "gcl-trace-2026-01-01-000000.json").write_text("{}", encoding="utf-8")
            (audit / "gcl-trace-2026-01-02-000000.json").write_text("{}", encoding="utf-8")
            result = fpe.collect_traces(root, None, None)
            self.assertEqual(len(result), 2)

    def test_since_hours_filters_old_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit = root / "audit-results"
            audit.mkdir()
            old = audit / "gcl-trace-2020-01-01-000000.json"
            old.write_text("{}", encoding="utf-8")
            # Manually age the file
            import os
            old_time = 1577836800  # 2020-01-01 UTC
            os.utime(old, (old_time, old_time))

            new = audit / "gcl-trace-2099-01-01-000000.json"
            new.write_text("{}", encoding="utf-8")

            result = fpe.collect_traces(root, None, 24)
            self.assertEqual(len(result), 1)
            self.assertIn("2099", result[0].name)


class TestExtractFailurePatterns(unittest.TestCase):
    """Tests for extract_failure_patterns() — JSON parsing."""

    def _make_trace(self, data: dict) -> Path:
        p = Path(tempfile.mktemp(suffix=".json"))
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_top_level_failure_pattern(self):
        trace = {
            "skill": "qcloud-cvm-ops",
            "final": {"status": "PASS"},
            "failure_pattern": {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Add InstanceIds",
                "reusable": True,
            },
        }
        p = self._make_trace(trace)
        result = fpe.extract_failure_patterns([p])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["command"], "TerminateInstances")

    def test_iteration_failure_pattern(self):
        trace = {
            "skill": "qcloud-redis-ops",
            "final": {"status": "MAX_ITER"},
            "iterations": [
                {
                    "critic": {"scores": {"correctness": 0.5}},
                    "failure_pattern": {
                        "category": "runtime",
                        "skill": "qcloud-redis-ops",
                        "command": "ClearInstance",
                        "error": "Permission denied",
                        "fix": "Check CAM policy",
                        "reusable": True,
                    },
                }
            ],
        }
        p = self._make_trace(trace)
        result = fpe.extract_failure_patterns([p])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["category"], "runtime")
        self.assertIn("#iter-1", result[0]["_source"])

    def test_skips_invalid_json(self):
        p = Path(tempfile.mktemp(suffix=".json"))
        p.write_text("not valid json{", encoding="utf-8")
        result = fpe.extract_failure_patterns([p])
        self.assertEqual(result, [])

    def test_skips_missing_failure_pattern(self):
        trace = {"skill": "qcloud-cdb-ops", "final": {"status": "PASS"}}
        p = self._make_trace(trace)
        result = fpe.extract_failure_patterns([p])
        self.assertEqual(result, [])


class TestMerge(unittest.TestCase):
    """Tests for merge() — dedup and increment."""

    def test_new_pattern_appended(self):
        existing = {}
        new = [
            {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "RunInstances",
                "error": "InvalidParameter",
                "fix": "Check args",
                "reusable": True,
            }
        ]
        result = fpe.merge(existing, new)
        key = ("qcloud-cvm-ops", "RunInstances", "InvalidParameter")
        self.assertIn(key, result)
        self.assertEqual(result[key]["count"], 1)

    def test_existing_pattern_incremented(self):
        existing = {
            ("qcloud-cvm-ops", "TerminateInstances", "MissingParameter"): {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Fix args",
                "count": 2,
                "reusable": True,
            }
        }
        new = [
            {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Fix args",
                "reusable": True,
            }
        ]
        result = fpe.merge(existing, new)
        key = ("qcloud-cvm-ops", "TerminateInstances", "MissingParameter")
        self.assertEqual(result[key]["count"], 3)

    def test_skips_missing_skill(self):
        existing = {}
        new = [{"category": "runtime", "skill": "", "command": "", "error": "err"}]
        result = fpe.merge(existing, new)
        self.assertEqual(len(result), 0)


class TestPrune(unittest.TestCase):
    """Tests for prune_low_frequency()."""

    def test_prunes_below_threshold(self):
        patterns = {
            ("a", "b", "c"): {"count": 1},
            ("a", "b", "d"): {"count": 3},
            ("a", "b", "e"): {"count": 5},
        }
        fpe.prune_low_frequency(patterns, min_count=3)
        self.assertEqual(len(patterns), 2)
        self.assertNotIn(("a", "b", "c"), patterns)


class TestEnforceLineCap(unittest.TestCase):
    """Tests for enforce_line_cap()."""

    def test_produces_valid_markdown(self):
        patterns = {
            ("qcloud-cvm-ops", "RunInstances", "InvalidParameter"): {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "RunInstances",
                "error": "InvalidParameter",
                "fix": "Check args",
                "count": 2,
                "reusable": True,
            }
        }
        lines = fpe.enforce_line_cap(patterns)
        self.assertTrue(lines[0].startswith("# Failure Patterns"))
        self.assertIn("## 1. CLI Parameter Errors", lines)
        self.assertIn("## Usage Guidelines", lines)

    def test_skips_empty_sections(self):
        patterns = {
            ("qcloud-cvm-ops", "RunInstances", "InvalidParameter"): {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "RunInstances",
                "error": "InvalidParameter",
                "fix": "Check args",
                "count": 2,
                "reusable": True,
            }
        }
        lines = fpe.enforce_line_cap(patterns)
        # Runtime section should not appear if empty
        section_titles = [ln for ln in lines if ln.startswith("## ")]
        self.assertNotIn("## 4. Runtime Execution Patterns", section_titles)


if __name__ == "__main__":
    unittest.main(verbosity=2)
