#!/usr/bin/env python3
"""
check_spec_file_refs.py — P0-2
Scan docs/superpowers/specs/*.md for file references (refs/*, references/*)
pointing to .py/.yaml/.json, verify they exist on disk.
Exit 0 = all pass, 1 = any missing refs.
"""
import argparse
import re
import sys
from pathlib import Path


def extract_refs(md_text: str) -> list[tuple[str, int, str]]:
    """Return list of (ref_path, line_no) for valid tool-file refs in md text."""
    refs = []
    for lineno, line in enumerate(md_text.splitlines(), 1):
        # Skip URLs
        if re.match(r"\s*https?://", line):
            continue
        # Skip lines with placeholder patterns
        if re.search(r"<[^>]+>|\$\{[^}]+\}", line):
            continue
        # Match inline code: `refs/...` or `references/...`
        for m in re.finditer(r"`(refs/[^`]+|references/[^`]+)`", line):
            path = m.group(1)
            ext = Path(path).suffix
            if ext in (".py", ".yaml", ".json"):
                refs.append((path, lineno, line.strip()))
    return refs


def main():
    parser = argparse.ArgumentParser(description="Check spec file references exist on disk.")
    parser.add_argument(
        "--root",
        default="docs/superpowers/specs",
        help="Glob pattern root for .md files (default: docs/superpowers/specs)",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root to resolve relative paths (default: .)",
    )
    args = parser.parse_args()

    root = Path(args.root)
    project_root = Path(args.project_root).resolve()
    if not root.exists():
        print(f"ERROR: spec root not found: {root}", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(root.glob("*.md"))
    if not md_files:
        print(f"WARNING: no .md files found under {root}", file=sys.stderr)

    missing = []

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        refs = extract_refs(content)
        checked = 0
        for ref_rel, lineno, line in refs:
            checked += 1
            resolved = (project_root / ref_rel).resolve()
            if not resolved.exists():
                missing.append((str(md_file), lineno, ref_rel, line))

        status = "✓" if checked == 0 or not any(
            str(md_file) in str(m) for m in missing
        ) else "✗"
        print(f"{status} {md_file} → {checked} refs checked")

    for md_path, lineno, ref, line in missing:
        print(f"✗ {md_path}:{lineno} → `{ref}` NOT FOUND")

    n_files = len(md_files)
    n_missing = len(missing)
    print(f"\nSUMMARY: {n_files} file(s) checked, {n_missing} missing ref(s)")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
