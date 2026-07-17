#!/usr/bin/env python3
"""Reflexion memory write-side — store failure patterns with dedup and line limit.

Usage:
  from reflexion_store import store_failure_pattern
  store_failure_pattern("qcloud-cvm-ops", "TerminateInstances", "MissingParameter", "Fix text")
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Import from failure_pattern_extract for parsing existing patterns
from failure_pattern_extract import parse_existing, enforce_line_cap

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE_PATH = ROOT / "docs" / "failure-patterns.md"
MAX_LINES = 200


def normalize_reflexion_key(
    category: str, skill: str, command: str, error: str
) -> tuple[str, str, str, str]:
    """Normalize a failure pattern into the cross-system dedup key (fixes L5).

    Shared shape with ``qcloud-copilot/copilot/quality/reflexion.py`` so the
    same failure converging from copilot scratch and GCL trace dedups instead
    of double-writing. Command is normalized to its verb/operation token
    (args dropped) and lowercased; error is lowercased and whitespace-collapsed.
    """
    norm_cmd = command.strip().lower().split("\n")[0].split(" ")[0]
    norm_err = " ".join(error.strip().lower().split())
    return (category.strip().lower(), skill.strip().lower(), norm_cmd, norm_err)


def parse_existing_safe(path: Path) -> dict[str, dict[str, Any]]:
    """Safely parse existing patterns with 4-tuple keys, returning {} on error.

    Re-keys the 3-tuple (skill, command, error) dict from the shared store
    layer into the 4-tuple (category, skill, command_norm, error) shape used
    by ``_make_key`` so same-pattern reads/writes dedup identically.
    """
    try:
        raw = parse_existing(path)
        patterns: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for p in raw.values():
            p["command"] = p.get("command", "") or p.get("operation", "")
            p["operation"] = p.get("operation", "") or p.get("command", "")
            category = p.get("category", "runtime")
            key = normalize_reflexion_key(category, p["skill"], p["command"], p["error"])
            patterns[key] = p
        return patterns
    except Exception:
        return {}


def _make_key(
    category: str, skill: str, command: str, error: str
) -> tuple[str, str, str, str]:
    """Create a unique key for deduplication (4-tuple, matches copilot side)."""
    return normalize_reflexion_key(category, skill, command, error)


def _prune_by_count(patterns: dict[str, dict[str, Any]], max_patterns: int) -> None:
    """Remove lowest-count patterns in-place until under limit.
    
    Sorts by count ascending and keeps top max_patterns.
    """
    if len(patterns) <= max_patterns:
        return

    # Sort by count ascending, remove lowest count patterns
    sorted_items = sorted(patterns.items(), key=lambda x: x[1].get("count", 0))
    to_remove = len(patterns) - max_patterns

    for i in range(to_remove):
        del patterns[sorted_items[i][0]]


def store_failure_pattern(
    skill: str,
    command: str,
    error: str,
    resolution: str,
    category: str = "runtime",
    path: Path | None = None,
) -> bool:
    """Store a failure pattern with dedup and line limit enforcement.

    Args:
        skill: Skill name (e.g., "qcloud-cvm-ops").
        command: Command or operation that failed.
        error: Error pattern or message.
        resolution: Fix or resolution text.
        category: Pattern category (cli_parameter, skill_generation, cross_skill, runtime, token_efficiency).
        path: Override path to failure-patterns.md (default: docs/failure-patterns.md).

    Returns:
        True if pattern was stored/updated successfully, False otherwise.

    Behavior:
        1. Deduplicates by (skill + command + error) tuple.
        2. If pattern exists: increments count, updates timestamp.
        3. If pattern is new: appends with count=1.
        4. Enforces ≤200 lines limit by pruning lowest-count patterns if needed.
    """
    # Validate required fields
    if not skill or not skill.strip():
        return False
    if not error or not error.strip():
        return False

    store_path = path or DEFAULT_STORE_PATH

    # Ensure parent directory exists
    store_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing patterns
    patterns = parse_existing_safe(store_path)

    # Create key for dedup (4-tuple so copilot/GCL sinks dedup identically)
    key = _make_key(category, skill, command, error)

    now = datetime.now().strftime("%Y-%m")

    if key in patterns:
        # Upsert: increment count, keep original fix and first_seen
        patterns[key]["count"] = patterns[key].get("count", 0) + 1
        # Note: we don't update fix or first_seen on upsert
    else:
        # New pattern
        patterns[key] = {
            "category": category,
            "skill": skill.strip(),
            "command": command.strip(),
            "error": error.strip(),
            "fix": resolution.strip() if resolution else "—",
            "count": 1,
            "reusable": True,
            "first_seen": now,
        }

    # Enforce line limit by pruning if needed
    # Each pattern takes ~1 line in table, plus header/footer
    # Estimate max patterns as (MAX_LINES - 50) for headers/footers
    max_patterns = MAX_LINES - 50
    if len(patterns) > max_patterns:
        _prune_by_count(patterns, max_patterns)

    # Rebuild and write file
    lines = enforce_line_cap(patterns)

    # Final safety check: if still over limit, prune more aggressively
    while len(lines) > MAX_LINES and patterns:
        # Remove the lowest count pattern
        sorted_items = sorted(patterns.items(), key=lambda x: x[1].get("count", 0))
        del patterns[sorted_items[0][0]]
        lines = enforce_line_cap(patterns)

    try:
        store_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def main() -> int:
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Store a failure pattern")
    parser.add_argument("--skill", required=True, help="Skill name")
    parser.add_argument("--command", default="", help="Command")
    parser.add_argument("--error", required=True, help="Error pattern")
    parser.add_argument("--resolution", default="", help="Fix/resolution")
    parser.add_argument("--category", default="runtime", help="Category")
    parser.add_argument("--path", type=Path, default=None, help="Override file path")

    args = parser.parse_args()

    result = store_failure_pattern(
        skill=args.skill,
        command=args.command,
        error=args.error,
        resolution=args.resolution,
        category=args.category,
        path=args.path,
    )

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
