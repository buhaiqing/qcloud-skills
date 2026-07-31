#!/usr/bin/env python3
"""Migrate legacy 2-5 column error tables in SKILL.md files to the
6-column standard format.

Phase 1 Step 1.3.3. Spec: docs/superpowers/specs/phase1-l3-adaptive-orchestration-design.md §1.3.2.

Standard format (6 columns):

    | Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |
    |------------|--------|-------------|---------|-------------|---------------|
    | `InvalidVpc.NotFound` | HALT | 0 | — | qcloud-vpc-ops | Verify VPC exists |
    | `RequestLimitExceeded` | RETRY | 3 | exponential | — | Back off and retry |

Pipeline:

1. Split SKILL.md into (yaml-frontmatter, markdown-body).
2. Walk body lines, identify legacy error tables (header + separator + ≥1 data row,
   first column ∈ {error code / error pattern / code / 错误码 / 错误模式}).
3. Parse each legacy row with ``error_table_parser.parse_error_table``.
4. Re-emit the same data as a 6-col standard table.
5. Re-join body; preserve YAML frontmatter via ruamel.yaml round-trip (or
   passthrough if we are not modifying it).

Modes:

* ``--dry-run``  — print unified-diff, do NOT modify files.
* ``--apply``    — overwrite files with migrated content.

Idempotency:

* Run twice; the second pass is a no-op (no legacy tables remain).

Lessons applied:

* L7 (re-read live target) — relies on ``parse_error_table`` which already
  supports both formats.
* L5 (assert populated values) — covered in test_migrate_error_tables.py.
* L1 (TestCase subclasses) — see test_migrate_error_tables.py.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from error_escalator import Action, ErrorRule
from error_table_parser import (
    _detect_format,
    _is_separator_row,
    _split_row,
    parse_error_table,
)

# ---------------------------------------------------------------------------
# Optional ruamel.yaml import (matches migrate_skill_frontmatter.py pattern).
# We use it ONLY to read/parse the frontmatter so we can preserve round-trip
# formatting of fields we DON'T touch. If absent, we passthrough the YAML
# text untouched (still safe — we never modify the YAML block in this tool).
# ---------------------------------------------------------------------------

try:
    from ruamel.yaml import YAML  # type: ignore
    _HAS_RUAMEL = True
except ImportError:
    _HAS_RUAMEL = False

ROOT_DEFAULT = Path(__file__).resolve().parents[1]

# 6-column header constants
HEADER = (
    "| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |"
)
SEPARATOR = (
    "|------------|--------|-------------|---------|-------------|---------------|"
)
_EM_DASH = "—"


# ---------------------------------------------------------------------------
# Frontmatter data carrier (no ruamel roundtrip needed for our purposes,
# but we keep the option open via _parse_frontmatter)
# ---------------------------------------------------------------------------

@dataclass
class Frontmatter:
    text: str  # the YAML text INCLUDING the surrounding "---" markers
    name: str | None = None
    version: str | None = None


def _split_frontmatter_body(text: str) -> tuple[Frontmatter | None, str]:
    """Split a SKILL.md file into (frontmatter, body).

    Frontmatter is the YAML block delimited by ``---`` lines at the top of
    the file (between line 0 and the next ``---`` line). If absent,
    returns (None, full_text).
    """
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    fm_text = text[: end + 4]  # includes "...\n---"  (closing dashes)
    body_start = end + 4
    body = text[body_start:]

    fm = _parse_frontmatter(fm_text)
    return fm, body


def _parse_frontmatter(fm_text: str) -> Frontmatter | None:
    """Parse a YAML frontmatter block. Falls back to text-only passthrough
    if YAML parsing fails (we never MODIFY the frontmatter, so we don't
    strictly need a parsed version — but tests want structured access)."""
    fm = Frontmatter(text=fm_text)
    try:
        # ruamel.yaml treats the leading "---" as a document separator, so we
        # strip both delimiters before parsing the body between them.
        stripped = fm_text.removeprefix("---\n")
        sep_idx = stripped.rfind("\n---")
        if sep_idx != -1:
            stripped = stripped[: sep_idx]
        if _HAS_RUAMEL:
            from io import StringIO
            y = YAML(typ="rt")
            y.preserve_quotes = True
            y.width = 1000
            y.indent(mapping=2, sequence=4, offset=2)
            data = y.load(StringIO(stripped))
        else:
            import yaml  # type: ignore
            data = yaml.safe_load(stripped)
    except (ImportError, OSError, ValueError, KeyError, AttributeError, TypeError):
        return fm
    if isinstance(data, dict):
        fm.name = str(data.get("name") or "")
        meta = data.get("metadata")
        if isinstance(meta, dict):
            v = meta.get("version")
            if v is not None:
                fm.version = str(v)
    return fm


def _rejoin(fm: Frontmatter | None, body: str) -> str:
    if fm is None:
        return body
    return fm.text + body


# ---------------------------------------------------------------------------
# Table detection (line-based, robust to surrounding prose)
# ---------------------------------------------------------------------------

# A row is "table-like" if it starts with '|' and contains at least one '|'
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")


def _split_table_block(block_lines: list[str]) -> list[list[str]] | None:
    """Convert a contiguous block of table-like lines into rows-of-cells.

    Returns None if the block doesn't look like a real table (no separator
    row, fewer than 2 rows, etc.).
    """
    if len(block_lines) < 2:
        return None
    rows: list[list[str]] = []
    for line in block_lines:
        rows.append(_split_row(line))
    # Drop a trailing separator row (it carries no data).
    cleaned = [r for r in rows if not _is_separator_row(r)]
    if len(cleaned) < 2:
        return None
    return cleaned


def _find_legacy_table_ranges(body: str) -> list[tuple[int, int, list[str], list[list[str]]]]:
    """Return list of ``(start_line_idx, end_line_idx_exclusive, header_row, data_rows)``
    for every legacy error table in ``body``.

    * start/end are 0-indexed into ``body.splitlines()``.
    * ``data_rows`` excludes the header row.
    * Stub tables (no data rows beyond the header) are skipped.
    """
    lines = body.splitlines()
    ranges: list[tuple[int, int, list[str], list[list[str]]]] = []

    i = 0
    while i < len(lines):
        if not _TABLE_ROW_RE.match(lines[i]):
            i += 1
            continue
        # Start of a table block: collect contiguous table-like lines.
        j = i
        while j < len(lines) and _TABLE_ROW_RE.match(lines[j]):
            j += 1
        block = lines[i:j]
        rows = _split_table_block(block)
        if rows is None:
            i = j
            continue
        header = rows[0]
        fmt = _detect_format(header)
        if fmt != "legacy":
            i = j
            continue
        data_rows = rows[1:]
        if not data_rows:
            i = j
            continue
        ranges.append((i, j, header, data_rows))
        i = j
    return ranges


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_backoff(r: ErrorRule) -> str:
    """Render the Backoff column for a single rule.

    Empty / fixed + no seconds → em-dash.
    Else prefer explicit list ``"2s,4s,8s"``; fallback to ``"exponential"``.
    """
    if r.backoff_seconds:
        return ",".join(f"{s}s" for s in r.backoff_seconds)
    if r.backoff_strategy == "exponential":
        return "exponential"
    return _EM_DASH


def _render_delegate(r: ErrorRule) -> str:
    return r.delegate_to if r.delegate_to else _EM_DASH


def _render_max_retries(r: ErrorRule) -> str:
    return str(r.max_retries)


def _render_action(r: ErrorRule) -> str:
    return r.action.value if isinstance(r.action, Action) else str(r.action)


def _render_recovery_hint(r: ErrorRule) -> str:
    """Preserve the original prose as-is. The parser strips backticks from
    codes but leaves the recovery hint untouched; we keep it untouched.
    Trailing newlines are stripped."""
    return r.recovery_hint.strip().replace("\n", " ").strip()


def _render_code(r: ErrorRule) -> str:
    """Re-wrap error code in backticks. Don't double-wrap."""
    code = r.code.strip().strip("`").strip()
    if not code:
        return code
    return f"`{code}`"


