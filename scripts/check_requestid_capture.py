#!/usr/bin/env python3
"""
Pre-commit hook: detect tccli response handling missing RequestId capture.

Exits 0 = all clear, 1 = issues found (commit blocked).

Detection rules:
  A. tccli subprocess: subprocess.run(["tccli", ...]) / subprocess.run("tccli", ...)
     → requires RequestId captured (data["Response"].get("RequestId") or log with RequestId)
  B. tencentcloud-sdk: response.Response accessed without capturing RequestId
  C. json.load(stdout) or result.stdout parsed without RequestId extraction

Usage (pre-commit hook, no args):
    python3 scripts/check_requestid_capture.py

Usage (self-test):
    python3 scripts/check_requestid_capture.py --self-test
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ─── Rule A: tccli subprocess + RequestId capture ─────────────────────────────

_TCCLI_RE = re.compile(r"subprocess\.run\s*\(\s*(\[|\")", re.IGNORECASE)
# GOOD patterns: RequestId captured
_REQUESTID_GET_RE = re.compile(r'RequestId\s*\)', re.IGNORECASE)
_REQUESTID_LOG_RE = re.compile(r'RequestId["\']', re.IGNORECASE)
_REQUESTID_VAR_RE = re.compile(r'request[_-]?id\s*=', re.IGNORECASE)
# Skip read-only operations (no write semantics, traceability less critical)
_READONLY_OPS_RE = re.compile(
    r"--version|Describe|Query|List|Get|Check|",
    re.IGNORECASE
)


def check_tccli_requestid(text: str) -> list[str]:
    """
    Return list of lines where tccli subprocess response is consumed
    but RequestId is not captured within 10 lines.
    """
    issues: list[str] = []
    lines = text.splitlines()
    in_triple = False

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if '"""' in stripped or "'''" in stripped:
            in_triple = not in_triple
            continue
        if in_triple or not stripped or stripped.startswith('#'):
            continue
        if not _TCCLI_RE.search(line):
            continue
        # Skip read-only operations
        if _READONLY_OPS_RE.search(line):
            continue

        # Found tccli call — look forward for Response consumption and RequestId capture
        window_end = min(len(lines), lineno + 10)
        window = "\n".join(lines[lineno - 1:window_end])

        has_response = "Response" in window
        has_requestid = (
            _REQUESTID_GET_RE.search(window)
            or _REQUESTID_LOG_RE.search(window)
            or _REQUESTID_VAR_RE.search(window)
        )

        if has_response and not has_requestid:
            issues.append(
                f"  Line {lineno}: tccli response consumed without RequestId capture\n"
                f"    {stripped[:80]}"
            )
    return issues


# ─── Rule B: tencentcloud-sdk response.Response without RequestId ──────────────

_SDK_CALL_RE = re.compile(r"\.Response\.[A-Z]", re.IGNORECASE)
_SDK_IMPORT_RE = re.compile(r"from tencentcloud", re.IGNORECASE)
_SDK_REQUESTID_RE = re.compile(r"RequestId", re.IGNORECASE)


def check_sdk_requestid(text: str) -> list[str]:
    """
    Return list of issues where tencentcloud-sdk response.Response is accessed
    but RequestId is not captured within ±5 lines.
    """
    issues: list[str] = []
    lines = text.splitlines()

    for lineno, line in enumerate(lines, 1):
        if not _SDK_CALL_RE.search(line):
            continue
        # Look backward for SDK import
        start = max(0, lineno - 6)
        window_before = "\n".join(lines[start:lineno - 1])
        if not _SDK_IMPORT_RE.search(window_before):
            continue
        # Look for RequestId in surrounding lines
        window_end = min(len(lines), lineno + 4)
        nearby = "\n".join(lines[start:window_end])
        if not _SDK_REQUESTID_RE.search(nearby):
            issues.append(
                f"  Line {lineno}: response.Response accessed without RequestId capture\n"
                f"    {line.strip()[:80]}"
            )
    return issues


# ─── Rule C: json.load(stdout) / result.stdout parsed without RequestId ───────

_JSON_PARSE_RE = re.compile(r"json\.(load|loads)\s*\(", re.IGNORECASE)
_RESULT_STDOUT_RE = re.compile(r"\.stdout", re.IGNORECASE)


def check_json_stdout_requestid(text: str) -> list[str]:
    """
    Return list of issues where stdout JSON is parsed but RequestId not extracted.
    Detects patterns like:
      data = json.loads(result.stdout)
      data = json.load(f)
      resp = json.loads(stdout)
    where Response/Result is consumed without RequestId capture.
    """
    issues: list[str] = []
    lines = text.splitlines()
    in_triple = False

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if '"""' in stripped or "'''" in stripped:
            in_triple = not in_triple
            continue
        if in_triple or not stripped or stripped.startswith('#'):
            continue

        has_json_parse = _JSON_PARSE_RE.search(line)
        has_stdout = _RESULT_STDOUT_RE.search(line)
        if not (has_json_parse or has_stdout):
            continue
        # Skip cases that already capture RequestId in this line
        if _SDK_REQUESTID_RE.search(line):
            continue

        # Look forward for Response consumption
        window_end = min(len(lines), lineno + 8)
        window = "\n".join(lines[lineno - 1:window_end])

        has_response = "Response" in window or "InstanceSet" in window
        has_requestid = (
            _REQUESTID_GET_RE.search(window)
            or _REQUESTID_LOG_RE.search(window)
            or _REQUESTID_VAR_RE.search(window)
        )

        if has_response and not has_requestid:
            issues.append(
                f"  Line {lineno}: stdout/stderr JSON parsed without RequestId capture\n"
                f"    {stripped[:80]}"
            )
    return issues


