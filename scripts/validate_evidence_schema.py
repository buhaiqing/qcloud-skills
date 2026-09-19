#!/usr/bin/env python3
"""Validate EvidenceRecord JSON files against docs/evidence-kernel-schema.json.

Accepts `.json` (a single record or an array of records) and `.jsonl` (one
record per line — the stream scripts/evidence_kernel.py appends to). Reading
JSONL here is a smaller diff than collecting lines into a temp JSON file in the
caller, and it keeps the KPI#1/#2 rules in this one authoritative validator.

Stdlib-only minimal draft-07 validation: required fields present, enum values,
and type checks (string/integer/number/boolean/object/array; type may be a list
for nullable). Also enforces two KPI safety rules:

  KPI#1: safety.leak_checked must be true.
  KPI#2: if safety.destructive is true then safety.token must be present (not null).

Exit codes: 0 = all valid, 1 = validation error(s), 2 = usage error.

Freshness and floor (`--max-age-days` / `--min-records`):
- `--max-age-days N` splits the read records into *fresh* (provenance.captured_at
  within N days) and *aged-out*. Safety rules still apply to every record read —
  a destructive op without a token is a violation whenever it happened — but only
  fresh records are counted as evidence of current behaviour, so a 2019 stream
  can no longer keep a safety gate green forever.
- `--min-records N` fails (exit 1) when fewer than N fresh records were read: a
  present-but-empty stream is a gap in the audit trail, not a clean bill of health.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "evidence-kernel-schema.json"


def _type_ok(value: object, expected) -> bool:
    if isinstance(expected, list):
        return any(_type_ok(value, e) for e in expected)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    return True


def _check_obj(obj: dict, schema: dict, path: str, errors: list) -> None:
    for field in schema.get("required", []):
        if field not in obj:
            errors.append(f"{path}.{field}: missing required field")
    props = schema.get("properties", {})
    for field, value in obj.items():
        if field not in props:
            continue
        sub = props[field]
        fpath = f"{path}.{field}"
        if "enum" in sub and value not in sub["enum"]:
            errors.append(f"{fpath}: {value!r} not in enum {sub['enum']}")
        if "type" in sub and not _type_ok(value, sub["type"]):
            errors.append(f"{fpath}: expected type {sub['type']}, got {type(value).__name__}")
        if sub.get("type") == "object" and isinstance(value, dict):
            _check_obj(value, sub, fpath, errors)


def validate_record(record: dict, idx: int, errors: list) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    _check_obj(record, schema, f"record[{idx}]", errors)
    # KPI#1: leak must be checked
    safety = record.get("safety")
    if isinstance(safety, dict) and safety.get("leak_checked") is not True:
        errors.append(f"record[{idx}].safety.leak_checked: KPI#1 requires leak_checked=true")
    # KPI#2: destructive requires a token
    if isinstance(safety, dict) and safety.get("destructive") is True and not safety.get("token"):
        errors.append(
            f"record[{idx}].safety.token: KPI#2 destructive op requires a non-null confirmation token"
        )
    # KPI#2 (extended): destructive requires plan_hash bound to the executed plan.
    # Spec Phase 3 — token<->plan_hash binding. The schema allows plan_hash to
    # be null for non-destructive records, but destructive=true without a
    # plan_hash means the audit trail cannot verify which plan the token
    # authorised. Without this rule, gcl_runner.py regressing to write
    # plan_hash=None for destructive ops would silently pass schema validation.
    if isinstance(safety, dict) and safety.get("destructive") is True and not safety.get("plan_hash"):
        errors.append(
            f"record[{idx}].safety.plan_hash: KPI#2 destructive op requires a non-null plan_hash (Phase 3 token<->plan binding)"
        )


def _parse_jsonl(path: str, text: str, errors: list) -> list:
    """One EvidenceRecord per non-blank line. A malformed line is an error, never
    a silent skip — a gap in the audit stream must fail the gate, not shrink it."""
    records = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{lineno}: cannot parse JSONL line ({exc})")
    return records


def _captured_at(record: dict) -> datetime | None:
    """provenance.captured_at as an aware UTC datetime, or None if unusable."""
    if not isinstance(record, dict):
        return None
    value = (record.get("provenance") or {}).get("captured_at")
    if not isinstance(value, str):
        return None
    try:
        # py311 fromisoformat accepts the trailing "Z" that evidence_kernel writes.
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help=".json (record or array) / .jsonl files")
    parser.add_argument("--max-age-days", type=float, default=None,
                        help="Count only records captured within N days as evidence")
    parser.add_argument("--min-records", type=int, default=0,
                        help="Fail when fewer than N fresh records were read")
    args = parser.parse_args(argv[1:])
    if not args.files:
        sys.stderr.write(
            "usage: validate_evidence_schema.py [--max-age-days N] [--min-records N]"
            " <file.json|file.jsonl> [...]\n"
        )
        return 2
    errors: list = []
    fresh: list = []
    aged = 0
    cutoff = (
        datetime.now(UTC) - timedelta(days=args.max_age_days)
        if args.max_age_days is not None
        else None
    )
    for path in args.files:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{path}: cannot read ({exc})")
            continue
        if path.endswith(".jsonl"):
            records = _parse_jsonl(path, text, errors)
        else:
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}: cannot read/parse JSON ({exc})")
                continue
            records = data if isinstance(data, list) else [data]
        for i, rec in enumerate(records):
            validate_record(rec, i, errors)
            if cutoff is None:
                fresh.append(rec)
                continue
            ts = _captured_at(rec)
            if ts is None:
                # An unprovable timestamp cannot be counted as fresh; refusing it
                # is the only fail-closed reading (a null captured_at would
                # otherwise be indefinitely fresh).
                errors.append(
                    f"{path}: record[{i}].provenance.captured_at: missing/unparseable,"
                    f" cannot prove freshness within {args.max_age_days:g} day(s)"
                )
            elif ts < cutoff:
                aged += 1
            else:
                fresh.append(rec)
    if len(fresh) < args.min_records:
        errors.append(
            f"only {len(fresh)} fresh record(s) read; --min-records floor is {args.min_records}"
        )
    if errors:
        for err in errors:
            print(f"FAIL {err}")
        return 1
    suffix = f", {aged} aged-out (>{args.max_age_days:g}d)" if cutoff is not None else ""
    print(f"OK: {len(fresh)} record(s) valid{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
