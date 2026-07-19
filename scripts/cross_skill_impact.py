#!/usr/bin/env python3
"""cross_skill_impact.py — Cross-skill dependency graph and impact analysis.

Builds a directed dependency graph from qcloud-*-ops/SKILL.md files by parsing:
  - YAML frontmatter `related_skills:` entries
  - Markdown body `delegate-to:` markers

Then answers:
  1. Which skills does skill X depend on?  (reverse reachability)
  2. If skill X degrades, which downstream skills are affected?  (forward propagation)
  3. What is the topological execution order?  (Kahn's algorithm)

Usage:
  python3 scripts/cross_skill_impact.py graph
  python3 scripts/cross_skill_impact.py impact --skill qcloud-aiops-diagnosis
  python3 scripts/cross_skill_impact.py critical-path --skill qcloud-aiops-diagnosis
  python3 scripts/cross_skill_impact.py topological-order
  python3 scripts/cross_skill_impact.py self-verify
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = ROOT / "qcloud-*-ops"

# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

DELEGATE_RE = re.compile(r"`([^`]+)`")
RELATED_RE  = re.compile(r"`qcloud-[a-z0-9]+-ops`")


def _parse_related_skills(skill_dir: Path) -> set[str]:
    """Extract related_skills from YAML frontmatter of SKILL.md."""
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return set()
    text = skill_file.read_text(encoding="utf-8")
    # Extract YAML frontmatter
    if not text.startswith("---"):
        return set()
    end = text.find("---", 3)
    if end < 0:
        return set()
    frontmatter = text[3:end]
    skills: set[str] = set()
    for line in frontmatter.splitlines():
        if line.strip().startswith("- "):
            val = line.strip()[2:].strip()
            if val.startswith("qcloud-") and val.endswith("-ops"):
                skills.add(val)
        elif "qcloud-" in line and "-ops" in line:
            for m in RELATED_RE.findall(line):
                skills.add(m)
    return skills


def _parse_delegate_to(skill_dir: Path) -> set[str]:
    """Extract delegate-to skill names from SKILL.md markdown body."""
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return set()
    text = skill_file.read_text(encoding="utf-8")
    # Find YAML frontmatter end
    if text.startswith("---"):
        end = text.find("---", 3)
        if end >= 0:
            text = text[end + 3:]
    targets: set[str] = set()
    # Match backtick-quoted skill names
    for m in DELEGATE_RE.findall(text):
        m = m.strip()
        if m.startswith("qcloud-") and m.endswith("-ops"):
            targets.add(m)
    return targets


def build_graph() -> tuple[dict[str, set[str]], dict[str, str]]:
    """Build adjacency list and label map from all skill directories.

    Returns (graph, labels) where:
      graph[x] = set of skills x depends on (incoming edges)
      labels[x] = human-readable skill name
    """
    import glob
    skill_dirs = glob.glob(str(OPS_DIR))
    graph: dict[str, set[str]] = defaultdict(set)
    labels: dict[str, str] = {}

    for sd in sorted(skill_dirs):
        sd_path = Path(sd)
        skill_id = sd_path.name  # e.g. "qcloud-cvm-ops"
        # Label from directory name
        labels[skill_id] = skill_id.replace("qcloud-", "").replace("-ops", "").replace("-", " ").title()
        # Incoming edges: other skills that this skill references
        related = _parse_related_skills(sd_path)
        delegates = _parse_delegate_to(sd_path)
        for dep in related | delegates:
            graph[skill_id].add(dep)

    return graph, labels


# ---------------------------------------------------------------------------
# Graph algorithms
# ---------------------------------------------------------------------------

def propagate_degradation(
    skill: str,
    graph: dict[str, set[str]],
    labels: dict[str, str],
    max_depth: int = 5,
) -> list[dict[str, Any]]:
    """BFS forward: find all skills affected if `skill` degrades.

    Returns list of {skill, depth, path} sorted by depth.
    """
    result = []
    visited = {skill}
    queue = deque([(skill, 0, [skill])])

    while queue:
        current, depth, path = queue.popleft()
        result.append({
            "skill": current,
            "depth": depth,
            "path": " → ".join(path),
            "label": labels.get(current, current),
        })
        if depth >= max_depth:
            continue
        for neighbor in graph.get(current, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1, path + [neighbor]))

    result.sort(key=lambda x: x["depth"])
    return result


def topological_order(
    graph: dict[str, set[str]],
    labels: dict[str, str],
) -> list[dict[str, Any]]:
    """Kahn's algorithm — return skills in dependency order (foundational first).

    graph[A] = set of skills A depends on (A's prerequisite skills).
    in_degree[X] = number of prerequisites X has.
    Nodes with no prerequisites (leaves) are processed first, then their dependents.
    """
    all_nodes: set[str] = set(graph.keys())
    for neighbors in graph.values():
        all_nodes |= neighbors

    # in_degree[X] = number of skills X depends on (X's prerequisites)
    in_degree = {n: len(graph.get(n, set())) for n in all_nodes}

    # Start with skills that have no prerequisites
    queue = sorted([n for n in all_nodes if in_degree[n] == 0], key=lambda n: labels.get(n, n))
    result = []
    removed: set[str] = set()

    while queue:
        node = queue.pop(0)
        if node in removed:
            continue
        removed.add(node)
        result.append({"skill": node, "label": labels.get(node, node), "in_degree": in_degree[node]})
        # For each skill S that depends on `node` (i.e., node is in S's prerequisites),
        # decrement S's in_degree; when it reaches 0, S is ready to process.
        for src, prereqs in graph.items():
            if node in prereqs and src not in removed:
                in_degree[src] -= 1
                if in_degree[src] == 0:
                    queue.append(src)
                    queue.sort(key=lambda n: labels.get(n, n))

    if len(result) != len(all_nodes):
        return [{"error": "cycle detected in dependency graph"}] + result
    return result


def render_graph(graph: dict[str, set[str]], labels: dict[str, str]) -> str:
    """Render adjacency list as ASCII art grouped by dependency depth."""
    lines = ["Cross-Skill Dependency Graph", "=" * 50]
    ordered = topological_order(graph, labels)

    for node in reversed(ordered):  # leaves first = most foundational
        if not isinstance(node, dict) or "skill" not in node:
            continue  # skip error dicts
        indent = "  " * node.get("in_degree", 0)
        deps = graph.get(node["skill"], set())
        dep_labels = ", ".join(sorted(labels.get(d, d) for d in deps)) or "(none)"
        lines.append(f"{indent}[{node['skill']}] ({node['label']}) ← {dep_labels}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_graph(_args: argparse.Namespace) -> int:
    graph, labels = build_graph()
    print(render_graph(graph, labels))
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    graph, labels = build_graph()
    affected = propagate_degradation(args.skill, graph, labels)
    if not affected:
        print(f"No downstream skills found for '{args.skill}'.")
        return 0
    print(f"Impact propagation from '{args.skill}' ({labels.get(args.skill, args.skill)}):")
    print(f"  {'Skill':<35} {'Depth':<8} {'Path'}")
    print(f"  {'-'*35} {'-'*8} {'-'*40}")
    for item in affected:
        print(f"  {item['skill']:<35} {item['depth']:<8} {item['path']}")
    return 0


def cmd_critical_path(args: argparse.Namespace) -> int:
    graph, labels = build_graph()
    affected = propagate_degradation(args.skill, graph, labels, max_depth=99)
    if not affected:
        print(f"No path from '{args.skill}'.")
        return 0
    # Longest path (max depth)
    longest = max(affected, key=lambda x: x["depth"]) if affected else None
    if longest:
        print(f"Longest impact path from '{args.skill}':")
        print(f"  {longest['path']}")
        print(f"  Depth: {longest['depth']}")
    # Show top N by depth
    print(f"\nAll affected skills ({len(affected)} total):")
    for item in sorted(affected, key=lambda x: -x["depth"])[: args.top_n]:
        print(f"  [{item['depth']}] {item['skill']} ({item['label']})")
    return 0


def cmd_topo(args: argparse.Namespace) -> int:
    graph, labels = build_graph()
    ordered = topological_order(graph, labels)
    valid = [n for n in ordered if isinstance(n, dict) and "skill" in n]
    if len(valid) != len(ordered):
        print("WARNING: cycle detected in dependency graph", file=sys.stderr)
    print("Topological execution order (foundational → dependent):")
    print(f"  {'#':<4} {'Skill':<35} {'In-degree':<12} {'Label'}")
    print(f"  {'-'*4} {'-'*35} {'-'*12} {'-'*20}")
    for i, node in enumerate(valid, 1):
        print(f"  {i:<4} {node['skill']:<35} {node.get('in_degree', 0):<12} {node['label']}")
    return 0


# ---------------------------------------------------------------------------
# Self-verification
# ---------------------------------------------------------------------------

def self_verify() -> bool:
    """Synthetic graph → verify propagation and topo sort."""
    # Manual mini-graph
    synthetic = {
        "qcloud-proactive-inspection": {"qcloud-cvm-ops", "qcloud-redis-ops"},
        "qcloud-aiops-diagnosis": {"qcloud-tke-ops", "qcloud-cvm-ops", "qcloud-monitor-ops"},
        "qcloud-finops-ops": {"qcloud-proactive-inspection", "qcloud-aiops-diagnosis"},
    }
    synth_labels = {
        "qcloud-proactive-inspection": "Proactive Inspection",
        "qcloud-aiops-diagnosis": "AIOps Diagnosis",
        "qcloud-finops-ops": "FinOps",
        "qcloud-cvm-ops": "CVM",
        "qcloud-redis-ops": "Redis",
        "qcloud-tke-ops": "TKE",
        "qcloud-monitor-ops": "Monitor",
    }

    # Test propagate
    affected = propagate_degradation("qcloud-proactive-inspection", synthetic, synth_labels)
    has_cvm = any(a["skill"] == "qcloud-cvm-ops" for a in affected)
    print(f"  [{'PASS' if has_cvm else 'FAIL'}] propagate_degradation finds CVM from proactive-inspection")
    if not has_cvm:
        return False

    # Test finops propagates to all 7 reachable nodes (including transitive deps)
    all_affected = propagate_degradation("qcloud-finops-ops", synthetic, synth_labels, max_depth=99)
    reachable = {a["skill"] for a in all_affected}
    # finops → proactive/aiops → their deps → TKE's deps (none), CVM's deps (none)
    expected = {
        "qcloud-proactive-inspection", "qcloud-aiops-diagnosis",
        "qcloud-finops-ops", "qcloud-cvm-ops", "qcloud-redis-ops",
        "qcloud-tke-ops", "qcloud-monitor-ops",
    }
    match = reachable == expected
    print(f"  [{'PASS' if match else 'FAIL'}] finops propagates to all {len(expected)} reachable: {reachable}")
    if not match:
        return False

    # Test topo sort: prerequisites always come before dependents
    ordered = topological_order(synthetic, synth_labels)
    names = [n["skill"] for n in ordered if "skill" in n]
    # Check all prerequisite→dependent ordering
    checks = [
        ("qcloud-finops-ops", "qcloud-proactive-inspection"),
        ("qcloud-finops-ops", "qcloud-aiops-diagnosis"),
        ("qcloud-proactive-inspection", "qcloud-cvm-ops"),
        ("qcloud-proactive-inspection", "qcloud-redis-ops"),
        ("qcloud-aiops-diagnosis", "qcloud-tke-ops"),
        ("qcloud-aiops-diagnosis", "qcloud-cvm-ops"),
        ("qcloud-aiops-diagnosis", "qcloud-monitor-ops"),
    ]
    ok = True
    for dependent, prereq in checks:
        pi = names.index(prereq)
        di = names.index(dependent)
        if not (pi < di):
            print(f"  [FAIL] {prereq} (idx {pi}) should come before {dependent} (idx {di})")
            ok = False
    print(f"  [{'PASS' if ok else 'FAIL'}] topological: all prerequisites before dependents")
    if not ok:
        return False

    print("  [PASS] self-verify: all checks passed")
    return True

# ---------------------------------------------------------------------------
# CLI builder
# ---------------------------------------------------------------------------

def _cmd_self_verify(_):
    return 0 if self_verify() else 1

def _cmd_self_verify(_):
    return 0 if self_verify() else 1

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("graph", help="Print dependency graph").set_defaults(func=cmd_graph)
    ip = sub.add_parser("impact", help="Show skills affected if a skill degrades")
    ip.add_argument("--skill", required=True, help="Skill name, e.g. qcloud-aiops-diagnosis")
    ip.set_defaults(func=cmd_impact)
    cp = sub.add_parser("critical-path", help="Show longest impact chain")
    cp.add_argument("--skill", required=True)
    cp.add_argument("--top-n", type=int, default=10)
    cp.set_defaults(func=cmd_critical_path)
    tp = sub.add_parser("topological-order", help="Execution order (foundational first)")
    tp.set_defaults(func=cmd_topo)
    sv = sub.add_parser("self-verify")
    sv.set_defaults(func=_cmd_self_verify)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
