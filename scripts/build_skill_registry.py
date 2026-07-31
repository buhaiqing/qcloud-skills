#!/usr/bin/env python3
"""Build Skill Registry from all qcloud-*-ops/SKILL.md frontmatter.

Refactored in Phase 1 Step 1.2.2: now uses SkillRegistry as the single source
of truth and emits a richer JSON. Backward-compatible: existing fields kept,
new fields (product_name, operation_aliases, param_mapping, version,
last_updated, structured delegate_to) added when available.

Outputs: audit-results/skill-registry.json
Modes:
  --emit   write the registry JSON
  --check  CI gate: ensure all dual-path/sdk-only skills have >=5 golden
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit-results"

# Local import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_registry import SkillRegistry, load_hardcoded_from_copilot


def build() -> dict:
    reg = SkillRegistry.from_skill_dirs(ROOT, hardcoded=load_hardcoded_from_copilot())
    skills = []
    for name in reg.discover():
        e = reg.get_entry(name)
        skills.append({
            "name": e.name,
            "path": str(e.path),
            "cli_applicability": e.cli_applicability,
            "description": e.description,
            "intent_keywords": e.intent_keywords,
            "delegate_to": e.delegate_to,
            "product_name": e.product_name,
            "operation_aliases": e.operation_aliases,
            "param_mapping": e.param_mapping,
            "version": e.version,
            "last_updated": e.last_updated,
        })
    return {"skills": skills, "count": len(skills)}


def main() -> None:
    if "--emit" in sys.argv:
        data = build()
        AUDIT.mkdir(exist_ok=True)
        (AUDIT / "skill-registry.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"emitted {data['count']} skills")
        sys.exit(0)
    if "--check" in sys.argv:
        data = build()
        missing = []
        for s in data["skills"]:
            if s["cli_applicability"] in ("dual-path", "sdk-only"):
                gdir = Path(s["path"]) / "assets" / "golden"
                n = len(list(gdir.glob("*.json"))) if gdir.exists() else 0
                if n < 5:
                    missing.append(f"{s['name']}: {n}/5 golden")
        if missing:
            print("KPI#3 FAIL:\n" + "\n".join(missing))
            sys.exit(1)
        print("KPI#3 OK: all executable skills have >=5 golden")
        sys.exit(0)
    print("usage: --emit | --check")
    sys.exit(2)


if __name__ == "__main__":
    main()