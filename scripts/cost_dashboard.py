#!/usr/bin/env python3
"""GCL Cost Dashboard — token budget tracking and cost visualization.

Usage:
  python3 scripts/cost_dashboard.py                      # dashboard
  python3 scripts/cost_dashboard.py --estimate --complexity medium --agents 4  # dry-run estimate
  python3 scripts/cost_dashboard.py --self-test          # internal checks
  python3 scripts/cost_dashboard.py --strict             # exit 1 if any loop exceeded budget

Exit codes: 0=ok, 1=exceeded budget (--strict only)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUDGET_FILE = ROOT / "scripts" / "gcl-budget.yaml"
AUDIT_DIR = ROOT / "audit-results"


def load_budget() -> dict[str, Any]:
    try:
        import yaml
        data = yaml.safe_load(BUDGET_FILE.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as e:
        print(f"WARN: could not load {BUDGET_FILE}: {e}", file=sys.stderr)
        return _default_budget()
    if not isinstance(data, dict):
        raise TypeError("gcl-budget.yaml must be a dict")
    return data


def _default_budget() -> dict[str, Any]:
    return {
        "defaults": {"total_budget": 80000, "warn_threshold": 0.8, "abort_threshold": 1.2},
        "model_pricing": {
            "minimax-cn/MiniMax-M2.7": {"input": 0.0001, "output": 0.0003},
            "minimax-cn/MiniMax-M3": {"input": 0.0003, "output": 0.0009},
            "MiniMax-M2.7": {"input": 0.0001, "output": 0.0003},
            "MiniMax-M3": {"input": 0.0003, "output": 0.0009},
        },
        "task_routing": {},
        "complexity_budget": {"low": 20000, "medium": 60000, "high": 120000},
    }


def _resolve_model(key: str, budget: dict[str, Any]) -> dict[str, float]:
    pricing = budget.get("model_pricing", {})
    for k in (key, key.replace("minimax-cn/", ""), key.split("/")[-1]):
        if k in pricing:
            return pricing[k]
    return {"input": 0.0001, "output": 0.0003}  # safe fallback


def _tokens_from_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Extract token usage from a trace. Schema may vary; extract what's available."""
    # Priority: explicit usage fields
    if "usage" in trace:
        return dict(trace["usage"])
    # Legacy orchestrator trace (gcl-trace-YYYYMMDD-HHMMSS.json)
    if "agents" in trace:
        total = 0
        for a in trace["agents"]:
            # tokens may be stored per-agent if populated
            for k in ("input_tokens", "output_tokens", "tokens"):
                total += int(a.get(k) or 0)
        if total:
            return {"total": total}
    # GCL iteration traces may embed usage in generator/critic
    iters = trace.get("iterations") or []
    total = 0
    for it in iters:
        for node in ("generator", "critic"):
            n = it.get(node) or {}
            for k in ("input_tokens", "output_tokens", "tokens"):
                total += int(n.get(k) or 0)
    if total:
        return {"total": total}
    # Fallback: estimate from trace metadata
    trace.get("task_id") or trace.get("skill") or "unknown"
    complexity = trace.get("complexity", 5)
    est = complexity * 2000
    return {"total": est, "_estimated": True}


def _cost_usd(tokens: int, model: str, budget: dict[str, Any]) -> float:
    p = _resolve_model(model, budget)
    # rough: 30% input, 70% output
    inp = int(tokens * 0.3)
    out = tokens - inp
    return (inp / 1000) * p["input"] + (out / 1000) * p["output"]


def _mini_chart(values: list[float], width: int = 30) -> str:
    if not values:
        return ""
    lo, hi = min(values), max(values)
    rng = hi - lo if hi != lo else 1
    bar = "".join("█" * max(1, int((v - lo) / rng * width)) for v in values)
    return bar


def _status_emoji(used: int, budget_total: int, warn: float, abort: float) -> str:
    ratio = used / budget_total if budget_total else 0
    if ratio >= abort:
        return "🔴"
    if ratio >= warn:
        return "🟡"
    return "🟢"


def _collect_traces(limit: int | None = None) -> list[tuple[Path, dict[str, Any]]]:
    if not AUDIT_DIR.is_dir():
        return []
    paths = sorted(AUDIT_DIR.glob("gcl-trace-*.json"), reverse=True)
    results: list[tuple[Path, dict[str, Any]]] = []
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            results.append((p, data))
        except (json.JSONDecodeError, OSError):
            continue
        if limit and len(results) >= limit:
            break
    return results


def _format_timestamp(path: Path) -> str:
    name = path.stem  # e.g. gcl-trace-20260719-154038
    ts = name.replace("gcl-trace-", "")
    try:
        dt = datetime.strptime(ts, "%Y%m%d-%H%M%S").replace(tzinfo=UTC)
        return dt.strftime("%m-%d %H:%M")
    except ValueError:
        return ts


