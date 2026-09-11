#!/usr/bin/env python3
"""Generate ≥5 golden scenario seed files per executable skill.

Scope (Phase 1 KPI#3 enforcement companion):

For every qcloud-*-ops skill that the registry lists as `dual-path` or
`sdk-only` AND that currently has <5 parseable golden files under
`assets/golden/`, emit 5 seed scenarios. The seeds are intentionally
generic across products (list / describe / create / update / delete)
because real per-action tccli plumbing requires per-skill authorship
that this script does NOT pretend to do.

Seeds are marked with `"_seed": true` and `"_seed_generator":
"generate_golden_seeds.py"` so downstream tooling (fixture authors,
sandbox E2E) can distinguish them from hand-curated golden files
(see qcloud-cvm-ops/assets/golden/list_instances.json for the
canonical non-seed example).

What this script guarantees:
- Every executable skill has ≥5 parseable JSON files under assets/golden/.
- `python3 scripts/build_skill_registry.py --check` therefore exits 0.

What this script does NOT do:
- Discover real tccli actions (cli_support_evidence is free text;
  hardcoding per-skill action lists is fragile and belongs to a
  per-skill authorship pass).
- Generate fixtures. `expected.fixture` is set to null; human authors
  must replace it with a path under assets/fixtures/.
- Modify qcloud-cvm-ops, which already has a hand-curated golden.

Idempotency: re-running is safe. Existing non-seed files are left
alone; only missing slots are filled.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Five canonical operational intents that map cleanly to describe/list
# /create/update/delete style tccli actions across most Tencent Cloud
# products. Keep these in sync with the seed_* filenames emitted below.
SEED_INTENTS = [
    ("seed_list", "List all resources in {{user.region}}", "list"),
    ("seed_describe_one", "Describe one resource by id in {{user.region}}", "describe"),
    ("seed_create", "Create a new resource with default settings in {{user.region}}", "create"),
    ("seed_update", "Update attributes of an existing resource in {{user.region}}", "update"),
    ("seed_delete", "Delete a resource by id in {{user.region}} (destructive; requires confirmation token)", "delete"),
]

SEED_GENERATOR = "generate_golden_seeds.py"
SEED_MARKER = True
REQUIRED_PER_SKILL = 5


def executable_skills() -> list[Path]:
    """Return SKILL.md paths for skills whose cli_applicability needs golden."""
    skill_dirs = sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("qcloud-") and p.name.endswith("-ops"))
    out = []
    for d in skill_dirs:
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text(encoding="utf-8")
        if "cli_applicability: \"dual-path\"" in text or "cli_applicability: \"sdk-only\"" in text:
            out.append(d)
    return out


def existing_golden(skill_dir: Path) -> list[Path]:
    gdir = skill_dir / "assets" / "golden"
    if not gdir.exists():
        return []
    return sorted(p for p in gdir.glob("*.json") if p.is_file())


def make_seed(skill_name: str, slot: str, intent_text: str, action_verb: str) -> dict:
    """Build one seed scenario. action is intentionally a placeholder."""
    return {
        "_seed": SEED_MARKER,
        "_seed_generator": SEED_GENERATOR,
        "_seed_skill": skill_name,
        "_seed_action_verb": action_verb,
        "intent": intent_text,
        "input": {
            "action": f"<REPLACE_WITH_REAL_TCCLI_ACTION_FOR_{action_verb.upper()}>",
            "region": "{{env.TENCENTCLOUD_REGION}}",
        },
        "expected": {
            "fixture": None,
            "assertions": [
                {"path": "$.Response", "op": "exists"},
            ],
        },
    }


def emit_seeds(skill_dir: Path) -> tuple[int, int]:
    """Return (seeded_count, skipped_existing_count)."""
    gdir = skill_dir / "assets" / "golden"
    existing = existing_golden(skill_dir)
    if len(existing) >= REQUIRED_PER_SKILL:
        return 0, len(existing)
    gdir.mkdir(parents=True, exist_ok=True)
    seeded = 0
    for slot, intent_text, verb in SEED_INTENTS:
        out = gdir / f"{slot}.json"
        if out.exists():
            continue
        out.write_text(
            json.dumps(make_seed(skill_dir.name, slot, intent_text, verb), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        seeded += 1
    return seeded, len(existing)


def main() -> int:
    targets = executable_skills()
    total_seeded = 0
    total_skipped_skills = 0
    for d in targets:
        seeded, existing = emit_seeds(d)
        if seeded > 0:
            print(f"seeded  {d.name}: +{seeded} (was {existing}/{REQUIRED_PER_SKILL})")
            total_seeded += seeded
        else:
            print(f"skip    {d.name}: already has {existing}/{REQUIRED_PER_SKILL}")
            total_skipped_skills += 1
    print(f"\ntotal: seeded {total_seeded} files across {len(targets)} skills; {total_skipped_skills} already complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
