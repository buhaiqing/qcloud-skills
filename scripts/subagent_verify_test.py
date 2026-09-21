#!/usr/bin/env python3
"""Unit tests for scripts/subagent_verify.py (L28 disk verification tool).

Pure stdlib + tempfile. Run with:
    python3 -m pytest scripts/subagent_verify_test.py -v

Covers:
- file_exists / file_line_count / file_contains helpers
- git_changed_files / git_commits_ahead against a temp git repo
- verify_claims: success, missing file, line count mismatch,
  must-have-content pass/fail, committed-sha mismatch
- main() argparse wiring: invalid args, JSON output, exit codes
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import subagent_verify


def _make_temp_repo() -> Path:
    """Create a temp dir with a git repo + an initial commit.

    Returns the temp repo path. The repo has one file (README.md) committed
    in HEAD. Caller can then add new files and test detection.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="subagent_verify_test_"))
    subprocess.run(
        ["git", "init", "-b", "main", str(tmpdir)],
        capture_output=True, text=True, check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmpdir), "config", "user.email", "test@example.com"],
        capture_output=True, text=True, check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmpdir), "config", "user.name", "Test User"],
        capture_output=True, text=True, check=True,
    )
    (tmpdir / "README.md").write_text("Initial commit\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(tmpdir), "add", "README.md"],
        capture_output=True, text=True, check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmpdir), "commit", "-m", "initial"],
        capture_output=True, text=True, check=True,
    )
    return tmpdir


class TestHelpers(unittest.TestCase):
    """Tests for file_exists / file_line_count / file_contains helpers."""

    def setUp(self) -> None:
        self.tmp = _make_temp_repo()
        (self.tmp / "AGENTS.md").write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_file_exists_true(self) -> None:
        self.assertTrue(subagent_verify.file_exists(self.tmp, "AGENTS.md"))

    def test_file_exists_false(self) -> None:
        self.assertFalse(subagent_verify.file_exists(self.tmp, "does-not-exist.md"))

    def test_file_line_count_exact(self) -> None:
        self.assertEqual(subagent_verify.file_line_count(self.tmp, "AGENTS.md"), 3)

    def test_file_line_count_missing_returns_none(self) -> None:
        self.assertIsNone(subagent_verify.file_line_count(self.tmp, "missing.md"))

    def test_file_contains_true(self) -> None:
        self.assertTrue(subagent_verify.file_contains(self.tmp, "AGENTS.md", "line 2"))

    def test_file_contains_false(self) -> None:
        self.assertFalse(subagent_verify.file_contains(self.tmp, "AGENTS.md", "line 99"))


