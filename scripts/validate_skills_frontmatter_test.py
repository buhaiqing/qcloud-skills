#!/usr/bin/env python3
"""Unit tests for scripts/validate_skills_frontmatter.py (component-engineering gates).

Covers: required-field presence (cli_support_evidence/environment), the
dual-path -> references/cli-usage.md cross-check, the --skip-missing-required
escape hatch, the meta-skill exemption, and the --git-diff version-bump gate
(L6: every gate must both fire and stay silent).
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import validate_skills_frontmatter as vf

TEMPLATE = """\
---
name: {name}
description: >-
  Test skill description.
compatibility: >-
  Python 3.8+.
metadata:
  version: "{version}"
  last_updated: "{updated}"
  cli_applicability: {cli}
  cli_support_evidence: >-
    Verified via `tccli {product} help`.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---
"""

# Valid skill but missing cli_support_evidence + environment.
MINIMAL = """\
---
name: qcloud-fake-ops
description: >-
  Test skill description.
compatibility: >-
  Python 3.8+.
metadata:
  version: "1.0.0"
  last_updated: "2026-01-01"
  cli_applicability: cli-only
---
"""

# Meta-skill style: no cli_applicability/cli_support_evidence/environment allowed.
GENERATOR = """\
---
name: qcloud-skill-generator
description: >-
  Meta-skill description.
compatibility: >-
  Python 3.8+.
metadata:
  version: "1.0.0"
  last_updated: "2026-01-01"
  type: meta-skill
---
"""


def write_skill(skill_dir: Path, content: str) -> Path:
    skill_dir.mkdir(parents=True, exist_ok=True)
    p = skill_dir / "SKILL.md"
    p.write_text(content, encoding="utf-8")
    return p


def valid(cli: str = "cli-first", version: str = "1.0.0", updated: str = "2026-01-01") -> str:
    return TEMPLATE.format(
        name="qcloud-fake-ops", cli=cli, product="cvm", version=version, updated=updated
    )


class FrontmatterPresenceTests(unittest.TestCase):
    def test_valid_skill_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = write_skill(Path(td), valid())
            errs, warns = vf.validate_skill(p)
            self.assertEqual(errs, [])
            self.assertEqual(warns, [])

    def test_missing_cli_support_evidence_fires(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = write_skill(Path(td), MINIMAL)
            errs, _ = vf.validate_skill(p)
            self.assertTrue(any("cli_support_evidence" in e for e in errs))

    def test_missing_environment_fires(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = write_skill(Path(td), MINIMAL)
            errs, _ = vf.validate_skill(p)
            self.assertTrue(any("environment" in e for e in errs))

    def test_skip_missing_required_downgrades_to_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = write_skill(Path(td), MINIMAL)
            errs, warns = vf.validate_skill(p, skip_missing_required=True)
            self.assertEqual(errs, [])
            self.assertTrue(any("cli_support_evidence" in w for w in warns))
            self.assertTrue(any("environment" in w for w in warns))

    def test_generator_exempt_from_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = write_skill(Path(td), GENERATOR)
            errs, warns = vf.validate_skill(p)
            self.assertEqual(errs, [])
            self.assertEqual(warns, [])


class DualPathCrossCheckTests(unittest.TestCase):
    def test_dual_path_without_cli_usage_fires(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = write_skill(Path(td), valid(cli="dual-path"))
            errs, _ = vf.validate_skill(p)
            self.assertTrue(any("cli-usage.md" in e for e in errs))

    def test_dual_path_with_cli_usage_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = write_skill(root, valid(cli="dual-path"))
            (root / "references").mkdir(parents=True, exist_ok=True)
            (root / "references" / "cli-usage.md").write_text("# cli usage\n", encoding="utf-8")
            errs, _ = vf.validate_skill(p)
            self.assertFalse(any("cli-usage.md" in e for e in errs))

    def test_skip_flag_does_not_weaken_dual_path_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = write_skill(Path(td), valid(cli="dual-path"))
            errs, _ = vf.validate_skill(p, skip_missing_required=True)
            self.assertTrue(any("cli-usage.md" in e for e in errs))


def _git(root: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")


class GitDiffBumpGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise unittest.SkipTest("git not available")

    def _repo_with_base(self, content: str) -> Path:
        root = Path(tempfile.mkdtemp())
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "t@test")
        _git(root, "config", "user.name", "t")
        write_skill(root / "qcloud-fake-ops", content)
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "base")
        return root

    def test_missing_bump_fires_and_bump_silent(self) -> None:
        root = self._repo_with_base(valid())
        # Working-tree change with version UNCHANGED -> must fire.
        changed = valid().replace("Test skill description.", "Test skill description. Changed.")
        write_skill(root / "qcloud-fake-ops", changed)
        errs, notes = vf.validate_git_diff(root, "HEAD")
        self.assertTrue(errs, f"expected bump error, notes={notes}")
        # Bump both fields -> must stay silent.
        write_skill(root / "qcloud-fake-ops", changed.replace('version: "1.0.0"', 'version: "1.1.0"')
                    .replace('last_updated: "2026-01-01"', 'last_updated: "2026-01-02"'))
        errs, _ = vf.validate_git_diff(root, "HEAD")
        self.assertEqual(errs, [])
        # Restore identical to base -> must stay silent.
        write_skill(root / "qcloud-fake-ops", valid())
        errs, _ = vf.validate_git_diff(root, "HEAD")
        self.assertEqual(errs, [])

    def test_new_file_skipped(self) -> None:
        root = self._repo_with_base(valid())
        write_skill(root / "qcloud-other-ops", valid())  # not committed -> untracked, not in diff
        # Untracked files are not listed by git diff --name-only; expect clean.
        errs, notes = vf.validate_git_diff(root, "HEAD")
        self.assertEqual(errs, [])
        self.assertTrue(notes)

    def test_cli_fire_and_silent(self) -> None:
        # End-to-end exit codes: main() with --git-diff.
        root = self._repo_with_base(valid())
        write_skill(root / "qcloud-fake-ops", valid().replace("Test skill description.", "Changed."))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vf.main(["--root", str(root), "--git-diff", "HEAD"]), 1)
        write_skill(root / "qcloud-fake-ops", valid().replace('version: "1.0.0"', 'version: "1.2.0"')
                    .replace('last_updated: "2026-01-01"', 'last_updated: "2026-01-03"'))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vf.main(["--root", str(root), "--git-diff", "HEAD"]), 0)

    def test_bad_base_ref_skips_gracefully(self) -> None:
        root = self._repo_with_base(valid())
        write_skill(root / "qcloud-fake-ops", valid().replace("Test skill description.", "Changed."))
        errs, notes = vf.validate_git_diff(root, "no-such-ref")
        self.assertEqual(errs, [])
        self.assertTrue(any("skipping" in n.lower() for n in notes))


if __name__ == "__main__":
    unittest.main()
