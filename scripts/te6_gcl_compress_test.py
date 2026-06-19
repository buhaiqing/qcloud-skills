#!/usr/bin/env python3
"""Unit tests for scripts/te6_gcl_compress.py."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import te6_gcl_compress as te6  # noqa: E402


class ParseRubricRulesTests(unittest.TestCase):
    def test_parse_compact_rule_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rubric = Path(tmp) / "rubric.md"
            rubric.write_text(
                "# Rubric\n\n"
                "## 4. Operation gates\n\n"
                "| # | Operation(s) | Gate |\n"
                "|---:|---|---|\n"
                "| 1 | DeleteInstance | **Require explicit confirmation** |\n"
                "| 2 | DescribeInstances | **Read-only only** |\n\n"
                "## 5. Anti-patterns\n",
                encoding="utf-8",
            )
            self.assertEqual(
                te6.parse_rubric_rules(rubric),
                [
                    ("1", "DeleteInstance", "Require explicit confirmation"),
                    ("2", "DescribeInstances", "Read-only only"),
                ],
            )

    def test_parse_rule_headings_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rubric = Path(tmp) / "rubric.md"
            rubric.write_text(
                "# Rubric\n\n"
                "## 4. Operation gates\n\n"
                "### Rule 1: Backup before restore\n"
                "### Rule 2: Confirm destructive action\n\n"
                "## 5. Anti-patterns\n",
                encoding="utf-8",
            )
            self.assertEqual(
                te6.parse_rubric_rules(rubric),
                [
                    ("1", "Backup before restore", "see rubric §4"),
                    ("2", "Confirm destructive action", "see rubric §4"),
                ],
            )


class PromptCompressionTests(unittest.TestCase):
    def test_split_sections(self) -> None:
        sections = te6.split_sections("intro\n## 1. One\na\n## 2. Two\nb\n")
        self.assertEqual(sections[1], "## 1. One\na")
        self.assertEqual(sections[2], "## 2. Two\nb")

    def test_compress_prompt_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_dir = root / "qcloud-test-ops" / "references"
            prompt_dir.mkdir(parents=True)
            prompt = prompt_dir / "prompt-templates.md"
            original = "\n\n".join(
                [
                    "# Test Prompts",
                    "## 1. Generator prompt template\nold generator",
                    "## 2. Critic prompt template\nold critic",
                    "## 3. Orchestrator prompt template\nold orchestrator",
                    "## 4. Per-operation variants\nold duplicated gates",
                    "## 5. Anti-patterns\n### Test-specific anti-patterns\n- ❌ Product-only bad path",
                    "## 6. Changelog\n| Version | Date | Change |\n|---|---|---|\n| 1.2.0 | 2026-06-18 | old |",
                    "## 7. See also\n- links",
                ]
            ) + "\n"
            prompt.write_text(original, encoding="utf-8")

            with patch.object(te6, "ROOT", root), patch.dict(
                te6.GCL_META,
                {"qcloud-test-ops": {"max_iter": 2, "cli": "test", "title": "Test"}},
            ):
                old_lines, new_lines = te6.compress_prompt("qcloud-test-ops", dry_run=True)

            self.assertGreater(old_lines, 0)
            self.assertGreater(new_lines, 0)
            self.assertEqual(prompt.read_text(encoding="utf-8"), original)

    def test_compress_quality_gate_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "qcloud-test-ops"
            references = skill_dir / "references"
            references.mkdir(parents=True)
            skill = skill_dir / "SKILL.md"
            rubric = references / "rubric.md"
            original = (
                "# Skill\n\n"
                "## Quality Gate (GCL)\n\n"
                "### Test-specific safety rules\n\n"
                "long duplicated safety gate text\n\n"
                "### Other section\n"
            )
            skill.write_text(original, encoding="utf-8")
            rubric.write_text(
                "# Rubric\n\n"
                "## 4. Operation gates\n\n"
                "| # | Operation(s) | Gate |\n"
                "|---:|---|---|\n"
                "| 1 | DeleteThing | **Confirm delete** |\n",
                encoding="utf-8",
            )

            with patch.object(te6, "ROOT", root), patch.dict(
                te6.GCL_META,
                {"qcloud-test-ops": {"max_iter": 2, "cli": "test", "title": "Test"}},
            ):
                old_lines, new_lines = te6.compress_quality_gate("qcloud-test-ops", dry_run=True)

            self.assertGreater(old_lines, 0)
            self.assertGreater(new_lines, 0)
            self.assertEqual(skill.read_text(encoding="utf-8"), original)


class MainTests(unittest.TestCase):
    def test_main_dry_run_custom_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "qcloud-missing-ops").mkdir()
            with patch.object(te6, "ROOT", root):
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    self.assertEqual(te6.main(["--dry-run", "--skill", "qcloud-missing-ops"]), 0)
            self.assertIn("Total saved:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
