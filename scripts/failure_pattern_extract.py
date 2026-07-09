#!/usr/bin/env python3
"""Extract failure_pattern from GCL traces and update docs/failure-patterns.md.

Reads ``audit-results/gcl-trace-*.json`` (or ``--input`` paths),
extracts each trace's ``failure_pattern`` field, deduplicates against
``docs/failure-patterns.md`` (match by skill + command + error),
increments count on duplicates, appends new patterns, and enforces the
200-line cap by pruning count < 3.

Usage:
  python3 scripts/failure_pattern_extract.py              # update in-place
  python3 scripts/failure_pattern_extract.py --dry-run    # print proposed changes
  python3 scripts/failure_pattern_extract.py --since-hours 168  # last week's traces only

Exit codes:
  0  success
  1  no traces / no patterns found
  2  parse error in failure-patterns.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PATTERNS_FILE = ROOT / "docs" / "failure-patterns.md"
AUDIT_DIR = ROOT / "audit-results"


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
    # Remove leading/trailing pipes (first/last empty cells) and surrounding backticks
    return [c.strip().strip("`") for c in cells[1:-1] if c.strip()]


CATEGORIES = ("cli_parameter", "skill_generation", "cross_skill", "runtime", "token_efficiency")
MAX_LINES = 200

# ---------------------------------------------------------------------------
# Markdown table parsing
# ---------------------------------------------------------------------------

def parse_existing(path: Path) -> dict[str, dict[str, Any]]:
    """Return {(skill, command, error): {fields...}} from the existing file."""
    patterns: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return patterns

    in_section = False
    table_headers: list[str] = []
    current_section_cat = ""

    # Known section title prefixes → category (must match enforce_line_cap / section_map)
    _SECTION_CAT: dict[str, str] = {
        "## 1. CLI Parameter": "cli_parameter",
        "## 2. Skill Generation": "skill_generation",
        "## 3. Cross-Skill": "cross_skill",
        "## 4. Runtime": "runtime",
        "## 5. Token Efficiency": "token_efficiency",
    }

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
                "fix": row.get("fix", row.get("resolution", row.get("rootcause", row.get("root cause", "")))).strip(),
                "count": count,
                "reusable": row.get("reusable", "true").strip().lower() == "true",
                "first_seen": row.get("first_seen", datetime.now().strftime("%Y-%m")),
            }
    return patterns


def emit_table(patterns: dict[str, dict[str, Any]], sections: dict[str, list[str]]) -> str:
    """Rebuild the markdown table sections from in-memory patterns."""

    def table_rows(category_filter: str) -> list[str]:
        rows = []
        for key, p in sorted(patterns.items(), key=lambda x: (-x[1]["count"], x[0][0])):
            if p["category"] != category_filter:
                continue
            skill = p["skill"] or "—"
            command = p["command"] or "—"
            error = p["error"] or "—"
            fix = p.get("fix", "—") or "—"
            count = p.get("count", 0)
            rows.append(
                f"| `{skill}` | `{command}` | {error} | {fix} | {count} |"
            )
        return rows

    lines = []
    for section_title, headers in sections.items():
        lines.append(f"\n{section_title}")
        lines.append("")
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in table_rows(section_title.split("|")[1].strip()):
            lines.append(row)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Trace processing
# ---------------------------------------------------------------------------

def collect_traces(root: Path, inputs: list[str] | None, since_hours: int | None) -> list[Path]:
    if inputs:
        out: list[Path] = []
        for pattern in inputs:
            out.extend(sorted(root.glob(pattern) if "*" in pattern else [Path(pattern)]))
        return [p for p in out if p.is_file()]

    audit_dir = root / "audit-results"
    if not audit_dir.is_dir():
        return []
    paths = sorted(audit_dir.glob("gcl-trace-*.json"))
    if since_hours is None:
        return paths
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    return [
        p for p in paths
        if datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) >= cutoff
    ]


def extract_failure_patterns(traces: list[Path]) -> list[dict[str, Any]]:
    """Read all traces, return list of failure_pattern dicts found."""
    found: list[dict[str, Any]] = []
    for p in traces:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARN: skip {p.name}: {e}", file=sys.stderr)
            continue

        # top-level
        fp = data.get("failure_pattern")
        if fp:
            fp["_source"] = p.name
            found.append(fp)

        # per-iteration
        for i, iteration in enumerate(data.get("iterations") or []):
            fp = iteration.get("failure_pattern")
            if fp:
                fp["_source"] = f"{p.name}#iter-{i+1}"
                found.append(fp)
    return found


def merge(
    existing: dict[str, dict[str, Any]],
    new: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Merge new patterns into existing. Increment count on duplicate keys."""
    for p in new:
        raw_skill = p.get("skill") or ""
        command = (p.get("command") or "").strip()
        error = (p.get("error") or "").strip()
        if not raw_skill.strip():
            continue
        skill = raw_skill.strip()
        key = (skill, command, error)
        if key in existing:
            existing[key]["count"] = existing[key].get("count", 0) + 1
        else:
            existing[key] = {
                "category": p.get("category", "runtime"),
                "skill": skill,
                "command": command,
                "error": error,
                "fix": p.get("fix", "—") or "—",
                "count": 1,
                "reusable": p.get("reusable", True),
                "first_seen": datetime.now().strftime("%Y-%m"),
            }
    return existing


