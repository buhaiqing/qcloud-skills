#!/usr/bin/env python3
"""Aggregate root-cause ranking results from a JSONL file (P0-5).

Reads ``audit-results/root-cause-rank.jsonl`` (or a positional path arg). Each
line is a JSON object:

.. code-block:: json

    {
      "context": { ... BusinessContext fields ... },
      "candidates": [ { ... CandidateRootCause fields ... }, ... ]
    }

Prints a per-context candidate table (``candidate_id|resource|priority|score|
components``) plus the top-1 candidate summary per context.

Exit codes: 0 success, 1 on missing/unreadable/parse failure. Stdlib-only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "audit-results" / "root-cause-rank.jsonl"

sys_path = str(ROOT / "qcloud-copilot")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from copilot import root_cause_rank as rcr


def _coerce_ctx(data: dict) -> rcr.BusinessContext:
    return rcr.BusinessContext(**data)


def _coerce_cand(data: dict) -> rcr.CandidateRootCause:
    return rcr.CandidateRootCause(**data)


def build_records(path: Path) -> list[tuple[rcr.BusinessContext, list[rcr.CandidateRootCause]]]:
    records: list[tuple[rcr.BusinessContext, list[rcr.CandidateRootCause]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        records.append((_coerce_ctx(obj["context"]), [_coerce_cand(c) for c in obj["candidates"]]))
    return records


def print_table(ctx: rcr.BusinessContext, results: list[rcr.RankResult]) -> None:
    print(f"context: service={ctx.service} business_chain={ctx.business_chain} "
          f"customer_tier={ctx.customer_tier} core_hours={ctx.core_hours} "
          f"maintenance_window={ctx.maintenance_window}")
    print("candidate_id|resource|priority|score|components")
    for r in results:
        print(f"{r.candidate_id}|{r.resource}|{r.priority:.4f}|"
              f"{r.score:.4f}|{json.dumps(r.components)}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0]) if argv else DEFAULT_PATH

    if not path.exists() or not path.is_file():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 1

    try:
        records = build_records(path)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        print(f"ERROR: failed to parse {path}: {e}", file=sys.stderr)
        return 1

    if not records:
        print("No records found.", file=sys.stderr)
        return 1

    ranker = rcr.RootCauseRanker()
    for i, (ctx, candidates) in enumerate(records):
        print(f"\n--- record {i} ---")
        results = ranker.rank(candidates, ctx)
        print_table(ctx, results)
        top = results[0] if results else None
        if top:
            print(f"top-1: {top.candidate_id} priority={top.priority:.4f} score={top.score:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
