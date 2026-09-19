#!/usr/bin/env python3
"""Extract failure_pattern from GCL traces and update docs/failure-patterns.md.

Reads ``audit-results/gcl-trace-*.json`` (or ``--input`` paths),
extracts each trace's ``failure_pattern`` field, deduplicates against
``docs/failure-patterns.md`` (match by skill + command + error), counts the
distinct traces that reported each pattern, and enforces the 200-line cap by
dropping the least-recurring rows.

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
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from _failure_pattern_store import (
    COLD_LIMIT,
    COLD_PATH,
    HOT_LIMIT,
    HOT_PATH,
    SILENCE_THRESHOLD_DAYS,
    WARM_LIMIT,
    WARM_PATH,
    load_all_layers,
    parse_existing,
)

ROOT = Path(__file__).resolve().parents[1]
PATTERNS_FILE = ROOT / "docs" / "failure-patterns.md"
AUDIT_DIR = ROOT / "audit-results"

CATEGORIES = ("cli_parameter", "skill_generation", "cross_skill", "runtime", "token_efficiency")
MAX_LINES = 200

# Error category taxonomy for cross-skill aggregation
ERROR_CATEGORIES = (
    "rate_limit",
    "auth_failure",
    "network_timeout",
    "quota_exceeded",
    "internal_error",
    "not_found",
    "invalid_param",
    "unknown",
)


def derive_error_category(error: str, category: str) -> str:
    """Derive error_category from error message and failure category.

    Maps raw error strings to ERROR_CATEGORIES taxonomy for cross-skill
    aggregation while preserving 'unknown' as the backward-compatible default.
    """
    if not error:
        return "unknown"

    error_lower = error.lower()

    # Rate limit patterns
    if any(kw in error_lower for kw in ("requestlimit", "ratelimit", "throttle", "too many requests")):
        return "rate_limit"

    # Auth failure patterns
    if any(kw in error_lower for kw in ("authfailure", "auth failure", "unauthorized", "access denied", "invalid credentials")):
        return "auth_failure"

    # Network timeout patterns
    if any(kw in error_lower for kw in ("timeout", "connection", "network", "econnrefused", "etimedout")):
        return "network_timeout"

    # Quota exceeded patterns
    if any(kw in error_lower for kw in ("quota", "limit exceeded", "exceed", "insufficient quota")):
        return "quota_exceeded"

    # Internal error patterns
    if any(kw in error_lower for kw in ("internalerror", "internal error", "server error", "service unavailable")):
        return "internal_error"

    # Not found patterns
    if any(kw in error_lower for kw in ("notfound", "not found", "does not exist", "resource not found")):
        return "not_found"

    # Invalid param patterns (CLI-level)
    if any(kw in error_lower for kw in ("invalidparameter", "missingparameter", "invalid param", "missing param", "illegal parameter")):
        return "invalid_param"

    return "unknown"

# ---------------------------------------------------------------------------
# Markdown table emit
# ---------------------------------------------------------------------------

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
    cutoff = datetime.now(UTC) - timedelta(hours=since_hours)
    return [
        p for p in paths
        if datetime.fromtimestamp(p.stat().st_mtime, tz=UTC) >= cutoff
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

        # final status block (canonical location per gcl_runner.py)
        final_block = data.get("final") or {}
        if isinstance(final_block, dict):
            fp = final_block.get("failure_pattern")
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


def pattern_key(p: dict[str, Any]) -> tuple[str, str, str] | None:
    """Dedup key (skill, command, error) for a raw failure_pattern.

    Returns None when ``skill`` is empty — such a pattern has no home in the
    store and every consumer (merge, the R3 gate, prune exemptions) drops it.
    """
    skill = (p.get("skill") or "").strip()
    if not skill:
        return None
    return (skill, (p.get("command") or "").strip(), (p.get("error") or "").strip())


def source_of(p: dict[str, Any]) -> str:
    """The GCL run (trace file) that observed a raw failure_pattern.

    ``_source`` is a trace filename, optionally suffixed ``#iter-N`` by
    ``extract_failure_patterns``. The suffix is dropped: one GCL run is one
    observation, however many of its iterations reported the same failure.
    Without that, a single run could manufacture a count on its own.
    """
    return (p.get("_source") or "").strip().split("#", 1)[0]


def merge(
    existing: dict[str, dict[str, Any]],
    new: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Merge new patterns into existing.

    ``count`` is the number of DISTINCT trace sources (``_source``) that have
    observed the pattern — never the number of times this function ran. A
    re-scan of the same corpus is therefore a no-op, while a new GCL run
    reporting the same failure adds exactly 1. Callers that pass patterns
    without a ``_source`` (programmatic use) keep the legacy per-observation
    increment.
    """
    for p in new:
        key = pattern_key(p)
        if key is None:
            continue
        src = source_of(p)
        now = datetime.now().strftime("%Y-%m")
        entry = existing.get(key)
        if entry is None:
            existing[key] = {
                "category": p.get("category", "runtime"),
                "skill": key[0],
                "command": key[1],
                "error": key[2],
                "fix": p.get("fix", "—") or "—",
                "count": 1,
                "sources": {src} if src else set(),
                "reusable": p.get("reusable", True),
                "first_seen": now,
                "last_seen": now,  # P0-C
                "severity": p.get("severity", "minor"),
            }
            continue
        sources = entry.setdefault("sources", set())
        if src:
            sources.add(src)
        entry["count"] = len(sources) if sources else entry.get("count", 0) + 1
        entry["last_seen"] = now  # P0-C: update on every hit
    return existing


