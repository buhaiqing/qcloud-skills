#!/usr/bin/env python3
"""
check_idempotency.py — Pre-commit hook: detect non-idempotent tccli/sdk/requests calls.

Exits 0 = all clear, 1 = issues found (commit blocked).

Detection rules:
  A. tccli subprocess: subprocess.run(["tccli", ...]) / subprocess.run("tccli", ...)
     → requires --ClientToken somewhere in the command list
  B. tencentcloud-sdk: from tencentcloud.X import Y / client.Call(...)
     → requires ClientToken field in request object
  C. requests: requests.post(...) / requests.get(...) / requests.request(...)
     → requires headers={"Idempotency-Key": ...} or "Idempotency-Key" in headers dict

Usage (pre-commit hook, no args):
    python3 scripts/check_idempotency.py

Usage (self-test):
    python3 scripts/check_idempotency.py --self-test
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ─── Rule A: tccli subprocess ─────────────────────────────────────────────────

_TCCLI_RE = re.compile(r"subprocess\.run\s*\(\s*(\[|\")", re.IGNORECASE)
_CLIENTTOKEN_RE = re.compile(r"--ClientToken|--client-token", re.IGNORECASE)


def check_tccli_subprocess(text: str) -> list[str]:
    """
    Return list of lines where tccli subprocess lacks --ClientToken.
    Skips:
      - Comment / docstring lines
      - String literal lines (inside triple-quoted strings)
      - Read-only operations: --version, Describe*, Query*, List*, Get*
    """
    issues = []
    in_triple = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        # Track triple-quoted string boundaries
        if '"""' in stripped or "'''" in stripped:
            in_triple = not in_triple
            continue
        if in_triple:
            continue
        # Skip blank, comment-only lines
        if not stripped or stripped.startswith('#'):
            continue
        if not _TCCLI_RE.search(line):
            continue
        # Skip read-only operations (check after tccli marker for string form)
        lower = line.lower()
        if '--version' in lower or 'describe' in lower or 'query' in lower or 'list' in lower or 'get' in lower or 'check' in lower:
            continue
        # tccli call detected — check for ClientToken flag
        if not _CLIENTTOKEN_RE.search(line):
            issues.append(f"  Line {lineno}: tccli subprocess without --ClientToken\n    {line.strip()}")
    return issues


# ─── Rule B: tencentcloud-sdk ─────────────────────────────────────────────────

_SDK_IMPORT_RE = re.compile(r"from tencentcloud", re.IGNORECASE)
# Match: client.MethodName(...) or variable = client.MethodName(...)
_SDK_CALL_RE = re.compile(
    r"(?:\w+\s*=\s*)?\w+\.\w+\s*\(",
    re.IGNORECASE
)
_CLIENTTOKEN_FIELD_RE = re.compile(r"ClientToken\s*=", re.IGNORECASE)


def check_tencentcloud_sdk(text: str) -> list[str]:
    """
    Return list of issues for tencentcloud-sdk calls without ClientToken.

    Uses a regex sliding-window approach:
      - When we find a tencentcloud import AND a nearby client.Method(...) call,
        check if ClientToken= appears within ±5 lines.
    """
    issues: list[str] = []
    lines = text.splitlines()

    for lineno, line in enumerate(lines, 1):
        if not _SDK_CALL_RE.search(line):
            continue
        # Look backward for SDK import
        start = max(0, lineno - 6)
        window_before = "\n".join(lines[start:lineno - 1])
        has_sdk_import = _SDK_IMPORT_RE.search(window_before)
        if not has_sdk_import:
            continue
        # Look for ClientToken in surrounding lines
        window_after = min(len(lines), lineno + 4)
        nearby = "\n".join(lines[start:window_after])
        if not _CLIENTTOKEN_FIELD_RE.search(nearby):
            issues.append(
                f"  Line {lineno}: tencentcloud-sdk call without ClientToken in request\n    {line.strip()}"
            )
    return issues


# ─── Rule C: requests with no Idempotency-Key header ──────────────────────────

_REQUESTS_CALL_RE = re.compile(
    r"requests\.(post|put|patch|delete|request)\s*\(",
    re.IGNORECASE,
)
_IDEMPOTENCY_KEY_RE = re.compile(r"Idempotency-Key", re.IGNORECASE)