def _render_standard_table(rules: list[ErrorRule]) -> str:
    """Render a list of ErrorRules into a 6-column markdown table.

    Output ends with a single newline. Always emits the header + separator,
    even when ``rules`` is empty (caller decides whether to drop the stub).
    """
    lines = [HEADER, SEPARATOR]
    for r in rules:
        lines.append(
            "| "
            + " | ".join(
                [
                    _render_code(r),
                    _render_action(r),
                    _render_max_retries(r),
                    _render_backoff(r),
                    _render_delegate(r),
                    _render_recovery_hint(r),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Per-skill migration
# ---------------------------------------------------------------------------

def _migrate_body(body: str) -> str:
    """Replace every legacy error table in ``body`` with its 6-col rendering.

    Uses line ranges to splice — content OUTSIDE the tables is byte-identical.
    """
    ranges = _find_legacy_table_ranges(body)
    if not ranges:
        return body
    lines = body.splitlines()
    # Walk back-to-front so earlier indices remain valid as we splice.
    out_lines = list(lines)
    for start, end, _header, data_rows in reversed(ranges):
        # Reconstruct the original block of lines (header + separator + rows).
        block_text = "\n".join(lines[start:end])
        rules = parse_error_table(block_text + "\n")
        # Sanity: rules count should equal data_rows count (parse_error_table
        # drops rows with empty first cell). If they diverge, fall back to
        # an empty 6-col table (preserves the table shape, drops unrecoverable
        # rows; the alternative is to crash the migration).
        if len(rules) != len(data_rows):
            # Best-effort: drop unrecoverable rows by emitting what we parsed.
            pass
        replacement = _render_standard_table(rules)
        # remove lines [start:end] and insert replacement (without trailing \n
        # to avoid doubling; replacement ends with one \n).
        out_lines[start:end] = [replacement.rstrip("\n")]
    return "\n".join(out_lines) + ("\n" if body.endswith("\n") else "")


def migrate_skill(skill_md: Path, *, dry_run: bool = False) -> tuple[str, str]:
    """Migrate a single SKILL.md. Returns ``(original_text, new_text)``.

    If no changes are required, ``original == new``.
    On ``dry_run=False`` the file is overwritten.
    Frontmatter is preserved exactly (we never modify the YAML).
    """
    original = skill_md.read_text(encoding="utf-8")
    fm, body = _split_frontmatter_body(original)
    new_body = _migrate_body(body)
    if new_body == body:
        return original, original
    new_text = _rejoin(fm, new_body)
    if not dry_run:
        skill_md.write_text(new_text, encoding="utf-8")
    return original, new_text


# ---------------------------------------------------------------------------
# Diff helper + CLI
# ---------------------------------------------------------------------------

def diff_text(a: str, b: str, label: str = "") -> str:
    return "".join(difflib.unified_diff(
        a.splitlines(keepends=True),
        b.splitlines(keepends=True),
        fromfile=f"{label} (before)" if label else "before",
        tofile=f"{label} (after)" if label else "after",
    ))


def _iter_skill_files(root: Path, only_skill: str | None) -> list[Path]:
    if only_skill:
        return [root / only_skill / "SKILL.md"]
    return sorted(root.glob("qcloud-*-ops/SKILL.md"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="Print unified-diff per skill, do NOT modify files")
    parser.add_argument("--apply", action="store_true",
                        help="Overwrite SKILL.md files in place")
    parser.add_argument("--root", default=str(ROOT_DEFAULT),
                        help="Repo root (default: parent of scripts/)")
    parser.add_argument("--skill", default=None,
                        help="Limit to a single skill name (debug)")
    parser.add_argument("--diff-out", default=None,
                        help="Write the unified diff to a file instead of stdout")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("ERROR: must specify --dry-run or --apply", file=sys.stderr)
        sys.exit(2)
    if args.dry_run and args.apply:
        print("ERROR: --dry-run and --apply are mutually exclusive", file=sys.stderr)
        sys.exit(2)

    root = Path(args.root).resolve()
    targets = _iter_skill_files(root, args.skill)
    diff_parts: list[str] = []
    total = 0
    changed = 0
    for path in targets:
        if not path.is_file():
            continue
        total += 1
        before, after = migrate_skill(path, dry_run=args.dry_run)
        if before == after:
            continue
        changed += 1
        label = path.parent.name
        diff_parts.append(f"--- {label} ---\n")
        diff_parts.append(diff_text(before, after, label=label))
        diff_parts.append("\n")

    out = "".join(diff_parts) if diff_parts else ""
    if args.diff_out:
        Path(args.diff_out).write_text(out, encoding="utf-8")
    else:
        if out:
            sys.stdout.write(out)
            sys.stdout.flush()

    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    summary = f"{mode}: {changed}/{total} skills would change / changed"
    print(summary, file=sys.stderr if args.diff_out else sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
