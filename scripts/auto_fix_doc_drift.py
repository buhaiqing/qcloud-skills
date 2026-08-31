#!/usr/bin/env python3
"""
auto_fix_doc_drift.py — P0-2
Auto-fix oversized Python code blocks in docs by replacing them with
"权威实现见 <path>" references.

Modes:
  --dry-run (default)  : show unified diffs, no file writes
  --apply              : actually write changes (requires --confirm)
  --target <file>      : only process single file
  --self-test          : run internal self-test
"""
import argparse
import difflib
import re
import sys
import tempfile
from pathlib import Path

LINE_THRESHOLD = 30
IMPORT_RE = re.compile(r"^\s*(from\s+[\w.]+\s+import\s+|import\s+[\w.]+)")
REL_IMPORT_RE = re.compile(r"^\s*(from\s+\.)|(\.\.)")
CONFIRM_TOKEN = "yes-i-really-mean-it"


def is_exempt(block_lines: list[str]) -> bool:
    if not block_lines:
        return False
    for pat in [
        re.compile(r"#\s*(AUTHORITATIVE:|权威实现见|see\s+\S+:)", re.IGNORECASE),
    ]:
        if pat.search(block_lines[0].strip()):
            return True
    return False


def extract_imports(block_lines: list[str]) -> list[str]:
    return [ln.strip() for ln in block_lines if IMPORT_RE.match(ln.strip())]


def infer_authority(block_lines: list[str]) -> str | None:
    """
    Infer authoritative path from block imports.
    Returns None if no path can be inferred.
    """
    imports = extract_imports(block_lines)
    if not imports:
        return None

    for imp in imports:
        # references.<module> or from references import <module>
        m = re.match(r"(?:from\s+)?references\.(\w+)", imp.replace("import ", ""))
        if m:
            return f"references/{m.group(1)}.py"

        # from . import x or from .. import x
        if REL_IMPORT_RE.match(imp):
            return "same-file-relative-import"

    return None


def scan_blocks(path: Path):
    """Replicate detection logic from check_doc_code_drift.py."""
    text = path.read_text(encoding="utf-8")
    blocks = []
    in_block = False
    block_start = 0
    block_lines = []
    block_raw = []

    for lineno, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```python"):
            in_block = True
            block_start = lineno
            block_lines = []
            block_raw = []
        elif in_block:
            if line.strip() == "```":
                if len(block_lines) > LINE_THRESHOLD and not is_exempt(block_lines):
                    authority = infer_authority(block_lines)
                    blocks.append({
                        "start": block_start,
                        "lines": len(block_lines),
                        "authority": authority,
                        "content": block_raw,
                    })
                in_block = False
                block_lines = []
                block_raw = []
            else:
                block_lines.append(line)
                block_raw.append(line)

    return blocks


def build_patch_lines(block: dict) -> list[str]:
    """Return replacement lines for the block."""
    authority = block["authority"]
    if authority:
        ref = f"> 权威实现见 {authority}"
    else:
        ref = "> 权威实现见 <无可推断路径，需手工修复>"
    return [ref, ""]


def compute_unified_diff(path: Path, blocks: list[dict]) -> str:
    """Build a unified diff string for the file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    fixable_ranges = [(b["start"], b["start"] + b["lines"] + 1)
                      for b in blocks if b["authority"] is not None]
    fixable_set = set()
    for s, e in fixable_ranges:
        for i in range(s, e + 1):
            fixable_set.add(i)

    new_lines = []
    for lineno, line in enumerate(lines, 1):
        if lineno in fixable_set:
            for b in blocks:
                if b["start"] == lineno and b["authority"] is not None:
                    new_lines.extend(build_patch_lines(b))
                    break
        else:
            new_lines.append(line)

    new_text = "\n".join(new_lines) + "\n"

    if text == new_text:
        return ""

    diff = difflib.unified_diff(
        lines,
        new_text.splitlines(),
        fromfile=str(path),
        tofile=str(path),
        lineterm="",
    )
    return "\n".join(diff)


def process_file(path: Path, dry_run: bool) -> tuple[int, int, str]:
    """Returns (total_blocks, fixable_blocks, diff_text)."""
    blocks = scan_blocks(path)
    fixable = [b for b in blocks if b["authority"] is not None]
    diff = ""
    if fixable:
        diff = compute_unified_diff(path, blocks)
    return len(blocks), len(fixable), diff


def self_test() -> bool:
    """Verify core logic with temp files."""
    content1 = """\
