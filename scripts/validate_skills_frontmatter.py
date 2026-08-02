#!/usr/bin/env python3
"""Validate SKILL.md YAML frontmatter across qcloud-* skill directories.

Usage:
  python3 scripts/validate_skills_frontmatter.py [--root PATH] [--skip-missing-required]
  python3 scripts/validate_skills_frontmatter.py --git-diff BASE_REF [--root PATH]

Checks presence of required keys (supports multiline ``>-`` blocks and
nested-under-metadata fields). ``--git-diff`` runs the version/last_updated
bump gate for SKILL.md files changed since BASE_REF.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

CLI_APPLICABILITY = {"dual-path", "cli-first", "cli-only", "sdk-only"}
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
OPTIONAL_CLI = {"qcloud-skill-generator"}


def extract_frontmatter(path: Path) -> tuple[str | None, list[str]]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER.match(text)
    if not m:
        return None, [f"{path}: missing YAML frontmatter"]
    return m.group(1), []


def _frontmatter_block(text: str) -> str | None:
    m = FRONTMATTER.match(text)
    return m.group(1) if m else None


def has_key(block: str, key: str) -> bool:
    return bool(re.search(rf"^{re.escape(key)}:\s", block, re.MULTILINE))


def nested_metadata_field(block: str, field: str) -> str | None:
    if not has_key(block, "metadata"):
        return None
    m = re.search(rf"^\s+{re.escape(field)}:\s*[\"']?([^\"'\n]+)", block, re.MULTILINE)
    return m.group(1).strip('"').strip("'") if m else None


def top_level_field(block: str, field: str) -> str | None:
    m = re.search(rf"^{re.escape(field)}:\s*[\"']?([^\"'\n]+)", block, re.MULTILINE)
    return m.group(1).strip('"').strip("'") if m else None


def extract_fields(block: str) -> tuple[str | None, str | None]:
    """Return (version, last_updated) using the metadata.*-first, top-level fallback."""
    return (
        nested_metadata_field(block, "version") or top_level_field(block, "version"),
        nested_metadata_field(block, "last_updated") or top_level_field(block, "last_updated"),
    )


def field_value_nonempty(block: str, key: str) -> bool:
    """True if ``key`` is present with a non-empty value (inline or block scalar)."""
    m = re.search(rf"^\s*{re.escape(key)}:\s*(.*)$", block, re.MULTILINE)
    if not m:
        return False
    inline = m.group(1).strip()
    if inline.startswith(('"', "'")):
        return bool(inline.strip('"').strip("'"))
    if inline.startswith((">-", "|-", ">", "|")):
        rest = block[m.end() :]
        return bool(re.match(r"(?s)\n[ \t]+\S", rest))
    return bool(inline)


def validate_skill(path: Path, skip_missing_required: bool = False) -> tuple[list[str], list[str]]:
    """Validate one SKILL.md; returns (errors, warnings)."""
    block, errs = extract_frontmatter(path)
    if block is None:
        return errs, []
    warnings: list[str] = []
    name = top_level_field(block, "name")
    if not name or not name.startswith("qcloud-"):
        errs.append(f"{path}: missing or invalid 'name' (must start with qcloud-)")

    if not has_key(block, "description"):
        errs.append(f"{path}: missing 'description'")

    if not has_key(block, "compatibility"):
        errs.append(f"{path}: missing 'compatibility'")

    cli = nested_metadata_field(block, "cli_applicability") or top_level_field(
        block, "cli_applicability"
    )
    if cli and cli not in CLI_APPLICABILITY:
        errs.append(f"{path}: invalid cli_applicability '{cli}'")
    elif not cli and name not in OPTIONAL_CLI:
        errs.append(f"{path}: missing cli_applicability")

    exempt = name in OPTIONAL_CLI
    if not exempt:
        if not field_value_nonempty(block, "cli_support_evidence"):
            msg = f"{path}: missing or empty cli_support_evidence"
            (warnings if skip_missing_required else errs).append(msg)
        if not field_value_nonempty(block, "environment"):
            msg = f"{path}: missing or empty environment"
            (warnings if skip_missing_required else errs).append(msg)

    if cli == "dual-path" and not exempt:
        cli_usage = path.parent / "references" / "cli-usage.md"
        if not cli_usage.is_file():
            errs.append(
                f"{path}: cli_applicability 'dual-path' requires references/cli-usage.md "
                f"(missing at {cli_usage})"
            )

    version, updated = extract_fields(block)
    if not version:
        errs.append(f"{path}: missing metadata.version")
    if not updated:
        errs.append(f"{path}: missing metadata.last_updated")

    return errs, warnings


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str] | None:
    """Run a git command in ``root``; return None if git is unavailable."""
    try:
        return subprocess.run(args, cwd=root, capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError):
        return None


def changed_skill_paths(root: Path, base_ref: str) -> list[str]:
    """Top-level SKILL.md paths (relative to root) changed between base_ref and working tree."""
    names: set[str] = set()
    any_ok = False
    for args in (
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        ["git", "diff", "--name-only", base_ref],
    ):
        proc = _run_git(root, args)
        if proc is None or proc.returncode != 0:
            continue
        any_ok = True
        names.update(line.strip() for line in proc.stdout.splitlines() if line.strip())
    if not any_ok:
        raise RuntimeError(f"git diff unavailable for base ref {base_ref!r}")
    return sorted(p for p in names if re.match(r"qcloud-[^/]+/SKILL\.md$", p))


def _base_content(root: Path, base_ref: str, rel: str) -> str | None:
    proc = _run_git(root, ["git", "show", f"{base_ref}:{rel}"])
    if proc is None or proc.returncode != 0:
        return None
    return proc.stdout


def validate_git_diff(root: Path, base_ref: str) -> tuple[list[str], list[str]]:
    """Version/last_updated bump gate. Returns (errors, notes)."""
    try:
        changed = changed_skill_paths(root, base_ref)
    except RuntimeError as exc:
        return [], [f"git unavailable for base ref {base_ref!r}: {exc} — skipping (L10)"]
    if not changed:
        return [], [f"no SKILL.md files changed between {base_ref} and working tree"]
    errors: list[str] = []
    notes: list[str] = []
    for rel in changed:
        path = root / rel
        if not path.is_file():
            continue
        base_text = _base_content(root, base_ref, rel)
        if base_text is None:
            notes.append(f"{rel}: new file (not in {base_ref}) — no bump required")
            continue
        base_block = _frontmatter_block(base_text)
        base_version, base_updated = extract_fields(base_block) if base_block else (None, None)
        if base_version is None and base_updated is None:
            notes.append(f"{rel}: base has no metadata — no bump required")
            continue
        work_text = path.read_text(encoding="utf-8")
        work_block = _frontmatter_block(work_text)
        work_version, work_updated = extract_fields(work_block) if work_block else (None, None)
        if not work_version or not work_updated:
            errors.append(f"{rel}: missing metadata.version/last_updated (git-diff bump check)")
            continue
        if work_version == base_version or work_updated == base_updated:
            errors.append(
                f"{rel}: metadata.version/last_updated not bumped since {base_ref} "
                f"(base version={base_version or '-'}, last_updated={base_updated or '-'}; "
                f"work version={work_version}, last_updated={work_updated})"
            )
    return errors, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--git-diff",
        metavar="BASE_REF",
        default=None,
        help=(
            "Version-bump gate: compare SKILL.md files changed between BASE_REF and the "
            "working tree, and fail when metadata.version/last_updated were not both bumped. "
            "Files absent from BASE_REF (new files) are skipped. Runs the bump check only."
        ),
    )
    parser.add_argument(
        "--skip-missing-required",
        action="store_true",
        help=(
            "Escape hatch: downgrade missing/empty cli_support_evidence and environment "
            "failures to warnings. Does NOT weaken the dual-path -> references/cli-usage.md "
            "cross-check or the --git-diff version-bump gate (both stay hard failures)."
        ),
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.git_diff:
        errs, notes = validate_git_diff(root, args.git_diff)
        for note in notes:
            print(f"  - {note}")
        for e in errs:
            print(f"  - {e}")
        if errs:
            print(f"FAIL: {len(errs)} SKILL.md file(s) missing version/last_updated bumps")
            return 1
        print(f"OK: version-bump gate clean against {args.git_diff}")
        return 0

    skills = sorted(root.glob("qcloud-*/SKILL.md"))
    all_errs: list[str] = []
    all_warns: list[str] = []
    for skill in skills:
        errs, warns = validate_skill(skill, skip_missing_required=args.skip_missing_required)
        all_errs.extend(errs)
        all_warns.extend(warns)

    if all_warns:
        print(f"WARNING: {len(all_warns)} warning(s)\n")
        for w in all_warns:
            print(f"  - {w}")

    if all_errs:
        print(f"FAIL: {len(all_errs)} error(s) in {len(skills)} skills\n")
        for e in all_errs:
            print(f"  - {e}")
        return 1
    print(f"OK: {len(skills)} SKILL.md frontmatter files validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
