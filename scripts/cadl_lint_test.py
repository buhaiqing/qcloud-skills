#!/usr/bin/env python3
"""Unit tests for scripts/cadl_lint.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import cadl_lint as cl  # noqa: E402


class CanonicalHookConstantTests(unittest.TestCase):
    def test_constant_is_non_blank_byte_sequence(self) -> None:
        self.assertTrue(cl.CANONICAL_HOOK.startswith(">"))
        self.assertTrue(cl.CANONICAL_HOOK.endswith("可复用资产。"))
        self.assertNotIn("\n", cl.CANONICAL_HOOK)

    def test_hook_contains_full_width_brackets(self) -> None:
        # Full-width brackets are part of the contract.
        self.assertIn("「", cl.CANONICAL_HOOK)
        self.assertIn("」", cl.CANONICAL_HOOK)


class LastNonblankLineTests(unittest.TestCase):
    def test_returns_terminator_when_file_ends_with_hook(self) -> None:
        text = "body\n\n> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。\n"
        self.assertEqual(cl._last_nonblank_line(text), cl.CANONICAL_HOOK)

    def test_returns_real_last_when_blank_lines_follow(self) -> None:
        text = "body\n\n> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。\n\n\n\n"
        self.assertEqual(cl._last_nonblank_line(text), cl.CANONICAL_HOOK)

    def test_returns_empty_for_all_blank(self) -> None:
        self.assertEqual(cl._last_nonblank_line("\n\n\n"), "")

    def test_returns_empty_for_empty_string(self) -> None:
        self.assertEqual(cl._last_nonblank_line(""), "")


class LintOneTests(unittest.TestCase):
    def test_ok_when_last_line_is_canonical_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "qcloud-cvm-ops"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "title: cvm\nbody\n\n"
                + cl.CANONICAL_HOOK + "\n",
                encoding="utf-8",
            )
            skill_md = skill / "SKILL.md"
            name, ok, msg = cl.lint_one(skill_md)
            self.assertEqual(name, "qcloud-cvm-ops")
            self.assertTrue(ok, msg)
            self.assertEqual(msg, "ok")

    def test_missing_hook_reports_last_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "qcloud-cvm-ops"
            skill.mkdir()
            (skill / "SKILL.md").write_text("body\nLast line is wrong.\n", encoding="utf-8")
            name, ok, msg = cl.lint_one(skill / "SKILL.md")
            self.assertEqual(name, "qcloud-cvm-ops")
            self.assertFalse(ok)
            self.assertIn("Last line is wrong.", msg)

    def test_missing_file_returns_not_found(self) -> None:
        ghost = Path("/tmp/definitely-missing-skill.md")
        if ghost.exists():  # pragma: no cover — paranoid cleanup
            ghost.unlink()
        name, ok, msg = cl.lint_one(ghost)
        self.assertFalse(ok)
        self.assertIn("not found", msg)


class FixOneTests(unittest.TestCase):
    def test_idempotent_when_already_compliant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "qcloud-cvm-ops"
            skill.mkdir()
            target = skill / "SKILL.md"
            target.write_text("body\n" + cl.CANONICAL_HOOK + "\n", encoding="utf-8")
            before = target.read_text(encoding="utf-8")
            self.assertFalse(cl.fix_one(target))
            self.assertEqual(target.read_text(encoding="utf-8"), before)

    def test_appends_to_file_without_trailing_newline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "qcloud-cvm-ops"
            skill.mkdir()
            target = skill / "SKILL.md"
            target.write_text("body without newline", encoding="utf-8")
            self.assertTrue(cl.fix_one(target))
            result = target.read_text(encoding="utf-8")
            self.assertTrue(result.endswith(cl.CANONICAL_HOOK + "\n"))
            self.assertIn("body without newline", result)

    def test_appends_to_file_with_trailing_newline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "qcloud-cvm-ops"
            skill.mkdir()
            target = skill / "SKILL.md"
            target.write_text("body\n", encoding="utf-8")
            self.assertTrue(cl.fix_one(target))
            result = target.read_text(encoding="utf-8")
            self.assertTrue(result.endswith(cl.CANONICAL_HOOK + "\n"))
            # Must not collapse the prior trailing newline.
            self.assertIn("\n\n", result)

    def test_double_fix_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "qcloud-cvm-ops"
            skill.mkdir()
            target = skill / "SKILL.md"
            target.write_text("body\n", encoding="utf-8")
            self.assertTrue(cl.fix_one(target))
            after_first = target.read_text(encoding="utf-8")
            self.assertFalse(cl.fix_one(target))
            after_second = target.read_text(encoding="utf-8")
            self.assertEqual(after_first, after_second)
            _, ok, msg = cl.lint_one(target)
            self.assertTrue(ok, msg)


class RunLintTests(unittest.TestCase):
    def test_mixed_directory_first_pass_then_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # mix of compliant, non-compliant, missing
            (root / "qcloud-ok-ops").mkdir()
            (root / "qcloud-ok-ops" / "SKILL.md").write_text(
                "x\n" + cl.CANONICAL_HOOK + "\n", encoding="utf-8"
            )
            (root / "qcloud-bad-ops").mkdir()
            (root / "qcloud-bad-ops" / "SKILL.md").write_text("missing hook\n", encoding="utf-8")
            (root / "qcloud-empty-ops").mkdir()
            (root / "qcloud-empty-ops" / "SKILL.md").write_text("\n\n", encoding="utf-8")

            paths = [p / "SKILL.md" for p in (root / "qcloud-ok-ops", root / "qcloud-bad-ops", root / "qcloud-empty-ops")]
            # Simulate by replacing ROOT for iter_skill_files — we just test run_lint directly.
            exit_code, report = cl.run_lint(paths, fix=False)
            self.assertEqual(exit_code, 1)
            self.assertEqual(sum(1 for r in report if r["ok"]), 1)  # only qcloud-ok-ops

            # Now fix and re-run.
            exit_code, report = cl.run_lint(paths, fix=True)
            self.assertEqual(exit_code, 0)
            self.assertEqual(sum(1 for r in report if r["ok"]), 3)
            self.assertTrue(all(r.get("fixed") for r in report if not r["ok"]))


if __name__ == "__main__":
    unittest.main()