def prune_low_frequency(
    patterns: dict[str, dict[str, Any]],
    min_count: int = 3,
    exclude: Iterable[tuple[str, str, str]] = (),
) -> None:
    """Remove patterns with count < min_count (in-place).

    ``exclude`` lists keys observed in the current run; they are never pruned,
    however low their count. A pattern seen now has demonstrably NOT stopped
    recurring, and retiring it in the same transaction that records it makes
    ``count`` unable to ever reach ``min_count`` — see docs/reflexion-memory.md §10.
    """
    keep = set(exclude)
    dead = [
        k for k, v in patterns.items()
        if v.get("count", 0) < min_count and k not in keep
    ]
    for k in dead:
        del patterns[k]


# ---------------------------------------------------------------------------
# P0-B: Layered storage (hot/warm/cold)
# ---------------------------------------------------------------------------

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _days_between(older: str, newer: str) -> int:
    """Days from older to newer. Returns 0 if either is empty/invalid."""
    if not older or not newer:
        return 0
    try:
        d1 = datetime.strptime(older[:10], "%Y-%m-%d")
        d2 = datetime.strptime(newer[:10], "%Y-%m-%d")
        return max(0, (d2 - d1).days)
    except ValueError:
        return 0


def merge_failure_batch(
    new: list[dict[str, Any]],
    hot: dict[str, dict[str, Any]],
    warm: dict[str, dict[str, Any]],
    cold: dict[str, dict[str, Any]],
) -> tuple[dict, dict, dict]:
    """Merge new failure patterns into hot/warm/cold layers.

    Algorithm (mirrors success_pattern_mine.py merge_batch):
      1. Substitution: same key → count++, last_seen=today
      2. Warm revive: key in warm + gap ≤ 30 days → move back to hot
      3. Silence hot: over HOT_LIMIT → oldest last_seen to warm
      4. Silence warm: over WARM_LIMIT → oldest last_seen to cold
      5. Cold cap: over COLD_LIMIT → prune lowest count
    """
    for p in new:
        raw_skill = p.get("skill") or ""
        command = (p.get("command") or "").strip()
        error = (p.get("error") or "").strip()
        if not raw_skill.strip():
            continue
        skill = raw_skill.strip()
        key = (skill, command, error)
        now = _today()
        severity = p.get("severity", "minor")

        if key in hot:
            # Substitution: increment count
            hot[key]["count"] = hot[key].get("count", 0) + 1
            hot[key]["last_seen"] = now
        elif key in warm:
            # Warm revive: gap ≤ 30 days
            gap = _days_between(warm[key].get("last_seen", ""), now)
            if gap <= SILENCE_THRESHOLD_DAYS:
                warm[key]["count"] = warm[key].get("count", 0) + 1
                warm[key]["last_seen"] = now
                hot[key] = warm[key]
                del warm[key]
            else:
                # No revive: create new in hot
                hot[key] = {
                    "category": p.get("category", "runtime"),
                    "skill": skill,
                    "command": command,
                    "error": error,
                    "fix": p.get("fix", "—") or "—",
                    "count": 1,
                    "reusable": p.get("reusable", True),
                    "first_seen": now,
                    "last_seen": now,
                    "severity": severity,
                }
        else:
            # Fresh entry in hot
            hot[key] = {
                "category": p.get("category", "runtime"),
                "skill": skill,
                "command": command,
                "error": error,
                "fix": p.get("fix", "—") or "—",
                "count": 1,
                "reusable": p.get("reusable", True),
                "first_seen": now,
                "last_seen": now,
                "severity": severity,
            }

    # Silence eviction: hot cap
    if len(hot) > HOT_LIMIT:
        evict_keys = sorted(
            hot.keys(),
            key=lambda k: (hot[k].get("last_seen", ""), hot[k].get("count", 0)),
        )
        needed = len(hot) - HOT_LIMIT
        for k in evict_keys[:needed]:
            if k not in warm:
                warm[k] = hot[k]
            else:
                if warm[k].get("count", 0) < hot[k].get("count", 0):
                    warm[k] = hot[k]
            del hot[k]

    # Silence eviction: warm → cold
    if len(warm) > WARM_LIMIT:
        evict_keys = sorted(
            warm.keys(),
            key=lambda k: (warm[k].get("last_seen", ""), warm[k].get("count", 0)),
        )
        needed = len(warm) - WARM_LIMIT
        for k in evict_keys[:needed]:
            cold[k] = warm[k]
            del warm[k]

    # Cold cap: prune lowest count
    if len(cold) > COLD_LIMIT:
        keep_keys = sorted(
            cold.keys(),
            key=lambda k: -cold[k].get("count", 0),
        )[:COLD_LIMIT]
        kept = {k: cold[k] for k in keep_keys}
        cold.clear()
        cold.update(kept)

    return hot, warm, cold


