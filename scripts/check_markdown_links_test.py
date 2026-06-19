#!/usr/bin/env python3
"""Unit tests for scripts/check_markdown_links.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import check_markdown_links as cml  # noqa: E402


def write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class IterMarkdownFilesTests(unittest.TestCase):
    def test_focuses_on_entry_docs_and_top_level_docs_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = write(root / "AGENTS.md")
            readme = write(root / "README.md")
            readme_cn = write(root / "README_CN.md")
            top_doc = write(root / "docs" / "gcl-spec.md")
            write(root / "docs" / "superpowers" / "plans" / "historical.md")
            write(root / "qcloud-cvm-ops" / "SKILL.md", "[bad](missing.md)")
            write(root / "qcloud-cvm-ops" / "references" / "cli-usage.md", "[bad](missing.md)")

            files = cml.iter_markdown_files(root)
            self.assertEqual(files, [agents, readme, readme_cn, top_doc])


class PathDetectionTests(unittest.TestCase):
    def test_ignores_command_like_backticks(self) -> None:
        self.assertFalse(cml.looks_like_repo_path("python3 scripts/foo.py --flag value"))
        self.assertFalse(cml.looks_like_repo_path("{{output.trace}}"))
        self.assertFalse(cml.looks_like_repo_path("*.md"))

    def test_accepts_explicit_repo_paths(self) -> None:
        self.assertTrue(cml.looks_like_repo_path("docs/gcl-spec.md"))
        self.assertTrue(cml.looks_like_repo_path("scripts/check_markdown_links.py"))
        self.assertTrue(cml.looks_like_repo_path("qcloud-cvm-ops/SKILL.md"))


class CheckFileTests(unittest.TestCase):
    def test_valid_local_links_and_repo_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "docs" / "gcl-spec.md")
            source = write(
                root / "AGENTS.md",
                "See [GCL](docs/gcl-spec.md#section) and `docs/gcl-spec.md`.\n",
            )
            self.assertEqual(cml.check_file(root, source), [])

    def test_missing_markdown_link_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write(root / "AGENTS.md", "See [Missing](docs/missing.md).\n")
            findings = cml.check_file(root, source)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].target, "docs/missing.md")
            self.assertEqual(findings[0].reason, "missing markdown link target")

    def test_missing_backtick_repo_path_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write(root / "README.md", "Run `scripts/missing.py`.\n")
            findings = cml.check_file(root, source)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].target, "scripts/missing.py")
            self.assertEqual(findings[0].reason, "missing backtick path target")

    def test_historical_skill_docs_are_not_scanned_by_main_file_iterator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "AGENTS.md", "ok\n")
            write(root / "README.md", "ok\n")
            write(root / "README_CN.md", "[English](README.md)\n")
            write(root / "qcloud-cvm-ops" / "SKILL.md", "[legacy missing](references/old.md)\n")
            findings = []
            for path in cml.iter_markdown_files(root):
                findings.extend(cml.check_file(root, path))
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
