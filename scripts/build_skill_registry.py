#!/usr/bin/env python3
"""Build Skill Registry from all qcloud-*-ops/SKILL.md frontmatter.
Emits audit-results/skill-registry.json. Also --check for CI (KPI #3)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit-results"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm

def build():
    skills = []
    for sk in sorted(ROOT.glob("qcloud-*-ops/SKILL.md")):
        fm = parse_frontmatter(sk.read_text())
        if not fm:
            continue
        skills.append({
            "name": fm.get("name", sk.parent.name),
            "path": str(sk.parent),
            "cli_applicability": fm.get("cli_applicability", ""),
            "description": fm.get("description", ""),
            "intent_keywords": re.findall(r"`([^`]+)`", fm.get("description", "")),
            "delegate_to": fm.get("related_skills", ""),
        })
    return {"skills": skills, "count": len(skills)}

def main():
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
