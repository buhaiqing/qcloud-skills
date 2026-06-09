#!/usr/bin/env python3
"""Validate SKILL.md YAML frontmatter across qcloud-* skill directories.

Usage:
  python3 scripts/validate_skills_frontmatter.py [--root PATH]

Checks presence of required keys (supports multiline ``>-`` blocks).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CLI_APPLICABILITY = {"dual-path", "cli-first", "cli-only", "sdk-only"}
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
LEGACY_NO_METADATA = {"qcloud-finops-ops"}
OPTIONAL_CLI = {"qcloud-skill-generator"}


def extract_frontmatter(path: Path) -> tuple[str | None, list[str]]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER.match(text)
    if not m:
        return None, [f"{path}: missing YAML frontmatter"]
    return m.group(1), []


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


def validate_skill(path: Path) -> list[str]:
    block, errs = extract_frontmatter(path)
    if block is None:
        return errs
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
    elif not cli and name not in LEGACY_NO_METADATA and name not in OPTIONAL_CLI:
        errs.append(f"{path}: missing cli_applicability")

    skill_name = name or ""
    if skill_name in LEGACY_NO_METADATA:
        return errs

    version = nested_metadata_field(block, "version")
    updated = nested_metadata_field(block, "last_updated")
    if not version:
        errs.append(f"{path}: missing metadata.version")
    if not updated:
        errs.append(f"{path}: missing metadata.last_updated")

    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    skills = sorted(args.root.glob("qcloud-*/SKILL.md"))
    all_errs: list[str] = []
    for skill in skills:
        all_errs.extend(validate_skill(skill))

    if all_errs:
        print(f"FAIL: {len(all_errs)} error(s) in {len(skills)} skills\n")
        for e in all_errs:
            print(f"  - {e}")
        return 1
    print(f"OK: {len(skills)} SKILL.md frontmatter files validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
