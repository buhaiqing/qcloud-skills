#!/usr/bin/env python3
"""Validate Charter C2-C6 compliance across every `qcloud-*-ops/SKILL.md`.

Aligns with `qcloud-skill-generator/SKILL.md` §"Charter Compliance Checklist".

| Charter | What it checks                     | Pass criteria                         |
|---------|------------------------------------|---------------------------------------|
| C2      | SHOULD / SHOULD NOT sections       | Contains "SHOULD Use"                 |
| C3      | Five Core Standards                | Contains "Five Core Standards"        |
| C4      | Well-Architected Framework         | Contains "Well-Architected Framework" |
| C5      | Structured I/O placeholders        | ``^## Variable`` heading present      |
| C6      | Token Efficiency rules             | Contains ``TE-`` rule reference       |

(C1 = frontmatter → `validate_skills_frontmatter.py`; C7 = GCL → `check_gcl_conformance.py`.)

Usage:
  python3 scripts/validate_charter.py                    # lint all skills
  python3 scripts/validate_charter.py --json            # machine-readable report
  python3 scripts/validate_charter.py --skill qcloud-cvm-ops  # one skill
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Skills known to have structural exceptions — skip onerous checks.
META_SKILL = frozenset({"qcloud-skill-generator"})
CROSS_PRODUCT = frozenset({
    "qcloud-aiops-diagnosis",
    "qcloud-proactive-inspection",
    "qcloud-well-architected-review",
})
# Acceptance stub with no runbook content — charter standards don't apply.
STUB_SKILL = frozenset({"qcloud-test-ops"})

# ── helpers ─────────────────────────────────────────────────────────────────


def _check(path: Path, text: str) -> dict[str, Any]:
    """Check C2-C6 for one SKILL.md. Returns per-charter verdicts."""
    skill = path.parent.name

    # C2: "SHOULD Use" (template) OR "**SHOULD:" (older skills like CVM)
    c2 = bool(re.search(r"(?:SHOULD\s+Use|\*\*SHOULD[:])", text))
    # C3: "Five Core Standards" heading or table
    c3 = bool(re.search(r"Five Core Standards", text))
    # C4: "Well-Architected Framework" or "Well-Architected"
    c4 = bool(re.search(r"Well-Architected", text))

    # C5: ## Variables heading OR {{env.*}}/{{user.*}}/{{output.*}} placeholders
    c5 = bool(
        re.search(r"^##\s+Variable", text, re.MULTILINE)
        or re.search(r"\{\{(?:env|user|output)\.\w+\}\}", text)
    )

    # C6: TE-1 through TE-7 reference (Token Efficiency rule tag)
    c6 = bool(re.search(r"TE-[1-7]", text))

    # Relaxations for special skills
    if skill in META_SKILL:
        c2 = True  # meta-skill uses different section structure
        c3 = True  # meta-skill defines the standards, doesn't reference them
        c4 = True
        c5 = True  # meta-skill has env placeholder docs
    if skill in CROSS_PRODUCT:
        c4 = c4 or (path.parent / "references" / "well-architected-assessment.md").exists()
    if skill in STUB_SKILL:
        c2 = c3 = c4 = c5 = c6 = True

    return {
        "skill": skill,
        "C2_SHOULD_SHOULD_NOT": c2,
        "C3_Five_Core_Standards": c3,
        "C4_Well_Architected": c4,
        "C5_Variables": c5,
        "C6_Token_Efficiency": c6,
        "ok": c2 and c3 and c4 and c5 and c6,
    }


# ── public API ──────────────────────────────────────────────────────────────


def iter_skill_files(root: Path = ROOT) -> list[Path]:
    paths: list[Path] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("qcloud-"):
            continue
        skill_md = entry / "SKILL.md"
        if skill_md.is_file():
            paths.append(skill_md)
    return paths


def check_all(root: Path = ROOT) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in iter_skill_files(root):
        text = path.read_text(encoding="utf-8")
        reports.append(_check(path, text))
    return reports


def check_one(skill: str, root: Path = ROOT) -> dict[str, Any] | None:
    path = root / skill / "SKILL.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    return _check(path, text)


# ── CLI ─────────────────────────────────────────────────────────────────────


def _format_report(reports: list[dict[str, Any]], json_out: bool) -> int:
    if json_out:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        failing = [r for r in reports if not r["ok"]]
        passed = len(reports) - len(failing)
        print(f"Charter C2-C6: {passed}/{len(reports)} skills conform.\n")

        if failing:
            # Split into blocking (C2-C5) and advisory (C6-only)
            blocking = []
            advisory = []
            for r in failing:
                missing = [
                    name for name, ok in r.items()
                    if name.startswith("C") and name != "skill" and not ok
                ]
                only_c6 = set(missing) <= {"C6_Token_Efficiency"}
                (advisory if only_c6 else blocking).append((r["skill"], missing))

            if blocking:
                print(f"BLOCKING — C2-C5 gaps ({len(blocking)} skills):")
                for name, missing in blocking:
                    print(f"  - {name}: missing {', '.join(missing)}")

            if advisory:
                print(f"ADVISORY — C6 Token Efficiency only ({len(advisory)} skills):")
                for name, _ in advisory:
                    print(f"  - {name}")

            if blocking:
                return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    p.add_argument("--skill", default=None, help="Check exactly one skill directory")
    return p


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()

    if args.skill:
        report = check_one(args.skill, root)
        if report is None:
            print(f"not found: {root / args.skill / 'SKILL.md'}", file=sys.stderr)
            return 2
        reports = [report]
    else:
        reports = check_all(root)

    return _format_report(reports, json_out=args.json)


if __name__ == "__main__":
    sys.exit(main())
