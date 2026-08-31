#!/usr/bin/env python3
"""Backfill missing schema fields (started_at, finished_at, commits, files_changed)
across all historical traces:
  - audit-results/gcl-trace-*.json  (individual trace files)
  - audit-results/evidence-local.jsonl (one JSON object per line)

Usage:
    python3 scripts/backfill_trace_schema.py     # dry-run (default)
    python3 scripts/backfill_trace_schema.py --apply   # actually write changes
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audit-results"
SCHEMA_FIELDS = ("started_at", "finished_at", "commits", "files_changed")


def _derive_started_at(trace: dict[str, Any], path: Path) -> str:
    """Pick the best available start timestamp."""
    if trace.get("started_at"):
        return trace["started_at"]
    try:
        mtime = os.path.getmtime(path)
        return datetime.fromtimestamp(mtime, tz=UTC).isoformat()
    except OSError:
        pass
    return datetime.now(UTC).isoformat()


def _backfill_record(trace: dict[str, Any], path: Path | None = None) -> tuple[dict[str, Any], list[str]]:
    """Fill missing schema fields in a trace record.

    Returns (updated_record, missing_fields_before).
    """
    missing = [f for f in SCHEMA_FIELDS if f not in trace]
    for field in missing:
        if field == "started_at":
            trace[field] = _derive_started_at(trace, path) if path else datetime.now(UTC).isoformat()
        elif field == "finished_at":
            trace[field] = datetime.now(UTC).isoformat()
        else:  # commits, files_changed
            trace[field] = []
    return trace, missing


def _backfill_json(path: Path, dry_run: bool = True) -> dict[str, Any]:
    """Backfill one gcl-trace-*.json file."""
    try:
        trace = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"path": str(path), "changed": False, "error": str(e)}

    _, missing = _backfill_record(trace, path)
    if not missing:
        return {"path": str(path), "changed": False, "missing": []}

    if not dry_run:
        path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"path": str(path), "changed": True, "missing": missing}


def _backfill_jsonl(path: Path, dry_run: bool = True) -> dict[str, Any]:
    """Backfill evidence-local.jsonl (one JSON object per line)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(l) for l in lines]
    except (json.JSONDecodeError, OSError) as e:
        return {"path": str(path), "changed": False, "error": str(e), "missing": list(SCHEMA_FIELDS)}

    all_missing: list[str] = []
    new_records = []
    any_changed = False
    for rec in records:
        _, missing = _backfill_record(rec)
        if missing:
            any_changed = True
            all_missing.extend(missing)
        new_records.append(rec)

    if not dry_run and any_changed:
        # Preserve one-JSON-object-per-line format
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in new_records) + "\n",
                        encoding="utf-8")

    return {"path": str(path), "changed": any_changed,
            "missing": list(dict.fromkeys(all_missing))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument("--apply", action="store_true",
                        help="Actually write changes (default is dry-run)")
    args = parser.parse_args()
    dry_run = not args.apply
    mode = "DRY-RUN" if dry_run else "APPLYING"

    json_files = sorted(glob.glob(str(AUDIT_DIR / "gcl-trace-*.json")))
    jsonl_files = [str(AUDIT_DIR / "evidence-local.jsonl")] if (AUDIT_DIR / "evidence-local.jsonl").exists() else []
    all_sources = json_files + jsonl_files

    if not all_sources:
        print("No trace sources found.")
        return 0

    print(f"[{mode}] Scanning {len(json_files)} JSON + {len(jsonl_files)} JSONL file(s) ...\n")

    total_changed = 0
    missing_counts: dict[str, int] = {f: 0 for f in SCHEMA_FIELDS}
    errors = []

    jsonl_line_count = 0
    for fp in json_files:
        result = _backfill_json(Path(fp), dry_run=dry_run)
        if "error" in result:
            errors.append(result)
            continue
        for f in SCHEMA_FIELDS:
            if f in result.get("missing", []):
                missing_counts[f] += 1
        if result["changed"]:
            total_changed += 1
            print(f"  [PATCHED] {Path(fp).name}")

    for fp in jsonl_files:
        result = _backfill_jsonl(Path(fp), dry_run=dry_run)
        if "error" in result:
            errors.append(result)
            continue
        # Count per line: each line is a trace, count missing per field
        try:
            lines = Path(fp).read_text(encoding="utf-8").splitlines()
            jsonl_line_count = len(lines)
            for line in lines:
                rec = json.loads(line)
                for f in SCHEMA_FIELDS:
                    if f not in rec:
                        missing_counts[f] += 1
        except (OSError, json.JSONDecodeError):
            pass
        if result["changed"]:
            total_changed += 1
            print(f"  [PATCHED] {Path(fp).name} ({jsonl_line_count} lines)")

    total_traces = len(json_files) + jsonl_line_count
    print(f"\n[{mode}] Summary:")
    print(f"  Total traces  : {total_traces} ({len(json_files)} JSON + {sum(len(open(f, encoding='utf-8').readlines()) for f in jsonl_files)} JSONL)")
    print(f"  Sources changed: {total_changed}")
    for f in SCHEMA_FIELDS:
        print(f"  {f:<16}: {missing_counts[f]}/{total_traces} traces missing (now filled)")

    if errors:
        print(f"\n  Errors        : {len(errors)}")
        for e in errors:
            print(f"    {e['path']}: {e.get('error', '?')}")

    if dry_run:
        print("\n(Dry-run complete. Run with --apply to write changes.)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
