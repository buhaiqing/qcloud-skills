#!/usr/bin/env python3
"""Run the local validation suite that mirrors the CI quality gates."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Step:
    name: str
    argv: tuple[str, ...]


def _compute_quality_score(report: dict[str, Any]) -> float:
    """Compute overall quality score (0-100) from skill report."""
    by_skill = report.get("by_skill", {})
    if not by_skill:
        return 100.0

    total_execs = report.get("total_executions", 0)
    if total_execs == 0:
        return 100.0

    total_passed = sum(s.get("pass", 0) for s in by_skill.values())
    pass_rate = total_passed / total_execs if total_execs > 0 else 1.0

    all_dims: dict[str, list[float]] = {}
    for skill_stats in by_skill.values():
        dims = skill_stats.get("dimensions_avg", {})
        for dim, val in dims.items():
            all_dims.setdefault(dim, []).append(val)

    dim_avg = sum(sum(v) / len(v) for v in all_dims.values()) / len(all_dims) if all_dims else 1.0

    score = (pass_rate * 0.6 + dim_avg * 0.4) * 100
    return round(score, 2)


def _determine_upgrade_signal(report: dict[str, Any]) -> str:
    """Determine upgrade signal severity from report."""
    upgrade_list = report.get("upgrade_signal", [])
    by_skill = report.get("by_skill", {})

    if not upgrade_list:
        return "none"

    total_skills = len(by_skill)
    upgrade_count = len(upgrade_list)

    if total_skills == 0:
        return "none"

    upgrade_ratio = upgrade_count / total_skills

    if upgrade_ratio >= 0.5:
        return "critical"
    if upgrade_ratio >= 0.25:
        return "major"
    return "minor"


def _generate_recommendations(report: dict[str, Any]) -> list[str]:
    """Generate recommendations based on quality report."""
    recommendations: list[str] = []
    by_skill = report.get("by_skill", {})
    upgrade_list = report.get("upgrade_signal", [])

    for skill in upgrade_list:
        stats = by_skill.get(skill, {})
        pass_rate = stats.get("pass_rate", 0.0)
        dims = stats.get("dimensions_avg", {})

        if pass_rate < 0.9:
            recommendations.append(f"{skill}: improve pass rate ({pass_rate:.0%} < 90%)")

        low_dims = [d for d, v in dims.items() if v < 0.8]
        if low_dims:
            recommendations.append(f"{skill}: strengthen dimensions: {', '.join(low_dims)}")

    return recommendations


def run_quality_score(root: Path, python: str = sys.executable) -> dict[str, Any]:
    """Run skill_quality_score.py and return transformed output."""
    argv = (python, "scripts/skill_quality_score.py", "score", "--json")
    print(f"$ {shlex.join(argv)}")

    result = subprocess.run(argv, cwd=root, capture_output=True, text=True)

    if result.returncode != 0:
        return {
            "quality_score": 0.0,
            "upgrade_signal": "critical",
            "recommendations": ["Failed to run quality score check"],
            "raw_error": result.stderr,
        }

    try:
        report = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {
            "quality_score": 0.0,
            "upgrade_signal": "critical",
            "recommendations": ["Failed to parse quality score output"],
        }

    return {
        "quality_score": _compute_quality_score(report),
        "upgrade_signal": _determine_upgrade_signal(report),
        "recommendations": _generate_recommendations(report),
        "_raw_report": report,
    }


def build_steps(python: str = sys.executable, github_output: bool = False) -> list[Step]:
    ruff_args = ("ruff", "check", ".")
    if github_output:
        ruff_args = ("ruff", "check", "--output-format=github", ".")

    return [
        Step("Ruff Python lint", ruff_args),
        Step("Validate SKILL.md frontmatter", (python, "scripts/validate_skills_frontmatter.py")),
        Step("Validate Well-Architected worker JSON examples", (python, "scripts/validate_product_assessment.py")),
        Step("Validate Markdown local links", (python, "scripts/check_markdown_links.py")),
        Step("Lint Python in Markdown", (python, "scripts/check_markdown_python.py", "--root", ".")),
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


def _print_quality_summary(result: dict[str, Any]) -> None:
    """Print quality score summary in a readable format."""
    print("\n==> Skill Quality Score")
    print(f"quality_score: {result['quality_score']}")
    print(f"upgrade_signal: {result['upgrade_signal']}")
    if result["recommendations"]:
        print("recommendations:")
        for rec in result["recommendations"]:
            print(f"  - {rec}")
    else:
        print("recommendations: []")


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

    quality_result = run_quality_score(root)
    _print_quality_summary(quality_result)

    if quality_result["upgrade_signal"] == "critical":
        print("\nWARNING: Critical upgrade signal detected", file=sys.stderr)
        return 1

    print("\nOK: local validation suite passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
