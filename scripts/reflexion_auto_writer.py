#!/usr/bin/env python3
"""Reflexion auto-writer — auto-call failure_pattern_extract after GCL runs.

Single-purpose: bridge the gap between gcl_runner.py trace persistence
and docs/failure-patterns.md updates. Reuses functions from
failure_pattern_extract.py (do NOT reimplement merge/dedup/parse).

Public API:
  write_trace(trace_dict, trace_path=None, *, patterns_path)  → bool  (atomic, fcntl-locked)
  main()                                                      → int   (bulk CLI)

Usage:
  python3 scripts/reflexion_auto_writer.py                # bulk: all traces
  python3 scripts/reflexion_auto_writer.py --dry-run      # show diff, no write
  python3 scripts/reflexion_auto_writer.py --since-hours 24
  python3 scripts/reflexion_auto_writer.py --input trace.json

Exit codes:
  0  success. Includes the no-op (no failure_pattern in any trace) and a corpus
     that legitimately overflows the 200-line cap: that truncation is reported
     by name on stderr as "REFLEXION GATE (non-fatal)" but is a designed budget,
     not a failure. The cap is a P0 constraint (AGENTS.md), not an operator
     knob, so failing `make all` for it made the target permanently red on a
     large corpus with no remedy the operator could apply — a gate nobody can
     clear stops being read.
  1  no traces / no patterns found
  3  R3 gate: something the run read did not reach the store for a reason the
     line cap cannot explain. Either the store is empty despite patterns being
     found (every one carries an empty `skill`, which merge() drops), or merge()
     accepted a pattern that is then absent and was not cap-evicted — a writer
     defect. A --dry-run preview never returns 3: it changes nothing, so it only
     reports what the next real run would do.
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
    pattern_key,
    prune_low_frequency,
)

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Single-trace atomic write (called by gcl_runner.py after persist_trace)
# ---------------------------------------------------------------------------

def write_trace(
    trace: dict[str, Any],
    trace_path: Path | None = None,
    *,
    patterns_path: Path,
) -> bool:
    """Update failure patterns from a single GCL trace dict.

    ``patterns_path`` is required and keyword-only: there is no destination
    default, so the shipped ``docs/failure-patterns.md`` cannot be reached by a
    caller that did not name it. That is what makes "a run against a temporary
    root cannot mutate the committed store" true of this function rather than of
    its callers — the default used to be the module's PATTERNS_FILE, and one
    call without it rewrote the committed, agent-facing store.

    A missing ``patterns_path`` is a TypeError at the call site: a programming
    error, raised before any work, not a reflexion failure. ``trace_path`` only
    backfills the ``_source`` field; it never changes the destination.

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

        target = patterns_path
        target.parent.mkdir(parents=True, exist_ok=True)
        # fcntl.flock requires an open fd; create if missing
        target.touch(exist_ok=True)
        evicted: list[str] = []
        dropped_self: tuple[str, str, str] | None = None
        with target.open("r+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                existing = parse_existing(target)
                before = set(existing)
                merged = merge(existing.copy(), [fp])
                # Two deliberate asymmetries with _bulk_update():
                #  - no prune here: one trace cannot tell whether a stored pattern
                #    stopped recurring — only a scan of the whole corpus can;
                #  - no empty-store gate: this path is allowed to be a no-op.
                # Both paths enforce the line cap, and both count DISTINCT traces
                # via merge(), so re-writing the same trace changes nothing.
                lines = enforce_line_cap(merged)
                # At the cap every new pattern evicts an existing one. The caller
                # cannot see that from the return value, so say it — and say it
                # for the newcomer too: `before` holds only pre-existing keys, so
                # the eviction report used to name every row *except* the one the
                # caller was writing, and write_trace still returned True while
                # the pattern it was called for was absent from the store.
                evicted = sorted(before - set(merged))
                own_key = pattern_key(fp)
                if own_key is not None and own_key not in merged:
                    dropped_self = own_key
                f.seek(0)
                f.write("\n".join(lines) + "\n")
                f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        if evicted:
            print(
                f"[reflexion_auto_writer] line cap {MAX_LINES} evicted "
                f"{len(evicted)} stored pattern(s) to write this one: "
                + ", ".join(f"{s}:{c}:{e}" for s, c, e in evicted[:5])
                + (f" (+{len(evicted) - 5} more)" if len(evicted) > 5 else ""),
                file=sys.stderr,
            )
        if dropped_self:
            print(
                f"[reflexion_auto_writer] line cap {MAX_LINES} also dropped the pattern "
                f"this write was called for ({dropped_self[0]}:{dropped_self[1]}:"
                f"{dropped_self[2]}): it is stored NOWHERE. True here means the write "
                "happened, not that this pattern is in the store.",
                file=sys.stderr,
            )
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
    # Every dedup key this run actually observed. --min-count is an AGING
    # policy: it retires patterns that have STOPPED recurring, so it must never
    # touch a key the current corpus reports. Pruning an observed key deletes it
    # in the very run that records it, and count can then never reach min_count
    # (see docs/reflexion-memory.md §10).
    observed = {k for p in new_patterns if (k := pattern_key(p))}
    prune_low_frequency(existing, min_count=min_count, exclude=observed)
    retired = existing_count - len(existing)
    kept_count = len(existing)
    merged = merge(existing, new_patterns)
    new_count = len(merged) - kept_count
    kept = len(merged)
    cap_input = set(merged)
    lines = enforce_line_cap(merged)
    dropped = kept - len(merged)
    cap_evicted = cap_input - set(merged)
    # R3: a reflexion loop that silently drops what it just read is not a
    # success — and the only path that drops an observed pattern is the line
    # cap above, so the check has to run after it. Computed before, `missing`
    # was structurally empty (both sides call pattern_key() on the same
    # new_patterns list) while the cap evicted observed keys at exit 0.
    #
    # Split by cause, because the cap is a designed budget and anything else is
    # a writer defect. `merge()` adds every key `observed` holds, so today every
    # `missing` key is cap-evicted — but that is merge()'s current behaviour,
    # not a property of the file, and the gate exists to notice when it changes
    # (see test_gate_names_an_observed_pattern_merge_dropped). So only loss the
    # cap does not explain is fatal; a corpus that merely overflows the
    # 200-line budget is reported and allowed through, because --min-count
    # cannot recover a cap-evicted key, MAX_LINES is a P0 constraint rather than
    # an operator knob, and a `make all` that is permanently red on a large
    # corpus stops being read.
    missing = sorted(observed - set(merged))
    unexplained = [k for k in missing if k not in cap_evicted]

    total_hits = sum(p["count"] for p in merged.values())
    print(
        f"Traces scanned:        {len(trace_paths)}",
        f"New patterns:          {new_count}",
        f"Retired (count<{min_count}):  {retired}",
        f"Dropped (cap {MAX_LINES}):    {dropped}",
        f"Total patterns:        {len(merged)}",
        f"Total hits:            {total_hits}",
        f"Output lines:          {len(lines)}",
        sep="\n",
    )

    if dry_run:
        print("\n[dry-run] Would update:", PATTERNS_FILE.relative_to(ROOT))
        if missing:
            print(
                "[dry-run] WARNING: the next real run would drop "
                f"{len(missing)} observed pattern(s): "
                + ", ".join(f"{s}:{c}:{e}" for s, c, e in missing[:5]),
                file=sys.stderr,
            )
        if not merged:
            print(
                "[dry-run] WARNING: the next real run would leave the store empty.",
                file=sys.stderr,
            )
        return 0

    if unexplained:
        print(
            f"REFLEXION GATE: {len(unexplained)} pattern(s) found and ACCEPTED by merge() are "
            f"missing from the store, and the {MAX_LINES}-line cap did not evict them: "
            + ", ".join(f"{s}:{c}:{e}" for s, c, e in unexplained[:5])
            + (f" (+{len(unexplained) - 5} more)" if len(unexplained) > 5 else "")
            + ". Only the cap may drop a pattern this run read, so something else is "
            "losing rows — a writer defect, not a full store.",
            file=sys.stderr,
        )
        return 3

    if missing:
        print(
            f"REFLEXION GATE (non-fatal): {len(missing)} pattern(s) found in traces were "
            f"evicted by the {MAX_LINES}-line cap in docs/failure-patterns.md: "
            + ", ".join(f"{s}:{c}:{e}" for s, c, e in missing[:5])
            + (f" (+{len(missing) - 5} more)" if len(missing) > 5 else "")
            + ". The store is full, not broken: the budget is enforced by dropping the "
            "least-recurring rows. Compact the corpus, or keep the whole set with "
            "`failure_pattern_extract.py --layered`.",
            file=sys.stderr,
        )

    if not merged:
        print(
            f"REFLEXION STORE IS EMPTY despite {len(new_patterns)} pattern(s) found in traces "
            "— every one of them carries an empty 'skill' and is dropped by merge().",
            file=sys.stderr,
        )
        return 3

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
        help=(
            "Retires stored patterns absent from this run's corpus whose count "
            "is below the threshold (default: 3). Never retires a key this run "
            "observed — see docs/reflexion-memory.md §10"
        ),
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