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


def _find_yaml_dep_lines(yaml_path: Path) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    """
    Scan raw YAML lines for fix-suggestion anchors (detection logic unchanged).
    Returns ({tool: {atom: line_no}}, {tool: header_line}).
    """
    lines = yaml_path.read_text(encoding="utf-8").splitlines()
    deps: dict[str, dict[str, int]] = {}
    headers: dict[str, int] = {}
    seen_tools = False
    current_tool: str | None = None
    pending_item: str | None = None  # atom prefix from a `- tool: X` entry
    for lineno, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if raw.lstrip().startswith("tools:"):
            seen_tools = True
            continue
        if not seen_tools or not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^  ([A-Za-z_][\w]*):", raw)  # tool header at indent 2
        if m:
            current_tool = m.group(1)
            headers.setdefault(current_tool, lineno)
            deps.setdefault(current_tool, {})
            pending_item = None
            continue
        if current_tool is None:
            continue
        m = re.match(r"^\s+- tool:\s*([A-Za-z_][\w]*)", stripped)
        if m:
            pending_item = m.group(1)
            continue
        m = re.match(r"^\s+output:\s*([A-Za-z_][\w]*)", stripped)
        if m and pending_item:
            deps[current_tool].setdefault(f"{pending_item}.{m.group(1)}", lineno)
            pending_item = None
            continue
        if stripped in ("provides:", "dependency:", "requires:"):
            pending_item = None
    return deps, headers


def _find_py_atom_lines(py_path: Path) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    """
    Scan Python SPECS lines for fix-suggestion anchors (detection logic unchanged).
    Returns ({tool: {atom: line_no}}, {tool: header_line}).
    """
    lines = py_path.read_text(encoding="utf-8").splitlines()
    atoms: dict[str, dict[str, int]] = {}
    headers: dict[str, int] = {}
    current_tool: str | None = None
    for lineno, line in enumerate(lines, 1):
        m = re.search(r'tool_name\s*=\s*"([^"]+)"', line)
        if m:
            current_tool = m.group(1)
            headers.setdefault(current_tool, lineno)
            atoms.setdefault(current_tool, {})
            continue
        m = re.search(r'StateAtom\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"', line)
        if m and current_tool:
            atoms[current_tool].setdefault(f"{m.group(1)}.{m.group(2)}", lineno)
    return atoms, headers


FIX_TEMPLATE = "docs/superpowers/specs/yaml-drift-fix-template.md"


def fix_suggestions(
    tool: str,
    y_deps: list[str],
    p_deps: list[str],
    yaml_path: Path,
    py_path: Path,
    yaml_lines: dict[str, dict[str, int]],
    py_lines: dict[str, dict[str, int]],
    yaml_headers: dict[str, int],
    py_headers: dict[str, int],
) -> list[str]:
    """Actionable fix lines for a drifted tool (YAML = authoritative by design)."""
    missing_in_py = [d for d in y_deps if d not in p_deps]   # YAML has, PY lacks
    missing_in_yaml = [d for d in p_deps if d not in y_deps]  # PY has, YAML lacks
    out: list[str] = []
    if missing_in_py:
        anchor = py_headers.get(tool) or min((py_lines.get(tool, {}).get(a) for a in missing_in_py if a in py_lines.get(tool, {})), default=0)
        out.append(f"  → FIX (YAML 权威): {py_path}:{anchor} 补 StateAtom 依赖 {missing_in_py}")
    if missing_in_yaml:
        anchor = yaml_headers.get(tool) or min((yaml_lines.get(tool, {}).get(a) for a in missing_in_yaml if a in yaml_lines.get(tool, {})), default=0)
        out.append(f"  → FIX (PY 权威):   {yaml_path}:{anchor} 删 requires 依赖 {missing_in_yaml}")
    if out:
        out.append("  → 决策依据: 业务上该依赖是否真实前置? 是→补 PY; 否→改 YAML (见决策矩阵)")
        out.append(f"  → 完整模板: {FIX_TEMPLATE}")
    return out


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

    # Line anchors for fix suggestions (output only — detection logic unchanged)
    yaml_lines, yaml_headers = _find_yaml_dep_lines(yaml_path)
    py_lines, py_headers = _find_py_atom_lines(py_path)

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
                for fix_line in fix_suggestions(
                    tool, y_deps, p_deps, yaml_path, py_path,
                    yaml_lines, py_lines, yaml_headers, py_headers,
                ):
                    errors.append(fix_line)

    for w in warnings:
        print(f"WARN {w}")
    for e in errors:
        if e.startswith("  →"):
            print(e)
        else:
            print(f"✗ {e}")

    n_errors = len([e for e in errors if not e.startswith("  →")])
    n_warns = len(warnings)
    print(f"\nSUMMARY: {n_errors} tool(s) drifted, {n_warns} warning(s)")
    sys.exit(1 if n_errors else 0)


if __name__ == "__main__":
    main()
