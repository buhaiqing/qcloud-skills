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
from failure_pattern_extract import enforce_line_cap, parse_existing

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
    except (ImportError, OSError, ValueError, KeyError, AttributeError, TypeError):
        return {}


def _make_key(
    category: str, skill: str, command: str, error: str
) -> tuple[str, str, str, str]:
    """Create a unique key for deduplication (4-tuple, matches copilot side)."""
    return normalize_reflexion_key(category, skill, command, error)


def _prune_by_count(
    patterns: dict[str, dict[str, Any]], max_patterns: int
) -> list[tuple[str, dict[str, Any]]]:
    """Remove lowest-count patterns in-place until under limit.

    Returns the evicted (key, pattern) pairs in ascending count order
    so the caller can demote them to warmer storage instead of losing them.
    """
    if len(patterns) <= max_patterns:
        return []
    sorted_items = sorted(patterns.items(), key=lambda x: x[1].get("count", 0))
    to_remove = len(patterns) - max_patterns
    evicted = sorted_items[:to_remove]
    for key, _ in evicted:
        del patterns[key]
    return evicted


# ---------------------------------------------------------------------------
# Layer demotion (hot → warm → cold)
# ---------------------------------------------------------------------------
_HOT_LIMIT = 200
_WARM_LIMIT = 500
_HOT_PATH = ROOT / "docs" / "failure-patterns.md"
_WARM_PATH = ROOT / "docs" / "failure-patterns-warm.md"
_COLD_PATH = ROOT / "docs" / "failure-patterns-cold.md"


def _demote_patterns(
    evicted: list[tuple[str, dict[str, Any]]], dry_run: bool = False
) -> int:
    """Write evicted patterns to warmer storage layers.

    Priority: warm (≤500 lines) → cold (≤2000 lines).  Demoted patterns
    retain their count so the cold layer preserves recency signal.

    Returns the number of patterns successfully demoted.
    """
    demoted = 0
    for key, pattern in evicted:
        # Try warm first
        ok = _append_to_layer(pattern, _WARM_PATH, _WARM_LIMIT)
        if ok:
            demoted += 1
            continue
        # Warm full — try cold
        ok = _append_to_layer(pattern, _COLD_PATH, 2000)
        if ok:
            demoted += 1
            continue
        # Both layers full — silently discard (budget exhausted; not a fatal error)
    return demoted


def _append_to_layer(
    pattern: dict[str, Any], path: Path, max_lines: int
) -> bool:
    """Append one pattern to a layer file, enforcing its line limit.

    Returns True if the pattern was written; False if the layer is at capacity.
    Demotes lowest-count existing patterns to make room.

    ``max_lines`` must be handed to ``enforce_line_cap`` as well as used for the
    capacity maths: the cap defaults to the 200-line HOT limit, so a warm/cold
    layer rendered without it was silently re-capped to 200 lines and lost the
    rows it had just demoted there.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = parse_existing_safe(path) if path.exists() else {}
    if len(existing) >= max_lines - 10:  # leave room for headers
        # Demote lowest-count patterns to make space
        excess = len(existing) - (max_lines - 20)
        if excess > 0:
            sorted_existing = sorted(existing.items(), key=lambda x: x[1].get("count", 0))
            for k, _ in sorted_existing[:excess]:
                del existing[k]
    # Append or update
    key = (pattern.get("category", ""), pattern.get("skill", ""),
           pattern.get("command", ""), pattern.get("error", ""))
    key = (key[0].strip().lower(), key[1].strip().lower(),
           key[2].strip().lower(), " ".join(key[3].strip().lower().split()))
    existing[key] = pattern
    try:
        lines = enforce_line_cap(existing, max_lines=max_lines)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


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

    One of the writers of docs/failure-patterns.md; the full list lives in
    docs/reflexion-memory.md §10 and is machine-checked by
    reflexion_store_test.TestTheWriterListIsComplete. It is one of the two with
    no trace to attribute a hit to, so it records no ``sources`` and its
    increments land in the unattributed remainder that merge() carries over
    (see failure_pattern_extract.merge).
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

    # Enforce line limit by pruning if needed.
    # P1-2: evicted patterns are demoted to warm/cold layers instead of lost.
    max_patterns = MAX_LINES - 50
    if len(patterns) > max_patterns:
        evicted = _prune_by_count(patterns, max_patterns)
        _demote_patterns(evicted)

    # Rebuild and write file
    lines = enforce_line_cap(patterns)

    # Final safety: if still over hot limit despite pruning (should not happen
    # but guard in case enforce_line_cap behaves differently), demote excess.
    while len(lines) > MAX_LINES and patterns:
        sorted_items = sorted(patterns.items(), key=lambda x: x[1].get("count", 0))
        evicted = [(sorted_items[0][0], sorted_items[0][1])]
        del patterns[sorted_items[0][0]]
        _demote_patterns(evicted)
        lines = enforce_line_cap(patterns)

    try:
        store_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def get_cross_skill_patterns(error_category: str | None = None) -> dict[str, dict[str, Any]]:
    """Retrieve failure patterns optionally filtered by error_category.

    Args:
        error_category: If provided, only return patterns matching this
            error_category. If None, return all patterns.

    Returns:
        Dict of pattern dicts keyed by (category, skill, command_norm, error) tuple.
    """
    patterns = parse_existing_safe(DEFAULT_STORE_PATH)
    if error_category is None:
        return patterns

    filtered: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for key, p in patterns.items():
        if p.get("error_category") == error_category:
            filtered[key] = p
    return filtered

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
