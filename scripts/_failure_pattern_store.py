#!/usr/bin/env python3
"""Shared failure-pattern storage layer (P0-B).

Used by failure_pattern_extract.py and reflexion_retrieve.py.
Not executable directly.
"""
from __future__ import annotations

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


def _parse_table_row(line: str) -> list[str]:
    """Split a markdown table row by pipes, respecting backtick-enclosed content."""
    cells, current = [], ""
    in_backtick = False
    for ch in line:
        if ch == "`":
            in_backtick = not in_backtick
            current += ch
        elif ch == "|" and not in_backtick:
            cells.append(current.strip())
            current = ""
        else:
            current += ch
    cells.append(current.strip())
    return [c.strip().strip("`") for c in cells[1:-1] if c.strip()]


def parse_existing(path: Path) -> dict[str, dict[str, Any]]:
    """Return {(skill, command, error): {fields...}} from the existing md file."""
    patterns: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return patterns

    in_section = False
    table_headers: list[str] = []
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
            continue

        if not in_section:
            continue

        if line.startswith("|") and "---" not in line and "Skill" in line:
            table_headers = [h.lower().replace(" ", "").replace("-", "") for h in _parse_table_row(line)]
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