def prune_low_frequency(patterns: dict[str, dict[str, Any]], min_count: int = 3) -> None:
    """Remove patterns with count < min_count (in-place)."""
    dead = [k for k, v in patterns.items() if v.get("count", 0) < min_count]
    for k in dead:
        del patterns[k]


def enforce_line_cap(patterns: dict[str, dict[str, Any]]) -> list[str]:
    """Rebuild failure-patterns.md content, enforcing ~200 line cap."""
    now = datetime.now().strftime("%Y-%m-%d")

    sections = {
        "## 1. CLI Parameter Errors": [
            "Skill", "Command", "Error Pattern", "Fix", "Count"
        ],
        "## 2. Skill Generation Issues": [
            "Skill", "Command", "Error Pattern", "Fix", "Count"
        ],
        "## 3. Cross-Skill Composition Failures": [
            "Skill", "Command", "Error Pattern", "Resolution", "Count"
        ],
        "## 4. Runtime Execution Patterns": [
            "Skill", "Operation", "Error Pattern", "Root Cause", "Count"
        ],
        "## 5. Token Efficiency Violations": [
            "Skill", "Command", "Error Pattern", "Fix", "Count"
        ],
    }

    # Split patterns into sections by category
    by_section: dict[str, dict[str, dict[str, Any]]] = {s: {} for s in sections}
    section_map = {
        "cli_parameter": "## 1. CLI Parameter Errors",
        "skill_generation": "## 2. Skill Generation Issues",
        "cross_skill": "## 3. Cross-Skill Composition Failures",
        "runtime": "## 4. Runtime Execution Patterns",
        "token_efficiency": "## 5. Token Efficiency Violations",
    }
    for key, p in patterns.items():
        cat = p.get("category", "runtime")
        section = section_map.get(cat, "## 4. Runtime Execution Patterns")
        by_section[section][key] = p

    lines: list[str] = [
        "# Failure Patterns — Reflexion Memory",
        "",
        "> **Purpose**: Structured failure memory extracted from GCL traces and Self-Review records.",
        "> Agents can optionally load this file during Pre-flight to 预防 (prevent) known errors.",
        f"> **Updated**: {now} ({sum(p['count'] for p in patterns.values())} total hits across all patterns).",
        "> **Token budget**: ≤ 200 lines. When exceeded, prune patterns with count < 3.",
        "",
    ]

    for section_title, headers in sections.items():
        table_patterns = by_section[section_title]
        if not table_patterns:
            continue
        lines.append(section_title)
        lines.append("")
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for key, p in sorted(table_patterns.items(), key=lambda x: (-x[1]["count"], x[0][0])):
            skill = p["skill"] or "—"
            command = p.get("command", p.get("operation", "—")) or "—"
            error = p.get("error", p.get("root cause", "—")) or "—"
            fix = p.get("fix", p.get("resolution", "—")) or "—"
            count = p.get("count", 0)
            lines.append(f"| `{skill}` | `{command}` | {error} | {fix} | {count} |")

    # Usage guidelines (always kept)
    lines.extend([
        "",
        "## Usage Guidelines",
        "",
        "### For Agents (Pre-flight)",
        "```",
        "# Optional: Load failure patterns before executing a skill",
        "# 1. Read this file (lazy-load, ~130 lines)",
        "# 2. Filter patterns by current skill name",
        "# 3. Inject relevant patterns into Generator context as prevention hints",
        "```",
        "",
        "### For Self-Review (Round 3: Lessons Learned)",
        "```",
        "# After completing R1 + R2:",
        "# 1. Extract new failure patterns from this session",
        "# 2. Check if pattern already exists (dedup by skill + command + error)",
        "# 3. If new: append to appropriate section with count=1",
        "# 4. If existing: increment count",
        "# 5. If total lines > 200: prune patterns with count < 3",
        "```",
        "",
        "### For GCL Traces",
        "```json",
        '# When a GCL iteration fails, record the failure pattern:',
        '{',
        '  "failure_pattern": {',
        '    "category": "cli_parameter" | "skill_generation" | "cross_skill" | "runtime" | "token_efficiency",',
        '    "skill": "qcloud-xxx-ops",',
        '    "command": "tccli xxx ...",',
        '    "error": "InvalidParameter: ...",',
        '    "fix": "Use JSON array format for array params",',
        '    "reusable": true',
        '  }',
        "}",
        "```",
    ])

    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", nargs="*", help="Trace file(s) or glob under --root")
    parser.add_argument(
        "--since-hours", type=int, default=None,
        help="Only traces modified within N hours (default: all traces)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print proposed changes without writing"
    )
    parser.add_argument(
        "--min-count", type=int, default=3,
        help="Prune patterns with count below this threshold (default: 3)"
    )
    args = parser.parse_args()

    # Load existing
    existing = parse_existing(PATTERNS_FILE)
    existing_count = len(existing)

    # Collect and parse traces
    trace_paths = collect_traces(args.root, args.input, args.since_hours)
    if not trace_paths:
        print("No gcl-trace files found.", file=sys.stderr)
        return 1

    new_patterns = extract_failure_patterns(trace_paths)
    if not new_patterns:
        print("No failure_pattern fields found in traces.", file=sys.stderr)
        return 1

    # Merge
    merged = merge(existing.copy(), new_patterns)
    new_count = len(merged) - existing_count

    # Prune low-frequency
    prune_low_frequency(merged, min_count=args.min_count)
    pruned = existing_count + new_count - len(merged)

    # Build new content
    lines = enforce_line_cap(merged)
    if len(lines) > MAX_LINES + 10:
        print(
            f"WARN: output {len(lines)} lines exceeds cap ({MAX_LINES}). "
            f"Consider raising --min-count or archiving older patterns.",
            file=sys.stderr
        )

    # Summary
    total_hits = sum(p["count"] for p in merged.values())
    print(
        f"Traces scanned:     {len(trace_paths)}",
        f"New patterns:        {new_count}",
        f"Count increments:    {len(merged) - existing_count - new_count + (existing_count - len([k for k in existing if k in merged]))}",
        f"Pruned (count<{args.min_count}): {pruned}",
        f"Total patterns:      {len(merged)}",
        f"Total hits:          {total_hits}",
        f"Output lines:        {len(lines)}",
        sep="\n"
    )

    if args.dry_run:
        print("\n--- PROPOSED CONTENT ---")
        print("\n".join(lines))
        return 0

    PATTERNS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nUpdated: {PATTERNS_FILE.relative_to(args.root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