def _summarize_trace(p: Path, data: dict[str, Any], budget: dict[str, Any]) -> dict[str, Any]:
    tokens = _tokens_from_trace(data)
    total = tokens.get("total", 0)
    estimated = tokens.get("_estimated", False)

    defaults = budget.get("defaults", {})
    budget_total = defaults.get("total_budget", 80000)
    warn_t = defaults.get("warn_threshold", 0.8)
    abort_t = defaults.get("abort_threshold", 1.2)

    ratio = total / budget_total if budget_total else 0

    # Determine model for cost
    model = "MiniMax-M2.7"
    if data.get("agents"):
        model = data["agents"][0].get("model", model)
    elif "model" in data:
        model = data["model"]

    cost = _cost_usd(total, model, budget)
    status = _status_emoji(total, budget_total, warn_t, abort_t)

    return {
        "path": p,
        "task": data.get("task_id") or data.get("skill") or "?",
        "total_tokens": total,
        "estimated": estimated,
        "cost_usd": round(cost, 6),
        "budget_total": budget_total,
        "ratio": round(ratio, 3),
        "warn_threshold": warn_t,
        "abort_threshold": abort_t,
        "status": status,
        "model": model,
    }


def cmd_dashboard(budget: dict[str, Any]) -> int:
    traces = _collect_traces()
    if not traces:
        print("No gcl-trace files found in audit-results/.")
        return 0

    defaults = budget.get("defaults", {})
    budget_total = defaults.get("total_budget", 80000)
    warn_t = defaults.get("warn_threshold", 0.8)
    abort_t = defaults.get("abort_threshold", 1.2)

    summaries = []
    for p, data in traces:
        summaries.append(_summarize_trace(p, data, budget))

    # Latest loop detail
    latest = summaries[0]
    print(f"\n{'='*60}")
    print("  GCL Cost Dashboard")
    print(f"{'='*60}")
    print(f"  Latest Loop: {_format_timestamp(latest['path'])} | {latest['task']}")
    print(f"  Model: {latest['model']}")
    if latest['estimated']:
        print("  ⚠️  Token data not available — used estimate (complexity-based)")
    print()
    print("  Token Usage (latest):")
    print(f"    Total:       {latest['total_tokens']:,} tokens")
    print(f"    Cost:        ${latest['cost_usd']:.6f}")
    print(f"    Budget:      {budget_total:,} tokens")
    print(f"    Usage:       {latest['ratio']*100:.1f}%  {latest['status']}")
    print()

    # By-agent buckets (if available)
    latest_data = traces[0][1]
    if "agents" in latest_data:
        print("  By Agent:")
        for a in latest_data["agents"]:
            lbl = a.get("label", "?")
            tkn = sum(int(a.get(k, 0)) for k in ("input_tokens", "output_tokens", "tokens"))
            if tkn == 0:
                tkn = int(a.get("complexity", 5) or 5) * 2000
            print(f"    {lbl}: ~{tkn:,} tokens")
        print()

    # By-model buckets
    budget.get("model_pricing", {})
    model_totals: dict[str, int] = {}
    for s in summaries:
        m = s["model"]
        model_totals[m] = model_totals.get(m, 0) + s["total_tokens"]
    if model_totals:
        print(f"  By Model (cumulative across {len(summaries)} loops):")
        for m, t in sorted(model_totals.items(), key=lambda x: -x[1]):
            c = _cost_usd(t, m, budget)
            print(f"    {m}: {t:,} tokens, ~${c:.4f}")
        print()

    # Historical trend (last 5)
    recent = summaries[:5]
    print(f"  Budget vs Usage (last {len(recent)} loops):")
    header = "  Loop      Task                      Used%   Tokens     Status"
    print(f"  {header}")
    print(f"  {'-'*len(header)}")
    for s in recent:
        label = s["task"][:25].ljust(25)
        used_pct = f"{s['ratio']*100:5.1f}%"
        tkn = f"{s['total_tokens']:>8,}"
        status = s["status"]
        print(f"  {_format_timestamp(s['path'])}  {label}  {used_pct}  {tkn}  {status}")
    print()

    # Mini chart
    if len(recent) > 1:
        vals = [s["ratio"] for s in reversed(recent)]
        chart = _mini_chart(vals, 25)
        print(f"  Trend (min→max): {chart}")
        print(f"  {0:.0%}".ljust(len(chart), " ") + f" {max(vals):.0%}")
        print()

    # Budget config
    print("  Budget Config:")
    print(f"    total_budget: {budget_total:,}")
    print(f"    warn @ {warn_t*100:.0f}%  |  abort @ {abort_t*100:.0f}%")
    print()

    # Suggestions
    exceeded = [s for s in summaries if s["ratio"] >= warn_t]
    if exceeded:
        print("  Suggestions:")
        print(f"    🔔 {len(exceeded)} loop(s) hit ≥{warn_t*100:.0f}% budget")
        print("    → Consider splitting into smaller subagent batches")
        print("    → Switch blind_review to M2.7 if task allows")
        print()

    return 0


