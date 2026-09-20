#!/usr/bin/env python3
"""Shared failure-pattern storage layer (P0-B).

Used by failure_pattern_extract.py and reflexion_retrieve.py.
Not executable directly.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOT_PATH = ROOT / "docs" / "failure-patterns.md"
WARM_PATH = ROOT / "docs" / "failure-patterns-warm.md"
COLD_PATH = ROOT / "docs" / "failure-patterns-cold.md"
HOT_LIMIT = 200
WARM_LIMIT = 500
COLD_LIMIT = 2000
SILENCE_THRESHOLD_DAYS = 30
COLD_THRESHOLD_DAYS = 90

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


# Characters that are significant to the pipe-table format. A backslash only
# escapes one of these, so ordinary backslashes in trace text pass through.
_ESCAPABLE = "\\|`"


def escape_cell(text: Any) -> str:
    """Encode a value so it survives one write/read cycle of a pipe table.

    Inverse of ``unescape_cell``. A raw ``|`` splits the row (shifting every
    later column into the wrong header), and a raw backtick flips the parser's
    backtick state, which defeats the pipe check for the rest of the row. Trace
    text reaches these cells verbatim — ``command`` is the executed shell
    command, so pipelines and quoted params are ordinary — hence escaping
    rather than assuming the payload is tame.
    """
    return str(text).replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")


def unescape_cell(text: str) -> str:
    """Decode one cell written by ``escape_cell``."""
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in _ESCAPABLE:
            out.append(text[i + 1])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _parse_table_row(line: str) -> list[str]:
    """Split a markdown table row into its inner cells.

    Pipes are honoured only outside backticks, backticks and pipes can be
    escaped, and the empty cells produced by the row's own leading/trailing
    ``|`` are dropped. Every returned cell is already unescaped, so callers see
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
    return [unescape_cell(c.strip().strip("`")) for c in cells[1:-1]]


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
