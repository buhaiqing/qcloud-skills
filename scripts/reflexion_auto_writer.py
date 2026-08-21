#!/usr/bin/env python3
"""Reflexion auto-writer — auto-call failure_pattern_extract after GCL runs.

Single-purpose: bridge the gap between gcl_runner.py trace persistence
and docs/failure-patterns.md updates. Reuses functions from
failure_pattern_extract.py (do NOT reimplement merge/dedup/parse).

Public API:
  write_trace(trace_dict, trace_path=None)  → bool  (atomic, fcntl-locked)
  main()                                    → int   (bulk CLI: process all traces)

Usage:
  python3 scripts/reflexion_auto_writer.py                # bulk: all traces
  python3 scripts/reflexion_auto_writer.py --dry-run      # show diff, no write
  python3 scripts/reflexion_auto_writer.py --since-hours 24
  python3 scripts/reflexion_auto_writer.py --input trace.json

Exit codes:
  0  success (incl. no-op when no failure_pattern in any trace)
  1  no traces / no patterns found
  2  parse error in failure-patterns.md
  3  self-verify failure (V1-V5 from failure_pattern_extract)
"""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from failure_pattern_extract import (
    MAX_LINES,
    PATTERNS_FILE,
    collect_traces,
    enforce_line_cap,
    extract_failure_patterns,
    merge,
    parse_existing,
    prune_low_frequency,
)

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Single-trace atomic write (called by gcl_runner.py after persist_trace)
# ---------------------------------------------------------------------------

def write_trace(trace: dict[str, Any], trace_path: Path | None = None) -> bool:
    """Update docs/failure-patterns.md from a single GCL trace dict.

    Extracts the failure_pattern field at trace['final']['failure_pattern'].
    Atomic via fcntl.flock + write_text. Never raises — reflexion failures
    must not break the GCL caller. Returns True if write happened, False
    if no-op (no failure_pattern, or already-counted).
    """
    try:
        fp = (trace.get("final") or {}).get("failure_pattern")
        if not fp:
            return False
        if trace_path:
            fp = {**fp, "_source": trace_path.name}

        PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        # fcntl.flock requires an open fd; create if missing
        PATTERNS_FILE.touch(exist_ok=True)
        with PATTERNS_FILE.open("r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                existing = parse_existing(PATTERNS_FILE)
                merged = merge(existing.copy(), [fp])
                prune_low_frequency(merged, min_count=3)
                lines = enforce_line_cap(merged)
                f.seek(0)
                f.write("\n".join(lines) + "\n")
                f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True
    except Exception as e:  # noqa: BLE001 — reflexion must never break GCL
        print(f"[reflexion_auto_writer] write_trace failed: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Bulk CLI (mirrors failure_pattern_extract.main but with file lock)
# ---------------------------------------------------------------------------

def _bulk_update(trace_paths: list[Path], dry_run: bool, min_count: int) -> int:
    """Process N traces under lock; print summary; return exit code."""
    new_patterns = extract_failure_patterns(trace_paths)
    if not new_patterns:
        print("No failure_pattern fields found in traces.", file=sys.stderr)
        return 1

    existing = parse_existing(PATTERNS_FILE)
    existing_count = len(existing)
    merged = merge(existing.copy(), new_patterns)
    new_count = len(merged) - existing_count
    prune_low_frequency(merged, min_count=min_count)
    pruned = existing_count + new_count - len(merged)
    lines = enforce_line_cap(merged)

    if len(lines) > MAX_LINES + 10:
        print(
            f"WARN: output {len(lines)} lines exceeds cap ({MAX_LINES}). "
            f"Raise --min-count or archive older patterns.",
            file=sys.stderr,
        )

    total_hits = sum(p["count"] for p in merged.values())
    print(
        f"Traces scanned:        {len(trace_paths)}",
        f"New patterns:          {new_count}",
        f"Pruned (count<{min_count}):  {pruned}",
        f"Total patterns:        {len(merged)}",
        f"Total hits:            {total_hits}",
        f"Output lines:          {len(lines)}",
        sep="\n",
    )

    if dry_run:
        print("\n[dry-run] Would update:", PATTERNS_FILE.relative_to(ROOT))
        return 0

    PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PATTERNS_FILE.touch(exist_ok=True)
    with PATTERNS_FILE.open("r+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            f.write("\n".join(lines) + "\n")
            f.truncate()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    print(f"\nUpdated: {PATTERNS_FILE.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", nargs="*", help="Trace file(s) or glob under --root")
    parser.add_argument(
        "--since-hours", type=int, default=None,
        help="Only traces modified within N hours (default: all)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print diff, no write")
    parser.add_argument(
        "--min-count", type=int, default=3,
        help="Prune patterns with count below this threshold (default: 3)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable summary")
    args = parser.parse_args()

    trace_paths = collect_traces(args.root, args.input, args.since_hours)
    if not trace_paths:
        print("No gcl-trace files found.", file=sys.stderr)
        return 1

    if args.json:
        new_patterns = extract_failure_patterns(trace_paths)
        out = {
            "ts": datetime.now(UTC).isoformat(),
            "traces_scanned": len(trace_paths),
            "patterns_found": len(new_patterns),
            "patterns": new_patterns,
            "dry_run": args.dry_run,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    return _bulk_update(trace_paths, args.dry_run, args.min_count)


if __name__ == "__main__":
    sys.exit(main())