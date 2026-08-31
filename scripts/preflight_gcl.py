#!/usr/bin/env python3
"""Pre-flight GCL budget check — run before starting a GCL loop.

Usage:
  python3 scripts/preflight_gcl.py --complexity medium --agents 4
  python3 scripts/preflight_gcl.py --task-routing worker_fix --agents 2
  python3 scripts/preflight_gcl.py --complexity high --agents 3 --budget 120000

Exit codes: 0=ok (budget sufficient), 1=exceeds budget
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET_FILE = ROOT / "scripts" / "gcl-budget.yaml"


def load_budget() -> dict:
    try:
        import yaml
        return yaml.safe_load(BUDGET_FILE.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return {}


def resolve_pricing(model: str, budget: dict) -> tuple[float, float]:
    pricing = budget.get("model_pricing", {})
    for k in (model, model.replace("minimax-cn/", ""), model.split("/")[-1]):
        if k in pricing:
            p = pricing[k]
            return float(p["input"]), float(p["output"])
    return 0.0001, 0.0003  # fallback


def cost_usd(tokens: int, model: str, budget: dict) -> float:
    inp_rate, out_rate = resolve_pricing(model, budget)
    inp = int(tokens * 0.3)
    out = tokens - inp
    return (inp / 1000) * inp_rate + (out / 1000) * out_rate


def estimate_by_complexity(complexity: str, num_agents: int, budget: dict) -> tuple[int, float]:
    comp = budget.get("complexity_budget", {})
    est_per_agent = comp.get(complexity, 15000)
    total = est_per_agent * num_agents
    # 70% M2.7, 30% M3
    c = cost_usd(int(total * 0.7), "MiniMax-M2.7", budget)
    c += cost_usd(int(total * 0.3), "MiniMax-M3", budget)
    return total, c


def estimate_by_routing(routing_key: str, num_agents: int, budget: dict) -> tuple[int, float]:
    routing = budget.get("task_routing", {})
    entry = routing.get(routing_key, {})
    est_per_agent = int(entry.get("est_tokens", 15000))
    model = entry.get("model", "MiniMax-M2.7")
    total = est_per_agent * num_agents
    c = cost_usd(total, model, budget)
    return total, c


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--complexity", choices=["low", "medium", "high"],
                        help="Complexity level (overrides --task-routing)")
    parser.add_argument("--agents", type=int, default=4)
    parser.add_argument("--task-routing", dest="routing_key",
                        help="Use task_routing entry from gcl-budget.yaml")
    parser.add_argument("--budget", type=int, default=None,
                        help="Override total budget from gcl-budget.yaml")
    args = parser.parse_args()

    budget = load_budget()
    defaults = budget.get("defaults", {})
    total_budget = args.budget or defaults.get("total_budget", 80000)
    warn_t = defaults.get("warn_threshold", 0.8)
    abort_t = defaults.get("abort_threshold", 1.2)

    if args.complexity:
        est_tokens, est_cost = estimate_by_complexity(args.complexity, args.agents, budget)
        source = f"complexity={args.complexity}"
    elif args.routing_key:
        est_tokens, est_cost = estimate_by_routing(args.routing_key, args.agents, budget)
        source = f"task_routing={args.routing_key}"
    else:
        print("ERROR: specify --complexity or --task-routing", file=sys.stderr)
        return 2

    ratio = est_tokens / total_budget if total_budget else 0

    print(f"\n{'='*50}")
    print("  GCL Pre-flight Check")
    print(f"{'='*50}")
    print(f"  Mode:            {source}")
    print(f"  Agents:          {args.agents}")
    print(f"  Est tokens:      {est_tokens:,}")
    print(f"  Est cost:        ~${est_cost:.4f}")
    print(f"  Budget:          {total_budget:,}")
    print(f"  Usage:           {ratio*100:.1f}% of budget")
    print(f"  Warn @:          {warn_t*100:.0f}%  |  Abort @: {abort_t*100:.0f}%")
    print()

    if ratio >= abort_t:
        print(f"  Status:          🔴 ABORT — exceeds {abort_t*100:.0f}% threshold")
        print(f"  Headroom:        {total_budget - est_tokens:,} tokens")
        print("  → Reduce agents or complexity before proceeding")
        print()
        return 1
    elif ratio >= warn_t:
        print(f"  Status:          🟡 WARN — hits {warn_t*100:.0f}% threshold")
        print(f"  Headroom:        {total_budget - est_tokens:,} tokens")
        print("  → Proceed with caution; monitor closely")
        print()
        return 0
    else:
        print(f"  Status:          🟢 OK — {total_budget - est_tokens:,} headroom")
        print("  → Safe to launch GCL loop")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
