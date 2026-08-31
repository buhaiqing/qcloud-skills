#!/usr/bin/env python3
"""
check_yaml_python_drift.py — P2
Check references/*/tool_state_schema.yaml vs corresponding Python SPECS dict.
Verify tool dependency.requires lists match (YAML = single source of truth).
Exit 0 = in sync, 1 = drift detected.
"""
import argparse
import re
import sys
from pathlib import Path

import yaml


def parse_yaml_deps(yaml_path: Path) -> dict[str, list[str]]:
    """
    Parse tool_state_schema.yaml → {tool_name: [sorted requires atoms]}.
    An atom = "tool.output_key".
    """
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    result = {}
    tools = data.get("tools", {})
    for tool_name, spec in tools.items():
        deps = spec.get("dependency", {}).get("requires", [])
        atoms = []
        for d in deps:
            if isinstance(d, dict) and "tool" in d and "output" in d:
                atoms.append(f"{d['tool']}.{d['output']}")
            # skip entries without output (implicit deps) or string shorthand
        result[tool_name] = sorted(atoms)
    return result


def _match_balanced(text: str, start: int) -> tuple[int, str]:
    """Find the matching ')' for '(' at position start. Returns (end_pos, block)."""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return i + 1, text[start:i + 1]
        i += 1
    return i, text[start:]


def parse_python_deps(py_path: Path) -> dict[str, list[str]]:
    """
    Parse state_dependency.py → {tool_name: [sorted requires atoms]}.
    Extracts from StateAtom("tool", "output") in SPECS dict.
    Handles nested parentheses by counting balanced parens.
    """
    text = py_path.read_text(encoding="utf-8")
    result = {}
    pos = 0
    while True:
        m = re.search(r'ToolStateSpec\s*\(', text[pos:])
        if not m:
            break
        start = pos + m.start()
        end, block = _match_balanced(text, start)
        tn_m = re.search(r'tool_name\s*=\s*"([^"]+)"', block)
        if tn_m:
            tool_name = tn_m.group(1)
            atoms = re.findall(r'StateAtom\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"', block)
            result[tool_name] = sorted(f"{a}.{b}" for a, b in atoms)
        pos = end
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Check YAML vs Python state dependency declarations for drift."
    )
    parser.add_argument(
        "--yaml",
        default="references/toolgrounding/tool_state_schema.yaml",
        help="Path to tool_state_schema.yaml",
    )
    parser.add_argument(
        "--py",
        default="references/toolgrounding/state_dependency.py",
        help="Path to state_dependency.py",
    )
    args = parser.parse_args()

    yaml_path = Path(args.yaml)
    py_path = Path(args.py)

    if not yaml_path.exists():
        print(f"ERROR: YAML not found: {yaml_path}", file=sys.stderr)
        sys.exit(1)
    if not py_path.exists():
        print(f"ERROR: Python not found: {py_path}", file=sys.stderr)
        sys.exit(1)

    try:
        yaml_deps = parse_yaml_deps(yaml_path)
    except (yaml.YAMLError, KeyError, TypeError) as e:
        print(f"ERROR parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)

    py_deps = parse_python_deps(py_path)

    errors = []
    warnings = []

    # All tools in YAML must match Python
    all_tools = set(yaml_deps.keys()) | set(py_deps.keys())

    for tool in sorted(all_tools):
        y_deps = yaml_deps.get(tool, [])
        p_deps = py_deps.get(tool, [])

        if tool not in yaml_deps:
            warnings.append(f"{tool}: in PY=[{', '.join(p_deps)}] but not in YAML")
        elif tool not in py_deps:
            # YAML has it, Python doesn't — not an error (YAML is authoritative for now)
            pass
        else:
            if y_deps != p_deps:
                errors.append(
                    f"{tool}: YAML=[{', '.join(y_deps)}], PY=[{', '.join(p_deps)}]"
                )

    for w in warnings:
        print(f"WARN {w}")
    for e in errors:
        print(f"✗ {e}")

    n_errors = len(errors)
    n_warns = len(warnings)
    print(f"\nSUMMARY: {n_errors} tool(s) drifted, {n_warns} warning(s)")
    sys.exit(1 if n_errors else 0)


if __name__ == "__main__":
    main()