def self_verify_failure(
    hot: dict[str, dict[str, Any]],
    warm: dict[str, dict[str, Any]],
    cold: dict[str, dict[str, Any]],
) -> list[str]:
    """Run V1-V5 self-checks. Returns list of error strings (empty = pass)."""
    errors: list[str] = []
    DATE_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")

    # V1: no duplicate keys across layers
    for name_a, d_a in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for name_b, d_b in [("hot", hot), ("warm", warm), ("cold", cold)]:
            if name_a >= name_b:
                continue
            dup = set(d_a.keys()) & set(d_b.keys())
            if dup:
                errors.append(f"V1: duplicate keys across {name_a} and {name_b}: {list(dup)[:3]}")

    # V2: capacity limits
    if len(hot) > HOT_LIMIT:
        errors.append(f"V2: hot has {len(hot)} (limit {HOT_LIMIT})")
    if len(warm) > WARM_LIMIT:
        errors.append(f"V2: warm has {len(warm)} (limit {WARM_LIMIT})")
    if len(cold) > COLD_LIMIT:
        errors.append(f"V2: cold has {len(cold)} (limit {COLD_LIMIT})")

    # V3: total vs unique keys
    all_keys = set(hot.keys()) | set(warm.keys()) | set(cold.keys())
    total = len(hot) + len(warm) + len(cold)
    if len(all_keys) != total:
        errors.append(f"V3: total entries {total} != unique keys {len(all_keys)}")

    # V4: required fields
    for layer_name, d in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for k, e in d.items():
            for field in ["skill", "command", "error", "count", "last_seen"]:
                if not e.get(field):
                    errors.append(f"V4: key {k} in {layer_name} missing '{field}'")

    # V5: date format
    for layer_name, d in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for k, e in d.items():
            ls = e.get("last_seen", "")
            if ls and not DATE_RE.match(str(ls)):
                errors.append(f"V5: key {k} in {layer_name} invalid last_seen: '{ls}'")

    return errors


# ---------------------------------------------------------------------------
# Single-layer legacy (backward compatible)
# ---------------------------------------------------------------------------

