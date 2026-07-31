#!/usr/bin/env python3
"""CI gate: validate every error table in every qcloud-*-ops/SKILL.md.

Phase 1.3 linter. Walks the repo, parses tables, and checks:

1. **Action validity** — every parsed Action is in {HALT, RETRY, FIX, DELEGATE}.
2. **delegate_to is registered** — every non-empty delegate_to target exists
   in the SkillRegistry (or KNOWN_SKILLS fallback if the registry output is
   unavailable).
3. **Backoff is parseable** — explicit ``"2s,4s,8s"`` lists and the
   ``"exponential"`` keyword are recognised.
4. **Max retries is non-negative** — sanity check.
5. **Within-table duplicates** — same error code twice in one SKILL.md
   *table* is a copy-paste bug. (Same code across *different* operation
   tables is intentional and not flagged.)

Exit code:

* ``0`` — all checks pass
* ``1`` — at least one violation

Usage:
    python3 scripts/validate_error_tables.py           # full sweep
    python3 scripts/validate_error_tables.py --skill qcloud-cvm-ops
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from error_escalator import Action, ErrorRule
from error_table_parser import _extract_tables, parse_error_table


def _load_known_skills(repo_root: Path) -> set[str]:
    """Read the registry JSON if present, otherwise scan dirs.

    Falls back to a direct glob of ``qcloud-*-ops/`` so the linter stays
    usable before the registry has been built.
    """
    audit = repo_root / "audit-results" / "skill-registry.json"
    if audit.is_file():
        try:
            data = json.loads(audit.read_text(encoding="utf-8"))
            names = {s["name"] for s in data.get("skills", [])}
            if names:
                return names
        except (json.JSONDecodeError, KeyError):
            pass
    return {p.parent.name for p in repo_root.glob("qcloud-*-ops/SKILL.md")}


def _validate_rules(
    skill: str,
    rules: list[ErrorRule],
    known_skills: set[str],
) -> list[str]:
    """Return a list of human-readable violation messages.

    Note: duplicates are NOT flagged here — the same error code appearing
    under multiple operations (e.g. RunInstances + StopInstances both
    referencing ``RequestLimitExceeded``) is intentional. Duplicates are
    scoped within a single table only (see ``_validate_within_table_duplicates``).
    """
    violations: list[str] = []

    for r in rules:
        # Action validity (already enforced by enum but assert defensively).
        if r.action not in {a for a in Action}:
            violations.append(
                f"[{skill}] {r.code}: invalid action {r.action!r}"
            )
        # delegate_to must be a known skill (or None / empty).
        if r.delegate_to and r.delegate_to not in known_skills:
            violations.append(
                f"[{skill}] {r.code}: delegate_to={r.delegate_to!r} "
                f"not in SkillRegistry (known: {sorted(known_skills)[:5]}…)"
            )
        # Max retries non-negative.
        if r.max_retries < 0:
            violations.append(
                f"[{skill}] {r.code}: max_retries={r.max_retries} < 0"
            )
        # Backoff_seconds elements non-negative (skip when empty).
        for i, sec in enumerate(r.backoff_seconds):
            if sec < 0:
                violations.append(
                    f"[{skill}] {r.code}: backoff_seconds[{i}]={sec} < 0"
                )
        # Backoff_strategy must be a known strategy (we only emit "fixed"
        # or "exponential" — anything else is a parser bug worth flagging).
        if r.backoff_strategy not in ("fixed", "exponential"):
            violations.append(
                f"[{skill}] {r.code}: backoff_strategy={r.backoff_strategy!r} "
                f"unknown (use 'fixed' or 'exponential')"
            )

    return violations


def _validate_within_table_duplicates(skill: str, skill_md_text: str) -> list[str]:
    """Flag duplicate codes within a single error table only.

    The same code appearing under different operations is legitimate, but
    two identical rows in the same table is a copy-paste bug worth flagging.

    Only error tables (those whose header looks like an error-code column)
    are considered; pre-flight check tables are skipped.
    """
    from error_table_parser import _detect_format  # local import to avoid cycle
    violations: list[str] = []
    for table in _extract_tables(skill_md_text):
        if not table:
            continue
        if _detect_format(table[0]) is None:
            continue
        seen: dict[str, int] = {}
        for row in table[1:]:
            if not row or not row[0].strip():
                continue
            code = row[0].strip().strip("`").strip()
            if not code:
                continue
            seen[code] = seen.get(code, 0) + 1
        for code, n in seen.items():
            if n > 1:
                violations.append(
                    f"[{skill}] {code}: appears {n} times in same table"
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=ROOT,
        help="Repo root (default: parent of this script)",
    )
    parser.add_argument(
        "--skill", type=str, default=None,
        help="Restrict to a single skill name (debug)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit JSON instead of human-readable summary",
    )
    args = parser.parse_args()

    known_skills = _load_known_skills(args.root)
    targets: list[Path]
    if args.skill:
        targets = [args.root / args.skill]
    else:
        targets = sorted((args.root).glob("qcloud-*-ops"))

    all_violations: list[str] = []
    scanned: list[dict] = []
    for skill_dir in targets:
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        rules = parse_error_table(text)
        violations = _validate_rules(skill_dir.name, rules, known_skills)
        violations.extend(
            _validate_within_table_duplicates(skill_dir.name, text)
        )
        scanned.append({
            "skill": skill_dir.name,
            "rule_count": len(rules),
            "violations": violations,
        })
        all_violations.extend(violations)

    summary = {
        "skills_scanned": len(scanned),
        "total_rules": sum(s["rule_count"] for s in scanned),
        "violations": all_violations,
        "per_skill": scanned,
    }

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        for s in scanned:
            verdict = "OK " if not s["violations"] else "FAIL"
            print(f"{verdict} {s['skill']:<24} rules={s['rule_count']:>3}")
            for v in s["violations"]:
                print(f"    {v}")
        print(f"\n{summary['skills_scanned']} skills, "
              f"{summary['total_rules']} rules, "
              f"{len(all_violations)} violations")

    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())