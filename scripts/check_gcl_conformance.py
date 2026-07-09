#!/usr/bin/env python3
"""GCL Tier-A conformance checker (CI gate for plan 2026-06-18-gcl-tier-b-c-d-conformance).

Validates every skill in ``AGENTS.md`` §8 has the three GCL artifacts at Tier A quality:
- ``references/rubric.md`` with 8 numbered sections (§1 Scope, §2 Dimensions,
  §3 Per-dim checklist, §4 Product-specific rules, §5 Output schema, §6 Worked examples,
  §7 Changelog, §8 See also)
- ``references/prompt-templates.md`` with 7 numbered sections (§1 Generator,
  §2 Critic, §3 Orchestrator, §4 Per-op variants, §5 Anti-patterns, §6 Changelog,
  §7 See also)
- ``SKILL.md`` with ``## Quality Gate (GCL)`` heading

Exit codes:
  0 — all skills conform
  1 — at least one skill fails conformance (CI failure)
  2 — repository layout unexpected
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Mirrors AGENTS.md §8. Single source of truth — when AGENTS.md changes,
# update this set and re-run check.
GCL_SKILLS: frozenset[str] = frozenset({
    # Product-scoped (27)
    "qcloud-cvm-ops", "qcloud-cdb-ops", "qcloud-clb-ops", "qcloud-cos-ops",
    "qcloud-es-ops", "qcloud-redis-ops", "qcloud-tke-ops", "qcloud-vpc-ops",
    "qcloud-cam-ops", "qcloud-cdn-ops", "qcloud-cbs-ops", "qcloud-cls-ops",
    "qcloud-ckafka-ops", "qcloud-scf-ops", "qcloud-mongodb-ops",
    "qcloud-postgres-ops", "qcloud-ssl-ops", "qcloud-agsx-ops",
    "qcloud-finops-ops", "qcloud-monitor-ops",
    "qcloud-ccn-ops", "qcloud-vpn-ops", "qcloud-dc-ops",
    "qcloud-cicd-ops", "qcloud-service-mesh-ops", "qcloud-migration-ops",
    "qcloud-tcop-ops",
    # Cross-product (3)
    "qcloud-aiops-diagnosis", "qcloud-proactive-inspection",
    "qcloud-well-architected-review",
    # Meta-skill (1)
    "qcloud-skill-generator",
})

EXPECTED_RUBRIC_SECTIONS = 8  # §1..§8
EXPECTED_PROMPT_SECTIONS = 7  # §1..§7
_NUMBERED_HEADING = re.compile(r"^##\s+(\d+)\.\s+\S", re.MULTILINE)
_QUALITY_GATE = re.compile(r"^##\s+Quality Gate \(GCL\)\s*$", re.MULTILINE)


def _count_numbered_sections(text: str, target: int) -> int:
    """Return the highest-numbered section heading; -1 if none.

    Conformance rule: sections 1..target must all be present, and the highest
    present number must equal target (no gaps).
    """
    matches = [int(m.group(1)) for m in _NUMBERED_HEADING.finditer(text)]
    if not matches:
        return 0
    # All sections 1..target must appear at least once.
    return max(matches) if set(range(1, target + 1)).issubset(set(matches)) else 0


def check_skill(root: Path, skill: str) -> dict[str, Any]:
    """Return a per-skill conformance report. ``ok`` is True iff all three artifacts conform."""
    skill_dir = root / skill
    rubric_path = skill_dir / "references" / "rubric.md"
    prompt_path = skill_dir / "references" / "prompt-templates.md"
    skill_path = skill_dir / "SKILL.md"

    rubric_text = rubric_path.read_text(encoding="utf-8") if rubric_path.exists() else ""
    prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

    rubric_sections = _count_numbered_sections(rubric_text, EXPECTED_RUBRIC_SECTIONS)
    prompt_sections = _count_numbered_sections(prompt_text, EXPECTED_PROMPT_SECTIONS)
    has_quality_gate = bool(_QUALITY_GATE.search(skill_text))

    rubric_ok = bool(rubric_path.exists()) and rubric_sections == EXPECTED_RUBRIC_SECTIONS
    prompt_ok = bool(prompt_path.exists()) and prompt_sections == EXPECTED_PROMPT_SECTIONS
    skill_ok = bool(skill_path.exists()) and has_quality_gate

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
    """Run the full conformance sweep; returns one report per skill in GCL_SKILLS."""
    return [check_skill(root, skill) for skill in sorted(GCL_SKILLS)]


def cmd_check(args: argparse.Namespace) -> int:
    reports = check_all(args.root)
    failing = [r for r in reports if not r["ok"]]
    summary = {
        "total": len(reports),
        "passing": len(reports) - len(failing),
        "failing": len(failing),
        "failing_skills": [r["skill"] for r in failing],
    }
    if args.json:
        print(json.dumps({"summary": summary, "reports": reports}, indent=2))
    else:
        print(f"GCL conformance: {summary['passing']}/{summary['total']} skills conform.")
        if failing:
            print(f"\nFAILING ({len(failing)}):")
            for r in failing:
                reasons = []
                if not r["rubric_ok"]:
                    reasons.append(f"rubric={r['rubric_sections']}/8")
                if not r["prompt_ok"]:
                    reasons.append(f"prompt={r['prompt_sections']}/7")
                if not r["skill_ok"]:
                    reasons.append("no Quality Gate")
                print(f"  - {r['skill']}: {', '.join(reasons)}")
    return 1 if failing else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    p.set_defaults(func=cmd_check)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