def cmd_estimate(budget: dict[str, Any], complexity: str, num_agents: int) -> int:
    comp_budget = budget.get("complexity_budget", {})
    default_est = 15000
    est_tokens = comp_budget.get(complexity, default_est)
    total_est = est_tokens * num_agents

    defaults = budget.get("defaults", {})
    budget_total = defaults.get("total_budget", 80000)

    # Average cost: mix of M2.7 (70%) and M3 (30%)
    cost_m27 = _cost_usd(int(total_est * 0.7), "MiniMax-M2.7", budget)
    cost_m3 = _cost_usd(int(total_est * 0.3), "MiniMax-M3", budget)
    total_cost = cost_m27 + cost_m3

    ok = budget_total >= total_est
    ratio = total_est / budget_total if budget_total else 0

    print(f"\n{'='*50}")
    print("  GCL Budget Estimate")
    print(f"{'='*50}")
    print(f"  Complexity:     {complexity}")
    print(f"  Agents:         {num_agents}")
    print(f"  Est tokens:     {total_est:,} (×{num_agents} agents × ~{est_tokens:,}/agent)")
    print(f"  Est cost:       ~${total_cost:.4f} (M2.7 70% + M3 30%)")
    print(f"  Budget:         {budget_total:,}")
    print(f"  Usage:          {ratio*100:.1f}% of budget")
    if ok:
        print(f"  Status:         🟢 OK — {budget_total - total_est:,} headroom")
    else:
        print(f"  Status:         🔴 EXCEEDS budget by {total_est - budget_total:,} tokens")
        print("  → Suggestion: reduce agents or complexity")
    print()
    return 0


def cmd_self_test() -> int:
    budget = load_budget()
    assert isinstance(budget, dict), "budget must be dict"
    assert "defaults" in budget, "budget must have defaults"
    assert "model_pricing" in budget, "budget must have model_pricing"
    assert "complexity_budget" in budget, "budget must have complexity_budget"

    # Estimate path
    from io import StringIO

    # Test estimate
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        r = cmd_estimate(budget, "medium", 4)
    finally:
        sys.stdout = old_stdout

    assert r == 0, "estimate should return 0"

    # Test _cost_usd
    c = _cost_usd(1000, "MiniMax-M2.7", budget)
    assert isinstance(c, float) and c >= 0, "cost should be non-negative float"

    # Test _mini_chart
    chart = _mini_chart([0.1, 0.5, 0.9])
    assert isinstance(chart, str) and len(chart) > 0, "chart should be non-empty string"

    print("Self-test passed: budget loading, estimate, cost calc, chart — all OK")
    return 0


def cmd_strict(budget: dict[str, Any]) -> int:
    """Exit 1 if any loop exceeded abort_threshold."""
    traces = _collect_traces()
    defaults = budget.get("defaults", {})
    abort_t = defaults.get("abort_threshold", 1.2)

    exceeded: list[dict[str, Any]] = []
    for p, data in traces:
        s = _summarize_trace(p, data, budget)
        if s["ratio"] >= abort_t:
            exceeded.append(s)

    if exceeded:
        for s in exceeded:
            print(f"ABORT: {s['task']} at {_format_timestamp(s['path'])} — {s['ratio']*100:.1f}% of budget 🔴",
                  file=sys.stderr)
        return 1

    print(f"No loops exceeded abort threshold ({abort_t*100:.0f}%).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--estimate", action="store_true", help="Dry-run token/cost estimate")
    parser.add_argument("--complexity", default="medium",
                        choices=["low", "medium", "high"],
                        help="Complexity level for --estimate")
    parser.add_argument("--agents", type=int, default=4,
                        help="Number of agents for --estimate")
    parser.add_argument("--self-test", action="store_true", help="Run internal checks")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any loop exceeded abort threshold")
    parser.add_argument("--budget-file", type=Path, default=BUDGET_FILE,
                        help="Path to gcl-budget.yaml")
    args = parser.parse_args()

    budget = load_budget()

    if args.self_test:
        return cmd_self_test()
    if args.estimate:
        return cmd_estimate(budget, args.complexity, args.agents)
    if args.strict:
        return cmd_strict(budget)
    return cmd_dashboard(budget)


if __name__ == "__main__":
    sys.exit(main())
