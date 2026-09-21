#!/usr/bin/env python3
"""Enforce L28: subagent report = hint, not truth.

Per `docs/execution-lessons.md` L28:
    Subagent reports are unreliable bidirectionally — both "done"
    (fabricated commit SHA, inflated mutation %s) and "not done"
    (0 output, no artifacts) have been observed in production.

This script provides a deterministic disk-state verifier that any
agent runtime can call after dispatching a subagent. It compares
the subagent's CLAIMED file changes and line-count deltas against
actual disk state, and exits non-zero on mismatch.

Usage:
    # After subagent completes, verify claimed changes:
    python3 scripts/subagent_verify.py \\
        --root /path/to/repo \\
        --claimed-files AGENTS.md docs/execution-lessons.md \\
        --claimed-line-counts AGENTS.md:347 docs/execution-lessons.md:35 \\
        --committed-sha <expected_commit_or_HEAD> \\
        [--strict]   # treat warnings as failures

    # Or, simpler: just check that specific files have non-trivial content:
    python3 scripts/subagent_verify.py \\
        --root /path/to/repo \\
        --must-exist AGENTS.md docs/new-file.md \\
        --must-have-content '{"docs/new-file.md": ["section header", "key claim"]}'

Exit codes:
    0 — all claims verified
    1 — one or more claims failed verification
    2 — invalid arguments / setup error

Why a separate script (not a subagent)?
    Subagent reports about subagent work are the problem. Verification
    MUST be done by a non-subagent process that reads disk state directly.
    This script is that process.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _run_git(root: Path, *git_args: list[str]) -> str:
    """Run git command and return stdout. Raises on non-zero exit."""
    proc = subprocess.run(
        ["git", "-C", str(root), *git_args],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return proc.stdout


def get_current_sha(root: Path) -> str:
    """Return current HEAD commit SHA (full)."""
    return _run_git(root, "rev-parse", "HEAD").strip()


def file_exists(root: Path, rel_path: str) -> bool:
    """Check if a file relative to root exists on disk."""
    return (root / rel_path).is_file()


def file_line_count(root: Path, rel_path: str) -> int | None:
    """Return line count of a file, or None if file doesn't exist."""
    path = root / rel_path
    if not path.is_file():
        return None
    try:
        return sum(1 for _ in path.open("rb"))
    except OSError:
        return None


def file_contains(root: Path, rel_path: str, substring: str) -> bool:
    """Check if a file contains a substring (byte-level)."""
    path = root / rel_path
    if not path.is_file():
        return False
    try:
        return substring.encode("utf-8") in path.read_bytes()
    except (OSError, UnicodeEncodeError):
        return False


def git_changed_files(root: Path, since_sha: str) -> list[str]:
    """Return list of files changed since the given commit (or HEAD if empty).

    If since_sha is empty, compares staged + working-tree changes vs HEAD,
    which is the natural baseline for "what the subagent just did before
    committing".
    """
    diff_args = ["--diff-filter=AM"]
    if since_sha:
        # Diff between since_sha and working tree (includes committed + staged + working)
        diff_args += [since_sha]
    else:
        # Empty SHA: compare HEAD vs working tree (includes staged + working)
        diff_args += ["HEAD"]
    proc = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", *diff_args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return [f for f in proc.stdout.strip().splitlines() if f]


def git_commits_ahead(root: Path, since_sha: str) -> list[str]:
    """Return list of commit SHAs ahead of since_sha."""
    if not since_sha:
        return []
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-list", "--reverse", f"{since_sha}..HEAD"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return [s for s in proc.stdout.strip().splitlines() if s]


