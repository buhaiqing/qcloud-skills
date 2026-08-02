#!/usr/bin/env python3
"""Aggregate post-fix verification results (P0-4) into a summary table.

Reads ``audit-results/verification.jsonl`` (or a positional path), each line a
JSON object from a `VerificationResult` (+ optional sample fields). Prints a
table of ``action | verification_status | api_success | health_recovered |
recovery_magnitude | rollback_suggested`` plus a per-status summary line.

Exit 0 on success; 1 on missing/unreadable/parse error. Stdlib-only.

Usage:
  python3 scripts/verification_aggregate.py
  python3 scripts/verification_aggregate.py path/to/verification.jsonl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "audit-results" / "verification.jsonl"
STATUSES = ("verified", "recovered", "partial", "failed", "unverifiable")


def load_records(path: Path) -> list[dict[str, Any]]:
    """Parse each JSONL line into a dict. Raises OSError/ValueError on bad input."""
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"invalid JSON at {path}:{lineno}: {e}") from e
            if not isinstance(record, dict):
                raise TypeError(f"non-object record at {path}:{lineno}")
            records.append(record)
    return records


def render(records: list[dict[str, Any]]) -> str:
    """Build the human-readable table + summary string."""
    header = (
        f"{'action':<24} {'status':<12} {'api_success':<11} "
        f"{'health_recovered':<16} {'magnitude':<9} rollback"
    )
    lines = [header, "-" * len(header)]

    counts: dict[str, int] = {}
    for rec in records:
        status = rec.get("verification_status", "unknown")
        counts[status] = counts.get(status, 0) + 1
        lines.append(
            f"{rec.get('action', '')!s:<24} {status:<12} "
            f"{rec.get('api_success', '')!s:<11} {rec.get('health_recovered', '')!s:<16} "
            f"{rec.get('recovery_magnitude', 0.0):<9.3f} {rec.get('rollback_suggested', False)}"
        )

    summary = " | ".join(
        f"{s}: {counts.get(s, 0)}" for s in STATUSES if counts.get(s, 0) > 0
    )
    if not summary:
        summary = "no records"
    summary_line = f"total={len(records)}  {summary}"
    return "\n".join(lines) + "\n" + summary_line


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        path = Path(args[0])
    else:
        path = DEFAULT_PATH

    if not path.exists():
        print(f"ERROR: verification file not found: {path}", file=sys.stderr)
        return 1
    try:
        records = load_records(path)
    except (OSError, TypeError, ValueError) as e:
        print(f"ERROR: cannot read verification file {path}: {e}", file=sys.stderr)
        return 1

    print(render(records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
