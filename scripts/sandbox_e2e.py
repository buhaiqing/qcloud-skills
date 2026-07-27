"""Sandbox E2E golden-scenario matcher (stdlib only).

Walks <skill-dir>/golden/*.json, loads each scenario, reads the referenced
fixture (relative to skill-dir), and runs JSON-pointer assertions. Exit codes:
  0  all golden scenarios match
  1  one or more golden mismatches (GOLDEN MISMATCH printed)
  2  usage / structural error
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, List


def get_path(obj: Any, pointer: str) -> Any:
    """Resolve a `$.a.b[0].c` style pointer against obj.

    Raises KeyError on a missing dict key, IndexError on an out-of-range list
    index, ValueError on a malformed pointer segment.
    """
    if not pointer.startswith("$"):
        raise ValueError(f"pointer must start with '$': {pointer}")
    segment_re = re.compile(r"\.([^.\[\]]+)|\[(\d+)\]")
    pos = 1  # skip leading '$'
    current: Any = obj
    last_end = pos
    for match in segment_re.finditer(pointer, pos):
        key, idx = match.group(1), match.group(2)
        if idx is not None:
            current = current[int(idx)]
        else:
            current = current[key]
        last_end = match.end()
    # A trailing unparsed tail (e.g. "$.a." or "$.a@b") means a malformed
    # pointer — raise instead of silently returning the wrong value.
    if last_end != len(pointer):
        raise ValueError(f"malformed pointer tail: {pointer[last_end:]!r} in {pointer!r}")
    return current


def _eval_assertion(target: Any, assertion: dict) -> None:
    """Run one assertion; raise ValueError describing the failure."""
    path = assertion["path"]
    op = assertion["op"]
    try:
        actual = get_path(target, path)
    except (KeyError, IndexError) as exc:
        raise ValueError(f"path {path} not found: {exc}") from exc
    except ValueError as exc:
        raise ValueError(f"path {path} invalid: {exc}") from exc

    if op == "exists":
        return
    if op == "exists_not":
        raise ValueError(f"path {path} exists but op=exists_not")
    if op == "==":
        if actual != assertion["value"]:
            raise ValueError(f"path {path}: {actual!r} != {assertion['value']!r}")
        return
    if op == ">=":
        if not actual >= assertion["value"]:
            raise ValueError(f"path {path}: {actual!r} < {assertion['value']!r}")
        return
    raise ValueError(f"unknown op: {op}")


def check_scenario(scenario: dict, skill_dir: Path) -> List[str]:
    """Return a list of failure messages (empty == pass)."""
    failures: List[str] = []
    expected = scenario.get("expected")
    if not isinstance(expected, dict):
        return ["scenario missing 'expected'"]
    fixture_rel = expected.get("fixture")
    if not fixture_rel:
        return ["scenario missing 'expected.fixture'"]
    fixture_path = skill_dir / fixture_rel
    try:
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        return [f"fixture not found: {fixture_rel} ({exc})"]
    except json.JSONDecodeError as exc:
        return [f"fixture invalid JSON: {fixture_rel} ({exc})"]

    intent = scenario.get("intent", "<no intent>")
    for assertion in expected.get("assertions", []):
        try:
            _eval_assertion(fixture, assertion)
        except ValueError as exc:
            failures.append(f"[{intent}] {exc}")
    return failures


def main(argv: List[str]) -> int:
    args = argv[1:]
    if len(args) != 2 or args[0] != "--skill-dir":
        print("usage: sandbox_e2e.py --skill-dir <path>", file=sys.stderr)
        return 2
    skill_dir = Path(args[1])
    golden_dir = skill_dir / "assets" / "golden"
    if not golden_dir.is_dir():
        golden_dir = skill_dir / "golden"
    if not golden_dir.is_dir():
        print(f"GOLDEN MISMATCH: no golden/ dir in {skill_dir}", file=sys.stderr)
        return 2

    all_failures: List[str] = []
    scenario_files = sorted(golden_dir.glob("*.json"))
    if not scenario_files:
        print(f"GOLDEN MISMATCH: no scenarios in {golden_dir}", file=sys.stderr)
        return 1
    for sf in scenario_files:
        try:
            scenario = json.loads(sf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            all_failures.append(f"{sf.name}: invalid JSON ({exc})")
            continue
        all_failures.extend(check_scenario(scenario, skill_dir))

    if all_failures:
        print("GOLDEN MISMATCH:", file=sys.stderr)
        for msg in all_failures:
            print(f"  - {msg}", file=sys.stderr)
        return 1
    print(f"GOLDEN OK: {len(scenario_files)} scenario(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
