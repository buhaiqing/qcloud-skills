#!/usr/bin/env python3
"""cadl_lint — enforce the canonical CADL hook on every `qcloud-*-ops/SKILL.md`.

Usage:
  python3 scripts/cadl_lint.py                    # lint all skills (exit 1 on missing)
  python3 scripts/cadl_lint.py --fix              # idempotently inject hook into missing skills
  python3 scripts/cadl_lint.py --json            # machine-readable report
  python3 scripts/cadl_lint.py --skill qcloud-cvm-ops   # lint one skill

Contract authority: root `AGENTS.md` §"复利资产沉淀机制 (CADL, P0)". Detailed
background and rationale live in `docs/cadl-spec.md`.

The hook line is a single canonical byte sequence defined by the AGENTS.md contract
and produced by `qcloud-skill-generator/references/qcloud-skill-template.md` (tail).
Do NOT change CANONICAL_HOOK without updating the AGENTS.md contract first —
the linter is the runtime enforcement; the contract is the source of truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# The hook phrase. Full-width punctuation and brackets — change in AGENTS.md first.
CANONICAL_HOOK = (
    "> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」"
    "复盘并沉淀可复用资产。"
)

# The meta-skill is itself a skill of skills; it ships with the hook too.
META_SKILL_DIR = "qcloud-skill-generator"

ROOT = Path(__file__).resolve().parents[1]


def _last_nonblank_line(text: str) -> str:
    """Return the last non-blank line in `text`, or '' if all blank."""
    for line in reversed(text.splitlines()):
        if line.strip():
            return line
    return ""


def lint_one(path: Path) -> tuple[str, bool, str]:
    """Return (skill_name, ok, message)."""
    skill = path.parent.name
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (skill, False, "file not found")
    last = _last_nonblank_line(text)
    if last == CANONICAL_HOOK:
        return (skill, True, "ok")
    if not last:
        return (skill, False, "file is empty or all-blank")
    return (skill, False, f"last_nonblank_line={last!r}")


def fix_one(path: Path) -> bool:
    """Idempotently inject the canonical hook as the last non-blank line.

    Returns True if the file was modified, False if it was already compliant
    (or could not be read).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    if _last_nonblank_line(text) == CANONICAL_HOOK:
        return False  # already compliant
    # Make sure file ends with a newline before we append.
    if text and not text.endswith("\n"):
        text += "\n"
    # Add a single blank-line separator between prior content and the hook,
    # unless the file already ends with a blank line.
    if text.endswith("\n\n"):
        separator = ""
    elif text.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    path.write_text(text + separator + CANONICAL_HOOK + "\n", encoding="utf-8")
    return True


def iter_skill_files(root: Path = ROOT) -> list[Path]:
    """Return every SKILL.md under `qcloud-*-ops/` plus the meta-skill.

    Pattern: any first-level dir whose name starts with `qcloud-` and contains a
    `SKILL.md`, OR the canonical meta-skill dir `qcloud-skill-generator/SKILL.md`.
    """
    found: list[Path] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("qcloud-"):
            continue
        skill_md = entry / "SKILL.md"
        if skill_md.is_file():
            found.append(skill_md)
    return found


def run_lint(paths: list[Path], fix: bool = False) -> tuple[int, list[dict]]:
    """Lint (and optionally fix) every path. Returns (exit_code, report)."""
    report: list[dict] = []
    failures = 0
    for path in paths:
        skill, ok, msg = lint_one(path)
        try:
            rel = str(path.relative_to(ROOT))
        except ValueError:
            rel = str(path)
        entry = {"skill": skill, "path": rel, "ok": ok, "msg": msg}
        if not ok:
            if fix:
                if fix_one(path):
                    entry["fixed"] = True
                    entry["ok"] = True
                    entry["msg"] = "fixed"
                else:
                    failures += 1
            else:
                failures += 1
        report.append(entry)
    return (1 if failures else 0, report)


def _print_report(report: list[dict]) -> None:
    if not report:
        print("(no SKILL.md found)")
        return
    name_w = max(len(row["skill"]) for row in report)
    for row in report:
        status = "OK  " if row["ok"] else "FAIL"
        flag = " (fixed)" if row.get("fixed") else ""
        print(f"  {status}  {row['skill']:<{name_w}}  {row['msg']}{flag}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Idempotently inject the canonical hook into non-compliant skills.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON to stdout.",
    )
    parser.add_argument(
        "--skill",
        default=None,
        help="Lint exactly this skill (matches `<skill>/SKILL.md`).",
    )
    args = parser.parse_args(argv)

    if args.skill:
        target = ROOT / args.skill / "SKILL.md"
        if not target.is_file():
            print(f"not found: {target}", file=sys.stderr)
            return 2
        paths = [target]
    else:
        paths = iter_skill_files(ROOT)

    exit_code, report = run_lint(paths, fix=args.fix)
    if args.json:
        print(json.dumps(
            {"ok": exit_code == 0, "fix": args.fix, "skills": report},
            ensure_ascii=False,
            indent=2,
        ))
    else:
        failed = sum(1 for row in report if not row["ok"])
        verb = "FIX  REPORT" if args.fix else "LINT REPORT"
        print(f"CADL {verb} — {len(report)} skill(s) scanned, {failed} failing")
        _print_report(report)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
