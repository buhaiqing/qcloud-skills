#!/usr/bin/env python3
"""Fail when the pytest runner does not actually collect the committed suite.

`python3 -m pytest scripts -q` is the runner CI executes, so a test file pytest
never collects never runs -- and a suite that silently shrinks stays green.
This gate measures the runner instead of trusting it, catching the two silent
failure modes:

  C1 <collected> < <floor>   the collected count fell below the committed floor
                             (assets/shared/thresholds.json:tests_min_collected);
                             e.g. a stray conftest/pyproject deselecting tests
  C2 <file>                  a test file whose name never appears in pytest's
                             node ids, i.e. named outside every configured
                             runner pattern (the historical `test_*.py` vs
                             `*_test.py` gap -- 292 tests skipped)

Collection runs as `pytest --collect-only -q -c /dev/null` inside <root>/scripts
so no upper-level config can mask the real suite. Exit codes: 0 clean,
1 findings, 2 misconfiguration (no scripts dir, unreadable/invalid floor,
unparseable pytest output) -- 2 means "could not measure", never "clean".
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

THRESHOLDS_REL = Path("assets/shared/thresholds.json")
SCRIPTS_REL = Path("scripts")
FLOOR_KEY = "tests_min_collected"

COLLECT_COUNT_RE = re.compile(r"^(\d+) tests? collected\b", re.MULTILINE)
NODE_ID_RE = re.compile(r"^([^\s:]+\.py)::", re.MULTILINE)
TEST_FILE_NAME_RE = re.compile(r"^(?:test_.*|.*_test)\.py$")
TEST_CONTENT_RE = re.compile(r"unittest\.TestCase|^[ \t]*def test_", re.MULTILINE)

PYTEST_ARGS = ("--collect-only", "-q", "-c", "/dev/null")
SKIP_DIR_NAMES = {"__pycache__", "node_modules", ".venv", "venv"}


class ConfigError(Exception):
    """The gate cannot measure what it is meant to measure."""


@dataclass
class Report:
    collected: int
    floor: int
    test_files: int
    findings: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "collected": self.collected,
            "floor": self.floor,
            "test_files": self.test_files,
            "findings": [{"code": code, "detail": detail} for code, detail in self.findings],
        }


def load_floor(root: Path) -> int:
    """Read tests_min_collected, rejecting anything that is not a plain int."""
    path = root / THRESHOLDS_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read {path} for {FLOOR_KEY}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc}") from exc
    floor = data.get(FLOOR_KEY) if isinstance(data, dict) else None
    if isinstance(floor, bool) or not isinstance(floor, int):
        raise ConfigError(f"{path}: {FLOOR_KEY} must be an integer, got {floor!r}")
    return floor


def collect(root: Path) -> tuple[int, set[str]]:
    """Run the CI runner's collection pass; return (count, collected file names)."""
    scripts_dir = root / SCRIPTS_REL
    if not scripts_dir.is_dir():
        raise ConfigError(f"no scripts directory at {scripts_dir}")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *PYTEST_ARGS],
            cwd=scripts_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ConfigError(f"cannot run pytest: {exc}") from exc
    match = COLLECT_COUNT_RE.search(proc.stdout)
    if match is None:
        detail = " | ".join((proc.stderr or proc.stdout).strip().splitlines()[-3:])
        raise ConfigError(f"pytest reported no collected count (exit {proc.returncode}): {detail}")
    names = {Path(node).name for node in NODE_ID_RE.findall(proc.stdout)}
    return int(match.group(1)), names


def scan_test_files(root: Path) -> list[Path]:
    """Files a reader would call tests: runner-pattern name, or test-shaped body."""
    scripts_dir = root / SCRIPTS_REL
    found: list[Path] = []
    for path in sorted(scripts_dir.rglob("*.py")):
        relative = path.relative_to(scripts_dir)
        if any(part.startswith(".") or part in SKIP_DIR_NAMES for part in relative.parts[:-1]):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if TEST_FILE_NAME_RE.match(path.name) or TEST_CONTENT_RE.search(text):
            found.append(path)
    return found


def evaluate(root: Path) -> Report:
    floor = load_floor(root)
    collected, collected_names = collect(root)
    test_files = scan_test_files(root)
    report = Report(collected=collected, floor=floor, test_files=len(test_files))
    if collected < floor:
        report.findings.append(
            ("C1", f"{collected} < {floor}: collected count below tests_min_collected")
        )
    for path in test_files:
        if path.name not in collected_names:
            report.findings.append(
                ("C2", f"{path.relative_to(root)}: not collected by pytest (unmatched name)")
            )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", default=".", help="repository root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        report = evaluate(root)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        print(
            f"test collection: {report.collected} collected, floor {report.floor}, "
            f"{report.test_files} test files"
        )
        for code, detail in report.findings:
            print(f"{code} {detail}")
        if report.ok:
            print("OK: runner collects the committed suite")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
