#!/usr/bin/env python3
"""Validate EvidenceRecord JSON files against docs/evidence-kernel-schema.json.

Stdlib-only minimal draft-07 validation: required fields present, enum values,
and type checks (string/integer/number/boolean/object/array; type may be a list
for nullable). Also enforces two KPI safety rules:

  KPI#1: safety.leak_checked must be true.
  KPI#2: if safety.destructive is true then safety.token must be present (not null).

Exit codes: 0 = all valid, 1 = validation error(s), 2 = usage error.
"""
from __future__ import annotations

import json
import sys
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


def main(argv: list) -> int:
    if len(argv) < 2:
        sys.stderr.write("usage: validate_evidence_schema.py <file.json> [more.json ...]\n")
        return 2
    errors: list = []
    count = 0
    for path in argv[1:]:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: cannot read/parse JSON ({exc})")
            continue
        records = data if isinstance(data, list) else [data]
        count += 1
        for i, rec in enumerate(records):
            validate_record(rec, i, errors)
    if errors:
        for err in errors:
            print(f"FAIL {err}")
        return 1
    print(f"OK: {count} file(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
