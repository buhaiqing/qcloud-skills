#!/usr/bin/env python3
"""
auto_fix_doc_drift.py — P0-2
Auto-fix oversized Python code blocks in docs by replacing them with
"权威实现见 <path>" references.

Modes:
  --dry-run (default)  : show unified diffs, no file writes
  --apply              : apply HIGH-confidence fixes only
  --apply-all          : apply all fixable blocks (requires --confirm)
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
CLASS_RE = re.compile(r"^@(\w+)\s*$|^(?:class\s+)(\w+)")
FUNC_RE = re.compile(r"^def\s+(\w+)\s*\(")
HEADER_RE_1 = re.compile(r"^#\s*[Mm]odule:\s*(.+)")
HEADER_RE_2 = re.compile(r"^#\s*[Ff]ile:\s*(.+)")
HEADER_RE_3 = re.compile(r"^#\s*---+s*(.+?)\s*---+")
HEADER_RE_4 = re.compile(r"^#\s*(scripts/[\w_/]+\.py|references/[\w_/]+\.py|\w[\w/]*\.py)")
CONFIRM_TOKEN = "yes-i-really-mean-it"

# Search roots for class/func name lookups
SEARCH_ROOTS = ["scripts", "references"]


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


def _extract_class_names(block_lines: list[str]) -> list[str]:
    """Extract top-level class names from a code block."""
    names = []
    for ln in block_lines:
        stripped = ln.strip()
        m = CLASS_RE.match(stripped)
        if m:
            name = m.group(1) or m.group(2)
            if name and name not in ("unittest", "TestCase"):
                names.append(name)
    return names


def _extract_func_names(block_lines: list[str]) -> list[str]:
    """Extract top-level (non-dunder, non-private) function names."""
    names = []
    for ln in block_lines:
        stripped = ln.strip()
        m = FUNC_RE.match(stripped)
        if m:
            name = m.group(1)
            if not name.startswith("_") and name not in ("main",):
                names.append(name)
    return names
    return []


def _find_file_by_name(name: str) -> str | None:
    """Search SEARCH_ROOTS for a .py file defining `name` as class or function.
    Returns the path relative to repo root, or None.
    """
    # ponytail: linear scan — fine for small script/references dirs
    for root_name in SEARCH_ROOTS:
        root = Path(root_name)
        if not root.is_dir():
            continue
        for py_file in root.glob("**/*.py"):
            try:
                text = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            # check class or def at top level
            if re.search(rf"(?:^class\s+{re.escape(name)}\b|^def\s+{re.escape(name)}\s*\()",
                         text, re.MULTILINE):
                return str(py_file)
    return None


def _infer_from_header(block_lines: list[str]) -> str | None:
    """Pattern 1: block header comment indicating file path."""
    if not block_lines:
        return None
    first = block_lines[0].strip()
    for pat in (HEADER_RE_1, HEADER_RE_2, HEADER_RE_3, HEADER_RE_4):
        m = pat.match(first)
        if m:
            path = m.group(1).strip()
            # normalize: strip # prefix, leading/trailing whitespace
            path = re.sub(r"^#+\s*", "", path).strip()
            if path:
                return path
    return None


def _infer_from_classname(block_lines: list[str]) -> str | None:
    """Pattern 2: class name in block → grep SEARCH_ROOTS for definition."""
    for name in _extract_class_names(block_lines):
        found = _find_file_by_name(name)
        if found:
            return found
    return None


def _infer_from_funcname(block_lines: list[str]) -> str | None:
    """Pattern 3: top-level function name → grep SEARCH_ROOTS."""
    for name in _extract_func_names(block_lines):
        found = _find_file_by_name(name)
        if found:
            return found
    return None


def _infer_from_sibling_spec(file_path: Path, block_lines: list[str]) -> str | None:
    """Pattern 4: for docs/superpowers/specs/X.md, look for sibling X.py."""
    if file_path is None:
        return None
    parts = file_path.parts
    if "specs" in parts:
        idx = parts.index("specs")
        stem = Path(*parts[idx + 1:]).stem  # e.g. "success-patterns-design"
        for candidate in [
            f"scripts/{stem}.py",
            f"references/{stem}.py",
            stem + ".py",
        ]:
            if Path(candidate).exists():
                return candidate
    return None


def _infer_from_imports(block_lines: list[str]) -> str | None:
    """Pattern 5: import path fallback — import name matches a .py in SEARCH_ROOTS."""
    imports = extract_imports(block_lines)
    for imp in imports:
        # strip "from " or "import " prefix
        module = re.sub(r"^(?:from\s+|import\s+)", "", imp).strip().split(".")[0]
        for root_name in SEARCH_ROOTS:
            root = Path(root_name)
            if not root.is_dir():
                continue
            candidate = root / f"{module}.py"
            if candidate.exists():
                return str(candidate)
    return None


def infer_authority(block_lines: list[str], file_path: Path | None = None) -> tuple[str | None, str]:
    """
    Infer authoritative path from block content.
    Returns (path, confidence) where confidence is "HIGH"/"MEDIUM"/"LOW"/"NONE".
    """
    # P1: header comment
    authority = _infer_from_header(block_lines)
    if authority:
        return authority, "HIGH"

    # P2: class name
    authority = _infer_from_classname(block_lines)
    if authority:
        return authority, "HIGH"

    # P3: top-level function name
    authority = _infer_from_funcname(block_lines)
    if authority:
        return authority, "HIGH"

    # P4: sibling spec/py
    authority = _infer_from_sibling_spec(file_path, block_lines)
    if authority:
        return authority, "MEDIUM"

    # P5: import fallback
    authority = _infer_from_imports(block_lines)
    if authority:
        return authority, "LOW"

    return None, "NONE"


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
                    authority, confidence = infer_authority(block_lines, path)
                    blocks.append({
                        "start": block_start,
                        "lines": len(block_lines),
                        "authority": authority,
                        "confidence": confidence,
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
    # content1: header pattern → HIGH confidence
    content1 = """\