# ─── Per-file check ───────────────────────────────────────────────────────────

def check_file(path: Path) -> list[str]:
    """Return all RequestId capture issues in a Python file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"  Cannot read {path}: {e}"]

    issues: list[str] = []
    issues.extend(check_tccli_requestid(text))
    issues.extend(check_sdk_requestid(text))
    issues.extend(check_json_stdout_requestid(text))
    return issues


# ─── Self-test ───────────────────────────────────────────────────────────────

SELF_TEST_CASES = [
    # ── Rule A: tccli subprocess ─────────────────────────────────────────────
    (
        "A-GOOD: tccli with RequestId capture",
        (
            'result = subprocess.run(["tccli", "cvm", "DescribeInstances", "--Region", "ap-guangzhou"])\n'
            'data = json.loads(result.stdout)\n'
            'request_id = data["Response"].get("RequestId")\n'
            'log.info("DescribeInstances", request_id=request_id)\n'
            'instances = data["Response"]["InstanceSet"]'
        ),
        False,
    ),
    (
        "A-BAD: tccli without RequestId capture",
        (
            'result = subprocess.run(["tccli", "cvm", "RunInstances", "--Region", "ap-guangzhou"])\n'
            'data = json.loads(result.stdout)\n'
            'instances = data["Response"]["InstanceSet"]'
        ),
        True,
    ),
    # ── Rule B: tencentcloud-sdk ─────────────────────────────────────────────
    (
        "B-GOOD: SDK with RequestId capture",
        (
            "from tencentcloud.cvm.v20170312 import cvm_client, models\n"
            "req = models.RunInstancesRequest()\n"
            "resp = client.RunInstances(req)\n"
            "request_id = resp.Response.RequestId\n"
            "log.info('run_instances', request_id=request_id)\n"
            "instances = resp.Response.InstanceSet"
        ),
        False,
    ),
    (
        "B-BAD: SDK without RequestId capture",
        (
            "from tencentcloud.cvm.v20170312 import cvm_client, models\n"
            "req = models.RunInstancesRequest()\n"
            "resp = client.RunInstances(req)\n"
            "instances = resp.Response.InstanceSet"
        ),
        True,
    ),
    # ── Rule C: json.load stdout ─────────────────────────────────────────────
    (
        "C-GOOD: json.loads stdout with RequestId capture",
        (
            'resp = subprocess.run(["tccli", "cvm", "DescribeInstances"], capture_output=True)\n'
            'data = json.loads(resp.stdout)\n'
            'request_id = data.get("RequestId") or data.get("Response", {}).get("RequestId")\n'
            'logger.info("RequestId", request_id=request_id)\n'
            'instances = data["Response"]["InstanceSet"]'
        ),
        False,
    ),
    (
        "C-BAD: json.loads stdout without RequestId",
        (
            'resp = subprocess.run(["tccli", "cvm", "DescribeInstances"], capture_output=True)\n'
            'data = json.loads(resp.stdout)\n'
            'instances = data["Response"]["InstanceSet"]'
        ),
        True,
    ),
    # ── Clean cases ──────────────────────────────────────────────────────────
    (
        "Clean: no tccli/SDK calls",
        "x = 1\ny = 2\nlog.info('hello')\n",
        False,
    ),
    (
        "Clean: tccli Describe (read-only, no write)",
        'subprocess.run(["tccli", "cvm", "DescribeInstances", "--Region", "ap-guangzhou"])',
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

    return [Path(p) for p in result.stdout.splitlines() if Path(p).suffix == ".py"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Check RequestId capture in tccli/SDK response handling")
    parser.add_argument("--self-test", action="store_true", help="Run internal self-test")
    parser.add_argument("--files", nargs="*", type=Path, help="Specific files to check (default: git staged .py)")
    args = parser.parse_args()

    if args.self_test:
        print("check_requestid_capture.py self-test")
        ok = self_test()
        sys.exit(0 if ok else 1)

    files = args.files if args.files else get_staged_python_files()

    if not files:
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
        print(f"\n[{total_issues} RequestId capture issue(s)] — commit blocked")
        print("Fix: capture RequestId from response and log it for traceability.")
        sys.exit(1)
    else:
        print("check_requestid_capture.py: all clear")
        sys.exit(0)


if __name__ == "__main__":
    main()
