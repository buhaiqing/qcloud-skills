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
    lines = m.group(1).splitlines()
    i = 0
    BLOCK_INDICATORS = (">-", ">", "|", "|-", "|+")
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        val = raw.strip()
        # block scalar: value empty or an indicator -> gather indented continuation
        if val == "" or val.rstrip() in BLOCK_INDICATORS:
            body = []
            j = i + 1
            while j < len(lines) and (lines[j].startswith(" ") or lines[j].startswith("\t")):
                body.append(lines[j].strip())
                j += 1
            fm[key] = " ".join(body)
            i = j
        else:
            fm[key] = val.strip().strip('"')
            i += 1
    return fm

def _eval_intents(skill_dir: Path) -> list[str]:
    """Curated routing keywords from the skill's own eval_queries.json.

    Each skill's eval set already declares the `intent` values it should
    trigger on (e.g. "RunInstances"). Those are the canonical intent keywords
    for routing — prefer them over guessing from prose. Returns [] if absent.
    """
    eq = skill_dir / "assets" / "eval_queries.json"
    if not eq.exists():
        return []
    try:
        data = json.loads(eq.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict):
        data = data.get("queries", [])
    intents = [q["intent"] for q in data if isinstance(q, dict) and q.get("intent")]
    # de-dupe, preserve order
    seen: set[str] = set()
    return [i for i in intents if not (i in seen or seen.add(i))]

def build() -> dict:
    skills = []
    for sk in sorted(ROOT.glob("qcloud-*-ops/SKILL.md")):
        fm = parse_frontmatter(sk.read_text())
        if not fm:
            continue
        skill_dir = sk.parent
        # intent_keywords = backtick API names from description (existing)
        #  + curated `intent` values from the skill's own eval_queries.json
        backtick = re.findall(r"`([^`]+)`", fm.get("description", ""))
        keywords = backtick + _eval_intents(skill_dir)
        seen: set[str] = set()
        dedupe = [k for k in keywords if not (k in seen or seen.add(k))]
        skills.append({
            "name": fm.get("name", skill_dir.name),
            "path": str(skill_dir),
            "cli_applicability": fm.get("cli_applicability", ""),
            "description": fm.get("description", ""),
            "intent_keywords": dedupe,
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
