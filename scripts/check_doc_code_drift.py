#!/usr/bin/env python3
"""
check_doc_code_drift.py — P1-1
Scan docs/**/*.md for oversized Python code blocks (>30 lines, >5 blocks)
that may violate CP-6 (duplicate implementation instead of referencing).
Exits 0 = clean, 1 = drift detected.
"""
import argparse
import re
import sys
from pathlib import Path

EXEMPT_PATTERNS = [
    re.compile(r"#\s*(AUTHORITATIVE:|权威实现见|see\s+\S+:)", re.IGNORECASE),
]
LINE_THRESHOLD = 30
BLOCK_COUNT_THRESHOLD = 5


def is_exempt(block_lines: list[str]) -> bool:
    """Check if block has an exemption marker in first line comment."""
    if not block_lines:
        return False
    first = block_lines[0].strip()
    for pat in EXEMPT_PATTERNS:
        if pat.search(first):
            return True
    return False


def scan_file(path: Path) -> list[tuple[int, int]]:
    """
    Return list of (start_line, num_lines) for oversized non-exempt blocks.
    """
    text = path.read_text(encoding="utf-8")
    oversize = []
    in_block = False
    block_start = 0
    block_lines = []

    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```python"):
            in_block = True
            block_start = lineno
            block_lines = []
        elif in_block:
            if line.strip() == "```":
                if len(block_lines) > LINE_THRESHOLD and not is_exempt(block_lines):
                    oversize.append((block_start, len(block_lines)))
                in_block = False
                block_lines = []
            else:
                block_lines.append(line)

    return oversize


def main():
    parser = argparse.ArgumentParser(
        description="Detect oversized Python code blocks in docs that may violate CP-6."
    )
    parser.add_argument(
        "--root",
        default="docs",
        help="Root directory to scan for .md files (default: docs)",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: docs root not found: {root}", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(root.glob("**/*.md"))
    drifted_files = []

    for md_file in md_files:
        oversize = scan_file(md_file)
        n = len(oversize)
        if n > 0:
            drifted_files.append((md_file, oversize))
            print(
                f"✗ {md_file.relative_to(root)}: {n} oversized block(s) "
                f"(>{LINE_THRESHOLD} lines, no AUTHORITATIVE marker)"
            )
            for start, lines in oversize:
                print(
                    f"  → line {start}: {lines} lines, "
                    f"consider referencing references/ instead"
                )
        else:
            print(f"✓ {md_file.relative_to(root)}: 0 oversized blocks")

    n = len(drifted_files)
    print(f"\nSUMMARY: {n} file(s) with drift")
    sys.exit(1 if n else 0)


if __name__ == "__main__":
    main()
