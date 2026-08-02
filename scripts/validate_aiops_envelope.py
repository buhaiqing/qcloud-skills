#!/usr/bin/env python3
"""Validate AIOpsEnvelope JSON fixtures + detect breaking schema changes.

Stdlib-only minimal draft-07 validation (required/enum/type/const/pattern),
consistent with validate_evidence_schema.py.

Also provides breaking-change detection between two schema versions:

  - Removing a field from `required`
  - Narrowing an `enum` (removing values)
  - Changing a `const`
  - Relaxing `additionalProperties: false` is NOT breaking
  - Adding a new `required` field IS breaking (existing producers break)

Usage:
  python3 validate_aiops_envelope.py validate [schema.json [fixture.json ...]]
  python3 validate_aiops_envelope.py breaking <old.schema.json> <new.schema.json>

Exit codes: 0 = all valid / non-breaking, 1 = validation error or breaking, 2 = usage error.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = (
    ROOT / "qcloud-aiops-diagnosis" / "assets" / "aiops-envelope.schema.json"
)
DEFAULT_FIXTURES = (
    ROOT / "qcloud-aiops-diagnosis" / "assets" / "aiops-envelope.fixtures.json"
)


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
    if expected == "null":
        return value is None
    return True


def _check_obj(obj: dict, schema: dict, path: str, errors: list) -> None:
    for field in schema.get("required", []):
        if field not in obj:
            errors.append(f"{path}.{field}: missing required field")
    props = schema.get("properties", {})
    for field, value in obj.items():
        sub = props.get(field)
        if sub is None:
            if schema.get("additionalProperties") is False:
                errors.append(f"{path}.{field}: additional property not allowed")
            continue
        fpath = f"{path}.{field}"
        if "enum" in sub and value not in sub["enum"]:
            errors.append(f"{fpath}: {value!r} not in enum {sub['enum']}")
        if "const" in sub and value != sub["const"]:
            errors.append(f"{fpath}: expected const {sub['const']!r}, got {value!r}")
        if "type" in sub and not _type_ok(value, sub["type"]):
            errors.append(f"{fpath}: expected type {sub['type']}, got {type(value).__name__}")
        if "pattern" in sub and isinstance(value, str):
            import re

            if re.search(sub["pattern"], value) is None:
                errors.append(f"{fpath}: value {value!r} does not match pattern {sub['pattern']}")
        if sub.get("type") == "object" and isinstance(value, dict):
            _check_obj(value, sub, fpath, errors)
        if sub.get("type") == "array" and isinstance(value, list):
            items = sub.get("items")
            if isinstance(items, dict):
                for i, item in enumerate(value):
                    _check_obj(item, items, f"{fpath}[{i}]", errors)


def validate_fixtures(schema_path: Path, fixture_paths: list[Path]) -> int:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors: list = []
    count = 0
    for path in fixture_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        scenarios = data.get("scenarios", data) if isinstance(data, dict) else data
        if isinstance(scenarios, dict):
            items: list = [(name, rec) for name, rec in scenarios.items()]
        else:
            items = [(str(i), rec) for i, rec in enumerate(scenarios)]
        for name, rec in items:
            count += 1
            label = f"{path.name}:{name}"
            # fixture 是可选场景字段（不含 envelope 包装）。此处合成 wrap() 生成的
            # 包装字段（schema_version / event_id / timestamp），再用 schema 校验。
            rec = dict(rec)
            rec.setdefault("schema_version", "0.1")
            rec.setdefault("event_id", f"evt-{name[:12]}")
            rec.setdefault("timestamp", "2026-08-02T00:00:00Z")
            _check_obj(rec, schema, label, errors)
    if errors:
        for err in errors:
            print(f"FAIL {err}")
        return 1
    print(f"OK: {count} envelope fixture(s) valid against {schema_path.name}")
    return 0


def _breaking_changes(old: dict, new: dict) -> list:
    changes: list = []
    old_props = old.get("properties", {})
    new_props = new.get("properties", {})
    old_req = set(old.get("required", []))
    new_req = set(new.get("required", []))

    # 新增必填字段 = breaking（现有生产者会缺该字段）
    for field in sorted(new_req - old_req):
        changes.append(f"required +{field}: producers must now emit this field")
    # 保留 required 但字段被删 = breaking
    for field in sorted(old_req & new_req):
        if field not in new_props:
            changes.append(f"property {field}: required field removed")

    for field, new_sub in new_props.items():
        old_sub = old_props.get(field)
        if old_sub is None:
            continue
        # enum 收窄 = breaking
        if "enum" in new_sub and "enum" in old_sub and not set(old_sub["enum"]).issubset(set(new_sub["enum"])):
            changes.append(f"{field}: enum narrowed ({len(old_sub['enum'])} -> {len(new_sub['enum'])} values)")
        # const 变更 = breaking
        if "const" in new_sub and "const" in old_sub and new_sub["const"] != old_sub["const"]:
            changes.append(f"{field}: const changed {old_sub['const']!r} -> {new_sub['const']!r}")
    return changes


def detect_breaking(old_path: Path, new_path: Path) -> int:
    old = json.loads(old_path.read_text(encoding="utf-8"))
    new = json.loads(new_path.read_text(encoding="utf-8"))
    changes = _breaking_changes(old, new)
    if changes:
        for c in changes:
            print(f"BREAKING {c}")
        return 1
    print("OK: no breaking schema changes")
    return 0


def main(argv: list) -> int:
    if len(argv) < 2:
        sys.stderr.write(
            "usage: validate_aiops_envelope.py validate [schema.json [fixture.json ...]]\n"
            "       validate_aiops_envelope.py breaking <old.schema.json> <new.schema.json>\n"
        )
        return 2
    cmd = argv[1]
    if cmd == "validate":
        schema_path = Path(argv[2]) if len(argv) > 2 else DEFAULT_SCHEMA
        if len(argv) > 3:
            fixture_paths = [Path(p) for p in argv[3:]]
        else:
            fixture_paths = [DEFAULT_FIXTURES]
        return validate_fixtures(schema_path, fixture_paths)
    if cmd == "breaking":
        if len(argv) < 4:
            sys.stderr.write("usage: validate_aiops_envelope.py breaking <old.schema.json> <new.schema.json>\n")
            return 2
        return detect_breaking(Path(argv[2]), Path(argv[3]))
    sys.stderr.write(f"unknown command: {cmd!r}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
