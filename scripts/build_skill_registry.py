#!/usr/bin/env python3
"""Build Skill Registry from all qcloud-*-ops/SKILL.md frontmatter.

Refactored in Phase 1 Step 1.2.2: now uses SkillRegistry as the single source
of truth and emits a richer JSON. Backward-compatible: existing fields kept,
new fields (product_name, operation_aliases, param_mapping, version,
last_updated, structured delegate_to) added when available.

Outputs: audit-results/skill-registry.json
Modes:
  --emit   write the registry JSON
  --check  CI gate (KPI#3): every executable skill (dual-path / sdk-only)
           must provide golden-sample evidence — either a parseable JSON
           under assets/golden/, or (when the golden dir is absent) a
           non-empty assets/eval_queries.json list. Missing both is a hard
           failure; coverage via eval_queries.json only is informational.
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


def _is_valid_json(path: Path) -> bool:
    """Return True when the file parses as JSON (used by the --check gate)."""
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except (json.JSONDecodeError, OSError):
        return False


def _has_eval_queries(skill_path: Path) -> bool:
    """Return True when assets/eval_queries.json holds a non-empty JSON list."""
    p = skill_path / "assets" / "eval_queries.json"
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(data, list) and len(data) > 0


def main() -> None:
    if "--emit" in sys.argv:
        data = build()
        AUDIT.mkdir(exist_ok=True)
        (AUDIT / "skill-registry.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"emitted {data['count']} skills")
        sys.exit(0)
    if "--check" in sys.argv:
        data = build()
        notes = []
        missing = []
        for s in data["skills"]:
            if s["cli_applicability"] not in ("dual-path", "sdk-only"):
                continue
            gdir = Path(s["path"]) / "assets" / "golden"
            if gdir.exists():
                golden = list(gdir.glob("*.json"))
                if not any(_is_valid_json(p) for p in golden):
                    missing.append(f"{s['name']}: {len(golden)} golden file(s) present, none parse as JSON")
                continue
            if not _has_eval_queries(Path(s["path"])):
                missing.append(f"{s['name']}: no golden samples and no eval_queries.json")
            else:
                notes.append(f"{s['name']}: covered by eval_queries.json (no assets/golden/ dir)")
        if notes:
            print("golden-sample coverage notes:")
            for n in notes:
                print(f"  note {n}")
        if missing:
            print("KPI#3 FAIL:\n" + "\n".join(missing))
            sys.exit(1)
        print("KPI#3 OK: all executable skills have golden samples or eval_queries.json evidence")
        sys.exit(0)
    print("usage: --emit | --check")
    sys.exit(2)


if __name__ == "__main__":
    main()