class TestGitHelpers(unittest.TestCase):
    """Tests for git_changed_files / git_commits_ahead against a temp repo."""

    def setUp(self) -> None:
        self.tmp = _make_temp_repo()
        # Make a new commit that adds a file
        (self.tmp / "new.md").write_text("new file\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(self.tmp), "add", "new.md"],
            capture_output=True, text=True, check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.tmp), "commit", "-m", "add new"],
            capture_output=True, text=True, check=True,
        )

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_get_current_sha_format(self) -> None:
        sha = subagent_verify.get_current_sha(self.tmp)
        # Full SHA is 40 hex chars
        self.assertEqual(len(sha), 40)
        self.assertTrue(all(c in "0123456789abcdef" for c in sha))

    def test_git_changed_files_since_sha(self) -> None:
        # Get the SHA of HEAD~1 (before the new file commit)
        head_minus_1 = subprocess.run(
            ["git", "-C", str(self.tmp), "rev-parse", "HEAD~1"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        changed = subagent_verify.git_changed_files(self.tmp, head_minus_1)
        self.assertIn("new.md", changed)

    def test_git_commits_ahead(self) -> None:
        head_minus_1 = subprocess.run(
            ["git", "-C", str(self.tmp), "rev-parse", "HEAD~1"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        commits = subagent_verify.git_commits_ahead(self.tmp, head_minus_1)
        self.assertEqual(len(commits), 1)


class TestVerifyClaims(unittest.TestCase):
    """Tests for verify_claims() — the main verification logic."""

    def setUp(self) -> None:
        self.tmp = _make_temp_repo()
        (self.tmp / "AGENTS.md").write_text(
            "## Section 1\n\nbody\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_all_claims_pass(self) -> None:
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=["AGENTS.md"],
            claimed_line_counts={"AGENTS.md": 4},
            must_exist=["AGENTS.md"],
            must_have_content={"AGENTS.md": ["Section 1"]},
            must_have_changed_files=[],
            committed_sha="",
            strict=True,
        )
        self.assertEqual(code, 0)
        self.assertTrue(all("[FAIL]" not in f for f in findings))

    def test_claimed_file_missing_fails(self) -> None:
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=["claimed-but-missing.md"],
            claimed_line_counts=None,
            must_exist=[],
            must_have_content=None,
            must_have_changed_files=[],
            committed_sha="",
            strict=False,
        )
        self.assertEqual(code, 1)
        self.assertTrue(any("[FAIL]" in f and "does not exist" in f for f in findings))

    def test_line_count_mismatch_fails(self) -> None:
        # AGENTS.md has 4 lines; claim it has 100 (way over tolerance of 5)
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=[],
            claimed_line_counts={"AGENTS.md": 100},
            must_exist=[],
            must_have_content=None,
            must_have_changed_files=[],
            committed_sha="",
            strict=False,
        )
        self.assertEqual(code, 1)
        self.assertTrue(any("line count mismatch" in f for f in findings))

    def test_line_count_within_tolerance_passes(self) -> None:
        # Test fixture writes AGENTS.md with 3 lines ("## Section 1\n\nbody\n").
        # Claim 4 lines: diff=1, tolerance=max(1, 4//20)=max(1,0)=1. Within tolerance.
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=[],
            claimed_line_counts={"AGENTS.md": 4},
            must_exist=[],
            must_have_content=None,
            must_have_changed_files=[],
            committed_sha="",
            strict=False,
        )
        # Within tolerance → no warning emitted, exit 0
        self.assertEqual(code, 0, f"expected 0, got {code} with findings {findings}")

    def test_must_have_content_missing_fails(self) -> None:
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=[],
            claimed_line_counts=None,
            must_exist=[],
            must_have_content={"AGENTS.md": ["NonexistentHeader"]},
            must_have_changed_files=[],
            committed_sha="",
            strict=False,
        )
        self.assertEqual(code, 1)
        self.assertTrue(any(
            "expected content missing" in f for f in findings
        ))

    def test_must_exist_missing_fails(self) -> None:
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=[],
            claimed_line_counts=None,
            must_exist=["required-but-missing.md"],
            must_have_content=None,
            must_have_changed_files=[],
            committed_sha="",
            strict=False,
        )
        self.assertEqual(code, 1)
        self.assertTrue(any("required file missing" in f for f in findings))

    def test_committed_sha_match(self) -> None:
        actual_sha = subagent_verify.get_current_sha(self.tmp)
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=[],
            claimed_line_counts=None,
            must_exist=[],
            must_have_content=None,
            must_have_changed_files=[],
            committed_sha=actual_sha,
            strict=False,
        )
        self.assertEqual(code, 0)
        self.assertTrue(all("SHA mismatch" not in f for f in findings))

    def test_committed_sha_mismatch_fails(self) -> None:
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=[],
            claimed_line_counts=None,
            must_exist=[],
            must_have_content=None,
            must_have_changed_files=[],
            committed_sha="0" * 40,  # wrong SHA
            strict=False,
        )
        self.assertEqual(code, 1)
        self.assertTrue(any("SHA mismatch" in f for f in findings), f"got {findings}")

    def test_must_have_changed_files_pass(self) -> None:
        # After setUp, AGENTS.md is committed. Stage (but don't commit) a new
        # file, then verify must_have_changed_files matches against HEAD
        # (empty SHA = compare staged + working tree vs HEAD).
        (self.tmp / "new_file.md").write_text("new\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(self.tmp), "add", "new_file.md"],
            capture_output=True, text=True, check=True,
        )
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=[],
            claimed_line_counts=None,
            must_exist=[],
            must_have_content=None,
            must_have_changed_files=["new_file.md"],
            committed_sha="",  # empty = compare staged + working tree vs HEAD
            strict=False,
        )
        self.assertEqual(code, 0, f"expected 0, got {code}: {findings}")

    def test_must_have_changed_files_missing_fails(self) -> None:
        # After setUp, AGENTS.md is the only committed file. Claiming new_file.md
        # in git diff since HEAD should fail because no such file exists yet.
        head_sha = subagent_verify.get_current_sha(self.tmp)
        code, findings = subagent_verify.verify_claims(
            self.tmp,
            claimed_files=[],
            claimed_line_counts=None,
            must_exist=[],
            must_have_content=None,
            must_have_changed_files=["phantom_file.md"],
            committed_sha=head_sha,
            strict=False,
        )
        self.assertEqual(code, 1)
        self.assertTrue(any(
            "not in git diff" in f for f in findings
        ), f"got findings: {findings}")


class TestMainArgparse(unittest.TestCase):
    """Tests for main() argparse wiring and exit codes."""

    def setUp(self) -> None:
        self.tmp = _make_temp_repo()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_args_exits_2(self) -> None:
        from io import StringIO
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            with self.assertRaises(SystemExit) as ctx:
                subagent_verify.main()
            self.assertEqual(ctx.exception.code, 2)
        finally:
            sys.stderr = old_stderr

    def test_pass_with_minimal_args(self) -> None:
        # Create one file that matches must_exist
        (self.tmp / "exists.md").write_text("ok\n", encoding="utf-8")
        code = subagent_verify.main_with_root(
            self.tmp,
            must_exist=["exists.md"],
        )
        self.assertEqual(code, 0)

    def test_fail_with_missing_required_file(self) -> None:
        code = subagent_verify.main_with_root(
            self.tmp,
            must_exist=["definitely-missing.md"],
        )
        self.assertEqual(code, 1)

    def test_json_output(self) -> None:
        from io import StringIO
        (self.tmp / "exists.md").write_text("ok\n", encoding="utf-8")
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            code = subagent_verify.main_with_root(
                self.tmp,
                must_exist=["exists.md"],
                json_output=True,
            )
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertEqual(code, 0)
        parsed = json.loads(output)
        self.assertEqual(parsed["exit_code"], 0)
        self.assertIn("findings", parsed)
        self.assertIn("claim_summary", parsed)


if __name__ == "__main__":
    unittest.main()