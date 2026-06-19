#!/usr/bin/env python3
"""Run the local validation suite that mirrors the CI quality gates."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Step:
    name: str
    argv: tuple[str, ...]


def build_steps(python: str = sys.executable, github_output: bool = False) -> list[Step]:
    ruff_args = ("ruff", "check", ".")
    if github_output:
        ruff_args = ("ruff", "check", "--output-format=github", ".")

    return [
        Step("Ruff Python lint", ruff_args),
        Step("Validate SKILL.md frontmatter", (python, "scripts/validate_skills_frontmatter.py")),
        Step("Validate Well-Architected worker JSON examples", (python, "scripts/validate_product_assessment.py")),
        Step("Validate Markdown local links", (python, "scripts/check_markdown_links.py")),
        Step(
            "GCL runner smoke test",
            (
                python,
                "scripts/gcl_runner.py",
                "run",
                "--skill",
                "qcloud-well-architected-review",
                "--request",
                "CI smoke test",
                "--command",
                'echo {"Response":{"RequestId":"ci-smoke"}}',
                "--max-iter",
                "1",
                "--structural-critic-only",
            ),
        ),
        Step("GCL trace aggregate", (python, "scripts/gcl_trace_aggregate.py", "--since-hours", "168")),
        Step(
            "Script unit tests",
            (python, "-m", "unittest", "discover", "-s", "scripts", "-p", "*_test.py", "-v"),
        ),
        Step(
            "GCL alarm wire plan",
            (
                python,
                "scripts/gcl_alarm_wire.py",
                "plan",
                "--summary",
                "scripts/fixtures/gcl-quality-summary-healthy.json",
            ),
        ),
        Step("GCL Tier-A conformance", (python, "scripts/check_gcl_conformance.py")),
    ]


def run_step(root: Path, step: Step) -> int:
    print(f"\n==> {step.name}")
    print("$ " + shlex.join(step.argv))
    proc = subprocess.run(step.argv, cwd=root)
    return proc.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--list", action="store_true", help="Print commands without running them")
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Use GitHub annotation output for Ruff, matching CI output formatting",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    steps = build_steps(github_output=args.github_output)

    if args.list:
        for step in steps:
            print(f"{step.name}: {shlex.join(step.argv)}")
        return 0

    for step in steps:
        rc = run_step(root, step)
        if rc != 0:
            print(f"\nFAILED: {step.name} exited with {rc}", file=sys.stderr)
            return rc

    print("\nOK: local validation suite passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