def emit_layer(
    patterns: dict[str, dict[str, Any]],
    title: str,
    note: str = "",
) -> list[str]:
    """Emit one layer's md content (used for hot/warm/cold output)."""
    now = _today()
    sections = {
        "## 1. CLI Parameter Errors": [
            "Skill", "Command", "Error Pattern", "Fix", "Count", "LastSeen", "Severity"
        ],
        "## 2. Skill Generation Issues": [
            "Skill", "Command", "Error Pattern", "Fix", "Count", "LastSeen", "Severity"
        ],
        "## 3. Cross-Skill Composition Failures": [
            "Skill", "Command", "Error Pattern", "Resolution", "Count", "LastSeen", "Severity"
        ],
        "## 4. Runtime Execution Patterns": [
            "Skill", "Operation", "Error Pattern", "Root Cause", "Count", "LastSeen", "Severity"
        ],
        "## 5. Token Efficiency Violations": [
            "Skill", "Command", "Error Pattern", "Fix", "Count", "LastSeen", "Severity"
        ],
    }
    section_map = {
        "cli_parameter": "## 1. CLI Parameter Errors",
        "skill_generation": "## 2. Skill Generation Issues",
        "cross_skill": "## 3. Cross-Skill Composition Failures",
        "runtime": "## 4. Runtime Execution Patterns",
        "token_efficiency": "## 5. Token Efficiency Violations",
    }
    by_section: dict[str, dict[str, dict[str, Any]]] = {s: {} for s in sections}
    for key, p in patterns.items():
        cat = p.get("category", "runtime")
        section = section_map.get(cat, "## 4. Runtime Execution Patterns")
        by_section[section][key] = p

    total_hits = sum(p.get("count", 0) for p in patterns.values())
    lines = [
        f"# Failure Patterns — {title}",
        "",
        f"> **Generated**: {now}",
        f"> **Total hits**: {total_hits}",
        note or f"> **Token budget**: {len(sections) * 3 + 10 + len(patterns)} lines.",
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
        for key, p in sorted(table_patterns.items(), key=lambda x: (-x[1].get("count", 0), x[0][0])):
            skill = p.get("skill", "—") or "—"
            command = p.get("command", p.get("operation", "—")) or "—"
            error = p.get("error", p.get("root cause", "—")) or "—"
            fix = p.get("fix", p.get("resolution", "—")) or "—"
            count = p.get("count", 0)
            last_seen = p.get("last_seen", p.get("first_seen", "—")) or "—"
            severity = p.get("severity", "minor") or "minor"
            lines.append(
                f"| `{skill}` | `{command}` | {error} | {fix} | {count} | {last_seen} | {severity} |"
            )
    return lines


def save_layer(
    path: Path,
    patterns: dict[str, dict[str, Any]],
    title: str,
    note: str = "",
) -> None:
    lines = emit_layer(patterns, title, note)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _emit_store(patterns: dict[str, dict[str, Any]]) -> list[str]:
    """Render the store markdown: header + one table per non-empty category."""
    now = datetime.now().strftime("%Y-%m-%d")

    sections = {
        "## 1. CLI Parameter Errors": [
            "Skill", "Command", "Error Pattern", "Fix", "Count", "LastSeen", "Severity", "Sources"
        ],
        "## 2. Skill Generation Issues": [
            "Skill", "Command", "Error Pattern", "Fix", "Count", "LastSeen", "Severity", "Sources"
        ],
        "## 3. Cross-Skill Composition Failures": [
            "Skill", "Command", "Error Pattern", "Resolution", "Count", "LastSeen", "Severity", "Sources"
        ],
        "## 4. Runtime Execution Patterns": [
            "Skill", "Operation", "Error Pattern", "Root Cause", "Count", "LastSeen", "Severity", "Sources"
        ],
        "## 5. Token Efficiency Violations": [
            "Skill", "Command", "Error Pattern", "Fix", "Count", "LastSeen", "Severity", "Sources"
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
        f"> **Token budget**: ≤ {MAX_LINES} lines, enforced — when exceeded, the least-recurring rows are dropped.",
        "> **Count**: distinct GCL runs (traces) that reported the pattern; re-scans do not inflate it.",
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
            last_seen = p.get("last_seen", p.get("first_seen", "—")) or "—"  # P0-C
            severity = p.get("severity", "minor") or "minor"  # P0-C
            sources = " ".join(sorted(p.get("sources") or ())) or "—"
            lines.append(
                f"| `{skill}` | `{command}` | {error} | {fix} | {count} | {last_seen} | {severity} | {sources} |"
            )

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


def enforce_line_cap(patterns: dict[str, dict[str, Any]]) -> list[str]:
    """Rebuild failure-patterns.md content, enforcing the MAX_LINES cap.

    AGENTS.md makes "≤ 200 lines" a P0 constraint, so the cap is *applied*
    rather than warned about: while the rendered file overflows, the least
    valuable rows (lowest count, then oldest last_seen) are dropped from
    ``patterns``. ``patterns`` is mutated in place so the caller's own
    counters (Total patterns / Total hits) describe what was written.
    """
    lines = _emit_store(patterns)
    if len(lines) > MAX_LINES:
        ranked = sorted(
            patterns.items(),
            key=lambda kv: (
                kv[1].get("count", 0),
                str(kv[1].get("last_seen") or kv[1].get("first_seen") or ""),
                str(kv[0]),
            ),
        )
        for key, _entry in ranked:
            del patterns[key]
            lines = _emit_store(patterns)
            if len(lines) <= MAX_LINES:
                break
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
    parser.add_argument(
        "--layered", action="store_true",
        help="Use three-layer hot/warm/cold storage instead of single-file"
    )
    parser.add_argument(
        "--promote", action="store_true",
        help="P2-A: Suggest pattern promotion to skill Anti-Pattern section when count >= 10"
    )
    args = parser.parse_args()

    # P2-A: promote check
    if args.promote:
        hot, warm, cold = load_all_layers()
        suggestions = []
        for name, layer in [("Hot", hot), ("Warm", warm), ("Cold", cold)]:
            for key, pat in layer.items():
                if pat.get("count", 0) >= 10:
                    suggestions.append(
                        f"  [{name}] `{key}` — consider adding to skill SKILL.md Anti-Pattern section "
                        f"(count={pat['count']}, category={pat.get('category', '?')})"
                    )
        if suggestions:
            print("PROMOTION CANDIDATES (count >= 10):", file=sys.stderr)
            for s in suggestions:
                print(s, file=sys.stderr)
        else:
            print("No promotion candidates (no patterns with count >= 10).", file=sys.stderr)
        return 0

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

    if args.layered:
        # P0-B: Three-layer storage
        hot, warm, cold = load_all_layers()
        old_hot = len(hot)
        hot, warm, cold = merge_failure_batch(new_patterns, hot, warm, cold)
        errors = self_verify_failure(hot, warm, cold)
        if errors:
            print("SELF-VERIFICATION FAILED:", file=sys.stderr)
            for e in errors:
                print(f"  {e}", file=sys.stderr)
            if not args.dry_run:
                return 1
        new_hot = len(hot) - old_hot
        total_hits = sum(p.get("count", 0) for p in {**hot, **warm, **cold}.values())
        print(
            f"Traces scanned: {len(trace_paths)}",
            f"Hot layer:  {len(hot)} (+{new_hot} new)",
            f"Warm layer: {len(warm)}",
            f"Cold layer: {len(cold)}",
            f"Total hits: {total_hits}",
            sep="\n"
        )
        if args.dry_run:
            print(f"\n[dry-run] Would write hot={len(hot)}, warm={len(warm)}, cold={len(cold)}")
            return 0
        save_layer(HOT_PATH, hot, "Hot Layer",
                   f"> **Token budget**: ≤ {HOT_LIMIT} lines.")
        save_layer(WARM_PATH, warm, "Warm Layer",
                   f"> **Token budget**: ≤ {WARM_LIMIT} lines.")
        save_layer(COLD_PATH, cold, "Cold Layer",
                   f"> **Token budget**: ≤ {COLD_LIMIT} lines.")
        print(f"Written: {HOT_PATH.relative_to(args.root)}")
        print(f"Written: {WARM_PATH.relative_to(args.root)}")
        print(f"Written: {COLD_PATH.relative_to(args.root)}")
    else:
        # Legacy single-file storage
        merged = merge(existing.copy(), new_patterns)
        new_count = len(merged) - existing_count
        # Same aging policy as reflexion_auto_writer._bulk_update: a pattern
        # observed in this run is never pruned, however low its count.
        observed = {k for p in new_patterns if (k := pattern_key(p))}
        prune_low_frequency(merged, min_count=args.min_count, exclude=observed)
        pruned = existing_count + new_count - len(merged)
        kept = len(merged)
        lines = enforce_line_cap(merged)
        dropped = kept - len(merged)
        total_hits = sum(p["count"] for p in merged.values())
        print(
            f"Traces scanned:     {len(trace_paths)}",
            f"New patterns:        {new_count}",
            f"Count increments:    {len(merged) - existing_count - new_count + (existing_count - len([k for k in existing if k in merged]))}",
            f"Pruned (count<{args.min_count}): {pruned}",
            f"Dropped (cap {MAX_LINES}):   {dropped}",
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