# Header

Some text.

```python
from references.gcl_spec import GCLSpec
from references.toolgrounding import validate

def foo():
    pass
""" + "\n" + ("    line\n" * 35) + """\
```

More text.
"""
    content2 = """\
# Header

```python
""" + "\n".join(["    x = 1"] * 35) + """

```

More text.
"""

    with tempfile.TemporaryDirectory() as td:
        f1 = Path(td) / "f1.md"
        f2 = Path(td) / "f2.md"
        f1.write_text(content1)
        f2.write_text(content2)

        _, fix1, diff1 = process_file(f1, dry_run=True)
        _, fix2, diff2 = process_file(f2, dry_run=True)

        assert fix1 >= 1, f"expected fixable block, got {fix1}"
        assert "references/gcl_spec.py" in diff1, "expected authority in diff"
        assert fix2 == 0, f"expected 0 fixable, got {fix2}"
        assert "权威实现见" not in diff2, "unfixable block should not appear in diff"

    print("self-test: all assertions passed")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Auto-fix oversized Python code blocks in docs."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show diffs without writing (default)"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply changes to files"
    )
    parser.add_argument(
        "--confirm", default="", help="Required token to enable --apply"
    )
    parser.add_argument(
        "--target", type=Path, default=None, help="Process only this file"
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run self-test and exit"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show non-fixable blocks too"
    )
    args = parser.parse_args()

    if args.self_test:
        ok = self_test()
        sys.exit(0 if ok else 1)

    dry_run = not args.apply

    if args.apply and args.confirm != CONFIRM_TOKEN:
        try:
            stdin_token = sys.stdin.readline().strip()
        except EOFError:
            stdin_token = ""
        if stdin_token != "yes":
            print(
                "ERROR: --apply requires --confirm yes-i-really-mean-it\n"
                "  or pipe 'yes' via stdin:  yes | python3 auto_fix_doc_drift.py --apply",
                file=sys.stderr,
            )
            sys.exit(1)

    root = Path("docs")
    if not root.exists():
        print(f"ERROR: docs root not found: {root}", file=sys.stderr)
        sys.exit(1)

    files = [args.target] if args.target else sorted(root.glob("**/*.md"))

    total_files = 0
    total_fixable = 0

    for f in files:
        blocks = scan_blocks(f)
        fixable = [b for b in blocks if b["authority"] is not None]
        total_blocks = len(blocks)
        if total_blocks == 0:
            continue
        total_files += 1
        total_fixable += len(fixable)
        diff = ""
        if fixable:
            diff = compute_unified_diff(f, blocks)
        if diff:
            print(f"\n{'=' * 60}")
            print(f"File: {f}")
            print(f"Blocks: {total_blocks}, Fixable: {len(fixable)}")
            print(diff)
            if not dry_run:
                new_text = "\n".join(rebuild_file_content(f)) + "\n"
                f.write_text(new_text, encoding="utf-8")
                print(f"[APPLIED] {f}")
        elif args.verbose and total_blocks > 0:
            print(f"\n{'=' * 60}")
            print(f"File: {f}  (oversized but not auto-fixable)")
            for b in blocks:
                reason = b["authority"] or "无可推断路径 (无 references.* import)"
                print(f"  line {b['start']}: {b['lines']} lines → {reason}")

    print(f"\nSUMMARY: {total_files} file(s) scanned, {total_fixable} block(s) fixable")
    if dry_run:
        print("(dry-run — no files written)")
    sys.exit(0)


def rebuild_file_content(path: Path) -> list[str]:
    """Rebuild file content with fixable blocks replaced."""
    blocks = scan_blocks(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    fixable_ranges = [
        (b["start"], b["start"] + b["lines"] + 1)
        for b in blocks if b["authority"] is not None
    ]
    fixable_set = set()
    for s, e in fixable_ranges:
        for i in range(s, e + 1):
            fixable_set.add(i)

    new_lines = []
    for lineno, line in enumerate(lines, 1):
        if lineno in fixable_set:
            for b in blocks:
                if b["start"] == lineno and b["authority"] is not None:
                    new_lines.extend(build_patch_lines(b))
                    break
        else:
            new_lines.append(line)
    return new_lines


if __name__ == "__main__":
    main()
