#!/usr/bin/env python3
"""GCL Tier-A conformance checker.

Verifies that each of the 24 ``qcloud-*-ops`` skills ships the canonical
Generator-Critic-Loop artifact set required by ``AGENTS.md`` §8 / §10:

- ``references/rubric.md`` with exactly 8 numbered sections (1..8, no gaps)
- ``references/prompt-templates.md`` with exactly 7 numbered sections (1..7, no gaps)
- ``SKILL.md`` containing the ``## Quality Gate (GCL)`` heading

Usage:
    python3 scripts/check_gcl_conformance.py            # human-readable summary
    python3 scripts/check_gcl_conformance.py --json     # machine-readable JSON
    python3 scripts/check_gcl_conformance.py --root DIR # scan a different root

Exits 0 if all 24 skills conform, 1 otherwise.

Pure stdlib — no external dependencies. Python 3.10+ syntax.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


#: Canonical 24-skill set declared in ``AGENTS.md`` §8. Order is irrelevant
#: (we always sort on output); immutability prevents accidental mutation.
GCL_SKILLS: frozenset[str] = frozenset({
    "qcloud-cvm-ops",
    "qcloud-cdb-ops",
    "qcloud-clb-ops",
    "qcloud-cos-ops",
    "qcloud-es-ops",
    "qcloud-redis-ops",
    "qcloud-tke-ops",
    "qcloud-vpc-ops",
    "qcloud-cam-ops",
    "qcloud-cdn-ops",
    "qcloud-cbs-ops",
    "qcloud-cls-ops",
    "qcloud-ckafka-ops",
    "qcloud-scf-ops",
    "qcloud-mongodb-ops",
    "qcloud-postgres-ops",
    "qcloud-ssl-ops",
    "qcloud-agsx-ops",
    "qcloud-finops-ops",
    "qcloud-monitor-ops",
    "qcloud-aiops-diagnosis",
    "qcloud-proactive-inspection",
    "qcloud-well-architected-review",
    "qcloud-skill-generator",
})


def _count_numbered_sections(text: str, target: int) -> int:
    """Return ``target`` if all sections ``1..target`` are present, else ``0``.

    The skill's rubric.md / prompt-templates.md must contain a contiguous,
    gap-free sequence of ``## N. Title`` headings starting at 1. Any missing
    section makes the file non-conformant; we return 0 to make that
    unambiguous in the report (a non-zero value would otherwise suggest
    partial credit).

    The ``\\.`` after the number guards against false matches like
    ``## 1.0`` or ``## 10.`` — only single-digit ordinals 1..target count.
    """
    if target < 1:
        return 0
    for n in range(1, target + 1):
        if not re.search(rf"^## {n}\. ", text, re.MULTILINE):
            return 0
    return target


def check_skill(root: Path, skill: str) -> dict[str, Any]:
    """Build the per-skill conformance report.

    Returns a dict with the eight canonical keys (see AGENTS.md / Tier-A
    plan spec). Missing files are reported as 0/false rather than raising,
    so a single missing artifact cannot crash the sweep.
    """
    skill_dir = root / skill
    rubric_path = skill_dir / "references" / "rubric.md"
    prompt_path = skill_dir / "references" / "prompt-templates.md"
    skill_path = skill_dir / "SKILL.md"

    rubric_sections = 0
    if rubric_path.is_file():
        rubric_sections = _count_numbered_sections(
            rubric_path.read_text(encoding="utf-8"), 8,
        )

    prompt_sections = 0
    if prompt_path.is_file():
        prompt_sections = _count_numbered_sections(
            prompt_path.read_text(encoding="utf-8"), 7,
        )

    has_quality_gate = False
    if skill_path.is_file():
        has_quality_gate = bool(
            re.search(r"^## Quality Gate \(GCL\)$", skill_path.read_text(encoding="utf-8"), re.MULTILINE)
        )

    rubric_ok = rubric_sections == 8
    prompt_ok = prompt_sections == 7
    skill_ok = has_quality_gate

    return {
        "skill": skill,
        "rubric_sections": rubric_sections,
        "prompt_sections": prompt_sections,
        "has_quality_gate": has_quality_gate,
        "rubric_ok": rubric_ok,
        "prompt_ok": prompt_ok,
        "skill_ok": skill_ok,
        "ok": rubric_ok and prompt_ok and skill_ok,
    }


def check_all(root: Path) -> list[dict[str, Any]]:
    """Run :func:`check_skill` against every entry in :data:`GCL_SKILLS`.

    Output is sorted by skill name for stable diffs in CI logs.
    """
    return [check_skill(root, skill) for skill in sorted(GCL_SKILLS)]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Check GCL Tier-A artifact conformance across all qcloud-* skills.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repo root to scan (default: parent of this script).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON with `summary` and `reports` keys.",
    )
    return parser


def _format_human(reports: list[dict[str, Any]]) -> str:
    """Render the human-readable summary."""
    passing = sum(1 for r in reports if r["ok"])
    total = len(reports)
    lines: list[str] = [f"GCL conformance: {passing}/{total} skills conform."]
    failing = [r for r in reports if not r["ok"]]
    if failing:
        lines.append("")
        for r in failing:
            reasons: list[str] = []
            if not r["rubric_ok"]:
                reasons.append(f"rubric_sections={r['rubric_sections']}/8")
            if not r["prompt_ok"]:
                reasons.append(f"prompt_sections={r['prompt_sections']}/7")
            if not r["skill_ok"]:
                reasons.append("missing `## Quality Gate (GCL)` in SKILL.md")
            lines.append(f"  FAIL {r['skill']}: {', '.join(reasons)}")
    return "\n".join(lines) + "\n"


def cmd_check(args: argparse.Namespace) -> int:
    """CLI entry point. Returns the desired process exit code."""
    reports = check_all(args.root)
    passing = sum(1 for r in reports if r["ok"])

    if args.json:
        payload = {
            "summary": {
                "total": len(reports),
                "passing": passing,
                "failing": len(reports) - passing,
            },
            "reports": reports,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_human(reports), end="")

    return 0 if passing == len(reports) else 1


def main() -> int:
    """Module entry point."""
    parser = build_parser()
    args = parser.parse_args()
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
