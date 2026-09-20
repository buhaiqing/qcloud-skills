#!/usr/bin/env python3
"""Shared failure-pattern storage layer (P0-B).

Used by failure_pattern_extract.py and reflexion_retrieve.py.
Not executable directly.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOT_PATH = ROOT / "docs" / "failure-patterns.md"
WARM_PATH = ROOT / "docs" / "failure-patterns-warm.md"
COLD_PATH = ROOT / "docs" / "failure-patterns-cold.md"
WARM_LIMIT = 500
COLD_LIMIT = 2000
SILENCE_THRESHOLD_DAYS = 30
COLD_THRESHOLD_DAYS = 90

# Shared thresholds (TE-4): the hot layer's line budget is declared once, in
# assets/shared/thresholds.json, and read here — not restated by every module
# that writes the store.
_THRESHOLDS_PATH = ROOT / "assets" / "shared" / "thresholds.json"
_FALLBACK_HOT_LIMIT = 200


def _reflexion_max_lines() -> int:
    """`reflexion_max_lines` from the shared thresholds, else fallback + warning.

    Never raises: an unreadable or malformed thresholds file must not stop a
    caller from storing a pattern — the store matters more than the config that
    sizes it. The fallback is the historical 200-line cap.
    """
    def fallback(reason: str) -> int:
        print(
            f"warning: {_THRESHOLDS_PATH}: {reason}; using "
            f"reflexion_max_lines={_FALLBACK_HOT_LIMIT}",
            file=sys.stderr,
        )
        return _FALLBACK_HOT_LIMIT

    try:
        raw = json.loads(_THRESHOLDS_PATH.read_text(encoding="utf-8"))["reflexion_max_lines"]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return fallback(f"cannot read ({exc})")
    if isinstance(raw, bool) or not isinstance(raw, int):
        return fallback(f"reflexion_max_lines must be an int, got {raw!r}")
    return raw


HOT_LIMIT = _reflexion_max_lines()

# ---------------------------------------------------------------------------
# Markdown table parsing (shared logic)
# ---------------------------------------------------------------------------

_CATEGORIES = ("cli_parameter", "skill_generation", "cross_skill", "runtime", "token_efficiency")

# Known section title prefixes → category (must match emit/enforce functions)
_SECTION_CAT: dict[str, str] = {
    "## 1. CLI Parameter": "cli_parameter",
    "## 2. Skill Generation": "skill_generation",
    "## 3. Cross-Skill": "cross_skill",
    "## 4. Runtime": "runtime",
    "## 5. Token Efficiency": "token_efficiency",
}


# The characters a backslash may escape, mapped to the letter that stands for
# them after that backslash. Every other backslash in trace text is a literal,
# so file paths survive. ``\n``/``\r`` are in the table because
# ``parse_existing`` reads the file line by line: a raw newline used to split
# the row, and the pattern vanished from the store while the writer still
# reported success.
_ESCAPES: dict[str, str] = {"\\": "\\", "|": "|", "`": "`", "\n": "n", "\r": "r"}
# Inverse of _ESCAPES, keyed by the character after the backslash.
_UNESCAPES: dict[str, str] = {letter: ch for ch, letter in _ESCAPES.items()}
# Characters that can legally follow a backslash: what _parse_table_row must
# keep glued together so an escaped pipe is not mistaken for a delimiter.
_ESCAPABLE = "".join(_UNESCAPES)


def escape_cell(text: Any) -> str:
    """Encode a value so it survives one write/read cycle of a pipe table.

    Inverse of ``unescape_cell``. A raw ``|`` splits the row (shifting every
    later column into the wrong header), a raw backtick flips the parser's
    backtick state, which defeats the pipe check for the rest of the row, and a
    raw newline ends the row outright. Trace text reaches these cells verbatim —
    ``command`` is the executed shell command, ``error`` is a raw exception
    string — hence escaping rather than assuming the payload is tame.

    Backslashes are doubled first, so a later replacement's own backslashes are
    never re-escaped.
    """
    out = str(text)
    for ch, letter in _ESCAPES.items():
        out = out.replace(ch, "\\" + letter)
    return out


def unescape_cell(text: str) -> str:
    """Decode one cell written by ``escape_cell``."""
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in _UNESCAPES:
            out.append(_UNESCAPES[text[i + 1]])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _decode_cell(cell: str) -> str:
    """Turn one raw table cell into the value that was written.

    One *balanced* backtick wrapper is dropped before unescaping, never after.
    ``escape_cell`` guarantees no unescaped backtick appears in the payload, so
    a cell that both starts and ends with one can only be a wrapper: the check
    cannot eat a value's own trailing backtick. Doing it in the other order (the
    previous shape, ``strip("`")`` on still-escaped text) removed that trailing
    backtick and orphaned its escape, silently rewriting ``error`` — part of the
    dedup key — so the same failure re-keyed as a new row on every scan.

    Leading/trailing whitespace is stripped, which makes the dedup key
    whitespace-normalised: ``' lead '`` and ``'lead'`` are one pattern, and
    ``merge``/``pattern_key`` strip the same way.
    """
    text = cell.strip()
    if len(text) >= 2 and text[0] == "`" and text[-1] == "`":
        text = text[1:-1]
    return unescape_cell(text).strip()


def _parse_table_row(line: str) -> list[str]:
    """Split a markdown table row into its inner cells.

    Pipes are honoured only outside backticks, backticks and pipes can be
    escaped, and the empty cells produced by the row's own leading/trailing
    ``|`` are dropped. Every returned cell is already decoded, so callers see
    the value that was written.
    """
    cells, current = [], ""
    in_backtick = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line) and line[i + 1] in _ESCAPABLE:
            current += line[i : i + 2]
            i += 2
            continue
        if ch == "`":
            in_backtick = not in_backtick
        elif ch == "|" and not in_backtick:
            cells.append(current)
            current = ""
            i += 1
            continue
        current += ch
        i += 1
    cells.append(current)
    return [_decode_cell(c) for c in cells[1:-1]]


def _parse_sources(cell: str) -> set[str]:
    """Parse the Sources cell: a JSON array, falling back to the legacy list.

    The JSON array (``["a.json","ev il b.json"]``) is the current encoding and
    round-trips spaces, pipes and backticks. Rows written before it joined bare
    filenames with spaces, so a legacy filename containing a space cannot be
    recovered — such a row reads as N separate sources and heals on its next
    write, which is why the fallback only has to be safe, not exact.
    """
    if not cell:
        return set()
    try:
        parsed = json.loads(cell)
    except ValueError:
        parsed = None
    if isinstance(parsed, list):
        return {s for s in (str(v) for v in parsed) if s.strip()}
    return {s for s in cell.replace(",", " ").split() if s and s not in ("—", "-")}


def parse_existing(path: Path) -> dict[str, dict[str, Any]]:
    """Return {(skill, command, error): {fields...}} from the existing md file."""
    patterns: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return patterns

    in_section = False
    table_headers: list[str] = []
    has_sources_col = False
    current_section_cat = ""

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_section = False
            current_section_cat = ""
            for prefix, cat in _SECTION_CAT.items():
                if line.startswith(prefix):
                    in_section = True
                    current_section_cat = cat
                    break
            table_headers = []
            has_sources_col = False
            continue

        if not in_section:
            continue

        if line.startswith("|") and "---" not in line and "Skill" in line:
            table_headers = [h.lower().replace(" ", "").replace("-", "") for h in _parse_table_row(line)]
            # Whether this table declares a Sources column at all. Rows from the
            # pre-Sources format counted merge() invocations, not traces, so their
            # count is fiction to be replaced; a row that carries an explicit "—"
            # is a modern row whose count is real but unattributable (see merge).
            has_sources_col = "sources" in table_headers
            continue

        if line.startswith("|") and "---" not in line and table_headers:
            cells = _parse_table_row(line)
            if len(cells) < 3:
                continue
            row: dict[str, Any] = {}
            for h, v in zip(table_headers, cells):
                row[h] = v

            skill = row.get("skill", "").strip()
            command = row.get("command", row.get("operation", "")).strip()
            error = row.get("errorpattern", row.get("error", "")).strip()
            if not skill:
                continue

            count_str = row.get("count", "0").strip()
            try:
                count = int(re.sub(r"\[.*\]", "", count_str).strip())
            except ValueError:
                count = 0

            key = (skill, command, error)
            patterns[key] = {
                "category": row.get("category", current_section_cat).strip() or current_section_cat,
                "skill": skill,
                "command": command,
                "error": error,
                "fix": row.get(
                    "fix",
                    row.get("resolution", row.get("rootcause", row.get("root cause", ""))),
                ).strip(),
                "count": count,
                # Distinct GCL runs that reported this pattern (see merge()).
                # "—" is the emitted placeholder for "no sources recorded".
                "sources": _parse_sources(row.get("sources", "")),
                "_sources_recorded": has_sources_col,
                "reusable": row.get("reusable", "true").strip().lower() == "true",
                "first_seen": row.get("first_seen", ""),
                "last_seen": row.get("lastseen", row.get("first_seen", "")),
                "severity": row.get("severity", "minor"),
            }
    return patterns


def load_all_layers() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load hot/warm/cold layers. Missing files return empty dicts."""
    hot = parse_existing(HOT_PATH)
    warm = parse_existing(WARM_PATH) if WARM_PATH.exists() else {}
    cold = parse_existing(COLD_PATH) if COLD_PATH.exists() else {}
    return hot, warm, cold