# Header

Some text.

```python
# scripts/foo_bar.py
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
        assert "scripts/foo_bar.py" in diff1, f"expected authority in diff, got: {diff1[:300]}"
        assert fix2 == 0, f"expected 0 fixable, got {fix2}"
        assert "权威实现见" not in diff2, "unfixable block should not appear in diff"

    # content3: class-name matching — AutonomyPolicy is defined in scripts/autonomy_policy.py
    content3 = """\
# Header

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class AutonomyPolicy:
    level: int
    description: str

@dataclass
class AutonomyRule:
    condition: str
    action: str
""" + "\n" + ("    line\n" * 35) + """\
```

More text.
"""

    with tempfile.TemporaryDirectory() as td:
        f3 = Path(td) / "f3.md"
        f3.write_text(content3)
        _, fix3, diff3 = process_file(f3, dry_run=True)
        assert fix3 >= 1, f"expected fixable block via class name, got {fix3}"
        assert "scripts/autonomy_policy.py" in diff3, \
            f"expected scripts/autonomy_policy.py in diff, got: {diff3[:300]}"

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
        "--apply", action="store_true", help="Apply HIGH-confidence changes only"
    )
    parser.add_argument(
        "--apply-all", action="store_true", help="Apply all fixable blocks (requires --confirm)"
    )
    parser.add_argument(
        "--confirm", default="", help="Required token to enable --apply or --apply-all"
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

    dry_run = not (args.apply or args.apply_all)
    apply_all = args.apply_all

    if (args.apply or args.apply_all) and args.confirm != CONFIRM_TOKEN:
        try:
            stdin_token = sys.stdin.readline().strip()
        except EOFError:
            stdin_token = ""
        if stdin_token != "yes":
            print(
                "ERROR: --apply/--apply-all requires --confirm yes-i-really-mean-it\n"
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
    total_high = 0

    for f in files:
        blocks = scan_blocks(f)
        fixable = [b for b in blocks if b["authority"] is not None]
        high_conf = [b for b in fixable if b["confidence"] == "HIGH"]
        med_low = [b for b in fixable if b["confidence"] in ("MEDIUM", "LOW")]
        total_blocks = len(blocks)
        if total_blocks == 0:
            continue
        total_files += 1
        total_fixable += len(fixable)
        total_high += len(high_conf)
        diff = ""
        if fixable:
            diff = compute_unified_diff(f, blocks)
        if diff:
            print(f"\n{'=' * 60}")
            print(f"File: {f}")
            print(f"Blocks: {total_blocks}, Fixable: {len(fixable)}"
                  f" (HIGH={len(high_conf)}, MEDIUM/LOW={len(med_low)})")
            for b in blocks:
                if b["authority"] is not None:
                    conf_tag = f"[{b['confidence']}]"
                    reason = b["authority"]
                    print(f"  {conf_tag} line {b['start']}: {b['lines']} lines → {reason}")
            print(diff)
            if not dry_run:
                # --apply: only HIGH; --apply-all: all fixable
                blocks_to_fix = high_conf if (args.apply and not apply_all) else fixable
                new_text = "\n".join(rebuild_file_content(f, blocks_to_fix)) + "\n"
                f.write_text(new_text, encoding="utf-8")
                print(f"[APPLIED {len(blocks_to_fix)} block(s)] {f}")
        elif args.verbose and total_blocks > 0:
            print(f"\n{'=' * 60}")
            print(f"File: {f}  (oversized but not auto-fixable)")
            for b in blocks:
                reason = b["authority"] or "无可推断路径"
                print(f"  [{b.get('confidence','NONE')}] line {b['start']}: {b['lines']} lines → {reason}")

    print(f"\nSUMMARY: {total_files} file(s) scanned, {total_fixable} block(s) fixable (HIGH={total_high})")
    if dry_run:
        print("(dry-run — no files written)")
    sys.exit(0)


def rebuild_file_content(path: Path, blocks_to_fix: list[dict] | None = None) -> list[str]:
    """Rebuild file content with fixable blocks replaced.

    If blocks_to_fix is None, uses all blocks with authority (backward compat).
    """
    blocks = scan_blocks(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if blocks_to_fix is None:
        blocks_to_fix = [b for b in blocks if b["authority"] is not None]
    fixable_ranges = [
        (b["start"], b["start"] + b["lines"] + 1)
        for b in blocks_to_fix
    ]
    fixable_set = set()
    for s, e in fixable_ranges:
        for i in range(s, e + 1):
            fixable_set.add(i)

    new_lines = []
    for lineno, line in enumerate(lines, 1):
        if lineno in fixable_set:
            for b in blocks_to_fix:
                if b["start"] == lineno:
                    new_lines.extend(build_patch_lines(b))
                    break
        else:
            new_lines.append(line)
    return new_lines


if __name__ == "__main__":
    main()