def check_requests_headers(text: str) -> list[str]:
    """Return list of line numbers where requests calls lack Idempotency-Key header."""
    issues = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not _REQUESTS_CALL_RE.search(line):
            continue
        if not _IDEMPOTENCY_KEY_RE.search(line):
            issues.append(f"  Line {lineno}: requests call without Idempotency-Key header\n    {line.strip()}")
    return issues


# ─── Per-file check ───────────────────────────────────────────────────────────

def check_file(path: Path) -> list[str]:
    """Return all idempotency issues in a Python file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"  Cannot read {path}: {e}"]

    issues: list[str] = []
    issues.extend(check_tccli_subprocess(text))
    issues.extend(check_tencentcloud_sdk(text))
    issues.extend(check_requests_headers(text))
    return issues


# ─── Self-test ───────────────────────────────────────────────────────────────

SELF_TEST_CASES = [
    # (description, file_content, expect_issues)
    (
        "tccli subprocess WITH ClientToken",
        'subprocess.run(["tccli", "cvm", "RunInstances", "--ClientToken", token, "--Region", "ap-guangzhou"])',
        False,
    ),
    (
        "tccli subprocess WITHOUT ClientToken",
        'subprocess.run(["tccli", "cvm", "RunInstances", "--Region", "ap-guangzhou"])',
        True,
    ),
    (
        "requests.post WITH Idempotency-Key",
        'requests.post(url, headers={"Idempotency-Key": str(uuid.uuid4())})',
        False,
    ),
    (
        "requests.post WITHOUT Idempotency-Key",
        "requests.post(url, json=payload)",
        True,
    ),
    (
        "tencentcloud-sdk call without ClientToken (import form)",
        (
            "from tencentcloud.cvm.v20170312 import cvm_client, models\n"
            "req = models.RunInstancesRequest()\n"
            "resp = client.RunInstances(req)\n"
        ),
        True,
    ),
    (
        "tencentcloud-sdk call with ClientToken in request",
        (
            "from tencentcloud.cvm.v20170312 import cvm_client, models\n"
            "req = models.RunInstancesRequest()\n"
            "req.ClientToken = str(uuid.uuid4())\n"
            "resp = client.RunInstances(req)\n"
        ),
        False,
    ),
    (
        "tccli string form without ClientToken",
        'subprocess.run("tccli cvm RunInstances --Region ap-guangzhou", shell=True)',
        True,
    ),
    (
        "clean file (no API calls)",
        "x = 1\ny = 2\n",
        False,
    ),
]


def self_test() -> bool:
    """Run self-test, return True if all pass."""
    all_pass = True
    for desc, content, expect_issues in SELF_TEST_CASES:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as fh:
            fh.write(content)
            fh.flush()
            path = Path(fh.name)

        issues = check_file(path)
        path.unlink()

        has_issues = bool(issues)
        ok = has_issues == expect_issues
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {desc}")
        if not ok:
            if expect_issues:
                print("         Expected issues, got none")
            else:
                for iss in issues:
                    print(f"         Unexpected: {iss}")

    return all_pass


# ─── Main ─────────────────────────────────────────────────────────────────────

def get_staged_python_files() -> list[Path]:
    """Return list of staged Python files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        print("git not found — skipping staged file check", file=sys.stderr)
        return []

    files = []
    for path in result.stdout.splitlines():
        p = Path(path)
        if p.suffix == ".py":
            files.append(p)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Check idempotency in Python files")
    parser.add_argument("--self-test", action="store_true", help="Run internal self-test")
    parser.add_argument("--files", nargs="*", type=Path, help="Specific files to check (default: git staged .py)")
    args = parser.parse_args()

    if args.self_test:
        print("check_idempotency.py self-test")
        ok = self_test()
        sys.exit(0 if ok else 1)

    files = args.files if args.files else get_staged_python_files()

    if not files:
        # No staged Python files — nothing to check, allow commit
        sys.exit(0)

    total_issues = 0
    for path in files:
        issues = check_file(path)
        if issues:
            print(f"\n{path}:")
            for iss in issues:
                print(iss)
            total_issues += len(issues)

    if total_issues:
        print(f"\n[{total_issues} idempotency issue(s)] — commit blocked")
        print("Fix: add --ClientToken to tccli calls, ClientToken field to SDK requests,")
        print("     or Idempotency-Key header to requests calls.")
        sys.exit(1)
    else:
        print("check_idempotency.py: all clear")
        sys.exit(0)


if __name__ == "__main__":
    main()
