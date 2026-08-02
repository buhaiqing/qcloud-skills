#!/usr/bin/env python3
"""CI gate: validate every qcloud-*-ops/assets/eval_queries.json.

Each file must be a JSON array of objects. Every object must carry a
non-empty string ``query`` and a boolean ``should_trigger``. The legacy
``eval_set`` wrapper key is rejected.

Per-skill coverage is enforced: at least ``--min-positive`` cases with
``should_trigger=true`` and at least ``--min-negative`` with ``false``
(default 2/2, matching the AGENTS.md 2-round self-review standard).

Exit 0 when every skill passes; exit 1 with a per-file error list otherwise.

Usage:
    python3 scripts/validate_eval_queries.py
    python3 scripts/validate_eval_queries.py --root <repo-root>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _validate_file(path: Path, min_positive: int, min_negative: int) -> list[str]:
    """Validate one eval_queries.json. Returns a list of human-readable errors."""
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    if not isinstance(data, list):
        return [
            (
                f"{path}: top-level must be a JSON array of objects, "
                f"got {type(data).__name__}"
            )
        ]

    positives = 0
    negatives = 0
    seen_queries: set[str] = set()
    for i, case in enumerate(data):
        label = f"{path}:{i}"
        if not isinstance(case, dict):
            errors.append(f"{label}: case must be a JSON object, got {type(case).__name__}")
            continue
        if "eval_set" in case:
            errors.append(f"{label}: legacy 'eval_set' key is not allowed")
        query = case.get("query")
        if not isinstance(query, str) or not query.strip():
            errors.append(f"{label}: 'query' must be a non-empty string")
        else:
            if query in seen_queries:
                errors.append(f"{path}: duplicate query {query!r}")
            seen_queries.add(query)
        should_trigger = case.get("should_trigger")
        if not isinstance(should_trigger, bool):
            errors.append(f"{label}: 'should_trigger' must be a boolean (true/false)")
        elif should_trigger:
            positives += 1
        else:
            negatives += 1

    if positives < min_positive:
        errors.append(
            f"{path}: {positives} positive case(s) (should_trigger=true), "
            f"need >= {min_positive}"
        )
    if negatives < min_negative:
        errors.append(
            f"{path}: {negatives} negative case(s) (should_trigger=false), "
            f"need >= {min_negative}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=ROOT,
        help="Repo root (default: parent of this script)",
    )
    parser.add_argument(
        "--min-positive", type=int, default=2,
        help="Minimum should_trigger=true cases per skill (default: 2)",
    )
    parser.add_argument(
        "--min-negative", type=int, default=2,
        help="Minimum should_trigger=false cases per skill (default: 2)",
    )
    args = parser.parse_args()

    files = sorted(args.root.glob("qcloud-*-ops/assets/eval_queries.json"))
    failed: dict[str, list[str]] = {}
    for path in files:
        skill = path.parent.parent.name
        errors = _validate_file(path, args.min_positive, args.min_negative)
        if errors:
            failed[skill] = errors
            print(f"FAIL {skill}")
            for err in errors:
                print(f"    {err}")
        else:
            print(f"OK   {skill}")

    if failed:
        print(f"\n{len(files)} skills scanned, {len(failed)} failed")
        return 1
    print(f"\n{len(files)} skills scanned: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