def verify_claims(
    root: Path,
    claimed_files: list[str],
    claimed_line_counts: dict[str, int] | None,
    must_exist: list[str],
    must_have_content: dict[str, list[str]] | None,
    must_have_changed_files: list[str],
    committed_sha: str,
    strict: bool,
) -> tuple[int, list[str]]:
    """Run all verifications. Returns (exit_code, findings_list).

    findings_list contains human-readable strings:
      - "[OK] ..." for passed verifications (only when --strict)
      - "[FAIL] ..." for failed verifications (always shown)
    """
    findings: list[str] = []

    # 1. Verify all claimed files exist on disk
    for rel_path in claimed_files:
        if file_exists(root, rel_path):
            if strict:
                findings.append(f"[OK] file exists: {rel_path}")
        else:
            findings.append(f"[FAIL] claimed file does not exist on disk: {rel_path}")

    # 2. Verify claimed line counts match actual
    if claimed_line_counts:
        for rel_path, expected_lines in claimed_line_counts.items():
            actual = file_line_count(root, rel_path)
            if actual is None:
                findings.append(
                    f"[FAIL] claimed {rel_path} has {expected_lines} lines; "
                    f"file does not exist on disk"
                )
            elif actual != expected_lines:
                # Allow ±5% tolerance for line counts (subagents often approximate)
                tolerance = max(1, expected_lines // 20)
                if abs(actual - expected_lines) > tolerance:
                    findings.append(
                        f"[FAIL] line count mismatch: {rel_path} "
                        f"claimed={expected_lines} actual={actual} "
                        f"(tolerance=±{tolerance})"
                    )
                else:
                    if strict:
                        findings.append(
                            f"[WARN] line count near-miss: {rel_path} "
                            f"claimed={expected_lines} actual={actual} "
                            f"(within ±{tolerance} tolerance)"
                        )
            else:
                if strict:
                    findings.append(f"[OK] line count exact: {rel_path} = {actual}")

    # 3. Verify must-exist files exist
    for rel_path in must_exist:
        if file_exists(root, rel_path):
            if strict:
                findings.append(f"[OK] required file exists: {rel_path}")
        else:
            findings.append(f"[FAIL] required file missing: {rel_path}")

    # 4. Verify must-have-content
    if must_have_content:
        for rel_path, substrings in must_have_content.items():
            for substring in substrings:
                if file_contains(root, rel_path, substring):
                    if strict:
                        findings.append(
                            f"[OK] content present in {rel_path}: {substring[:50]!r}"
                        )
                else:
                    findings.append(
                        f"[FAIL] expected content missing in {rel_path}: "
                        f"{substring[:50]!r}"
                    )

    # 4b. Verify must-have-changed-files (git diff since committed_sha)
    if must_have_changed_files:
        # Use committed_sha if given; else compare against HEAD (i.e. uncommitted
        # + committed-since-fork). Empty string = compare working tree vs HEAD.
        changed = git_changed_files(root, committed_sha)
        for rel_path in must_have_changed_files:
            if rel_path in changed:
                if strict:
                    findings.append(
                        f"[OK] file in git diff since {committed_sha[:12] or 'HEAD'}: {rel_path}"
                    )
            else:
                findings.append(
                    f"[FAIL] file not in git diff since {committed_sha[:12] or 'HEAD'}: {rel_path}"
                )

    # 5. Verify committed SHA matches actual HEAD (if claimed)
    if committed_sha:
        actual_sha = get_current_sha(root)
        if actual_sha.startswith(committed_sha):
            if strict:
                findings.append(f"[OK] HEAD sha matches claim ({committed_sha[:12]})")
        else:
            findings.append(
                f"[FAIL] committed SHA mismatch: claimed={committed_sha[:12]} "
                f"actual={actual_sha[:12]}"
            )

    # Compute exit code: any FAIL -> 1
    has_fail = any("[FAIL]" in f for f in findings)
    return (1 if has_fail else 0), findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--root", type=Path, default=ROOT,
        help="Path to repo root (default: %(default)s)",
    )
    parser.add_argument(
        "--claimed-files", nargs="*", default=[],
        help="List of file paths the subagent CLAIMED to have created/modified",
    )
    parser.add_argument(
        "--claimed-line-counts", type=json.loads, default=None,
        help='JSON object mapping file path -> claimed line count, '
             'e.g. \'{"AGENTS.md": 347, "docs/x.md": 35}\'',
    )
    parser.add_argument(
        "--must-exist", nargs="*", default=[],
        help="Files that must exist on disk after subagent completes",
    )
    parser.add_argument(
        "--must-have-changed-files", nargs="*", default=[],
        help="Files that must appear in `git diff --name-only` since the "
             "committed_sha (or since fork point if no SHA given)",
    )
    parser.add_argument(
        "--must-have-content", type=json.loads, default=None,
        help='JSON object mapping file path -> list of substrings that must '
             'be present, e.g. \'{"docs/x.md": ["section header"]}\'',
    )
    parser.add_argument(
        "--committed-sha", default="",
        help="Commit SHA the subagent claimed to have created. "
             "Recommended: pass ≥7 chars (short SHA) — the verifier uses "
             "startswith() match for convenience. Pass full 40-char SHA for "
             "strict exact-match behavior.",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Treat near-misses (within line-count tolerance) as warnings, "
             "and report all [OK] findings",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output findings as JSON for machine parsing",
    )
    return parser


def main() -> int:
    """CLI entry point. Parses argv via argparse."""
    parser = build_parser()
    args = parser.parse_args()
    return main_with_root(
        root=args.root,
        claimed_files=args.claimed_files,
        claimed_line_counts=args.claimed_line_counts,
        must_exist=args.must_exist,
        must_have_content=args.must_have_content,
        must_have_changed_files=args.must_have_changed_files,
        committed_sha=args.committed_sha,
        strict=args.strict,
        json_output=args.json,
    )


def main_with_root(
    root: Path | None = None,
    claimed_files: list[str] | None = None,
    claimed_line_counts: dict[str, int] | None = None,
    must_exist: list[str] | None = None,
    must_have_content: dict[str, list[str]] | None = None,
    must_have_changed_files: list[str] | None = None,
    committed_sha: str = "",
    strict: bool = False,
    json_output: bool = False,
) -> int:
    """Test-friendly wrapper that bypasses argparse.

    When invoked as a CLI, main() calls this with all args defaulted; the
    CLI defaults to ROOT + no claims, which raises argparse error.
    When invoked from tests, callers pass explicit values.
    """
    root = root or ROOT
    claimed_files = claimed_files or []
    must_exist = must_exist or []
    must_have_changed_files = must_have_changed_files or []

    if not any([
        claimed_files, claimed_line_counts,
        must_exist, must_have_content, must_have_changed_files, committed_sha,
    ]):
        # Mimic argparse.error path
        print(
            "ERROR: at least one of --claimed-files, --claimed-line-counts, "
            "--must-exist, --must-have-content, --must-have-changed-files, "
            "--committed-sha is required",
            file=sys.stderr,
        )
        return 2

    try:
        exit_code, findings = verify_claims(
            root,
            claimed_files,
            claimed_line_counts,
            must_exist,
            must_have_content,
            must_have_changed_files,
            committed_sha,
            strict,
        )
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git command failed: {e}", file=sys.stderr)
        return 2
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: invalid JSON argument: {e}", file=sys.stderr)
        return 2

    if json_output:
        result: dict[str, Any] = {
            "exit_code": exit_code,
            "findings": findings,
            "claim_summary": {
                "claimed_files_count": len(claimed_files),
                "claimed_line_counts_count": len(claimed_line_counts or {}),
                "must_exist_count": len(must_exist),
                "must_have_content_count": len(must_have_content or {}),
                "committed_sha_given": bool(committed_sha),
            },
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for finding in findings:
            print(finding)
        if exit_code != 0:
            print(f"\n{exit_code} verification failure(s).", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())