#!/usr/bin/env python3
"""
aggregate_gcl_traces.py — GCL Loop 可度量指标聚合器

输入: audit-results/gcl-trace-*.json
输出: markdown stats report to stdout
exit: 0 always (graceful on no-trace)

自检模式:
    python3 scripts/aggregate_gcl_traces.py --self-test
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent.parent / "audit-results"
TRACER_PATTERN = "gcl-trace-*.json"


# ─── Fake trace factory (for --self-test) ────────────────────────────────────

def _fake_traces() -> list[dict]:
    """Generate 10 synthetic GCL traces covering PASS / MAX_ITER / multi-iter paths."""
    base = {
        "skill": "qcloud-test-ops",
        "request": "test op",
        "rubric_version": "v1",
        "preflight_reflexion": {"skill": "qcloud-test-ops", "command": "echo ok",
                                "injection_id": None, "matched_failure_keys": [],
                                "matched_failures": 0, "matched_successes": 0, "injection": ""},
    }
    traces = []

    # PASS in 1 iter
    for i in range(5):
        t = {**base, "iterations": [
            _iter(1, "PASS", suggestions=[], blocking=False,
                  scores={"correctness": 1.0, "safety": 1.0,
                          "traceability": 1.0, "idempotency": 1.0, "spec_compliance": 1.0})
        ], "final": {"status": "PASS", "iter": 1, "output": "ok"}}
        traces.append(t)

    # MAX_ITER
    for i in range(2):
        t = {**base, "iterations": [
            _iter(1, "RETRY", suggestions=["fix it"], blocking=True,
                  scores={"correctness": 0.5, "safety": 1.0,
                          "traceability": 0.5, "idempotency": 0.5, "spec_compliance": 0.5}),
            _iter(2, "RETRY", suggestions=["fix again"], blocking=True,
                  scores={"correctness": 0.5, "safety": 1.0,
                          "traceability": 0.5, "idempotency": 0.5, "spec_compliance": 0.5}),
        ], "final": {"status": "MAX_ITER", "iter": 2, "output": "partial"}}
        traces.append(t)

    # PASS in 2 iters (drift→fix)
    for i in range(2):
        t = {**base, "iterations": [
            _iter(1, "RETRY", suggestions=["yaml_drift: missing field X"], blocking=True,
                  scores={"correctness": 0.5, "safety": 1.0,
                          "traceability": 1.0, "idempotency": 1.0, "spec_compliance": 0.5}),
            _iter(2, "PASS", suggestions=[], blocking=False,
                  scores={"correctness": 1.0, "safety": 1.0,
                          "traceability": 1.0, "idempotency": 1.0, "spec_compliance": 1.0}),
        ], "final": {"status": "PASS", "iter": 2, "output": "ok"}}
        traces.append(t)

    # RETRY→PASS with blocker type variety
    traces.append({**base, "iterations": [
        _iter(1, "RETRY", suggestions=["spec file refs/xxx not found",
                                         "major: unclear error message"], blocking=True,
              scores={"correctness": 0.5, "safety": 1.0,
                      "traceability": 1.0, "idempotency": 1.0, "spec_compliance": 0.5}),
        _iter(2, "PASS", suggestions=[], blocking=False,
              scores={"correctness": 1.0, "safety": 1.0,
                      "traceability": 1.0, "idempotency": 1.0, "spec_compliance": 1.0}),
    ], "final": {"status": "PASS", "iter": 2, "output": "ok"}})

    return traces


def _iter(n: int, decision: str, suggestions: list, blocking: bool,
          scores: dict) -> dict:
    return {
        "iter": n,
        "generator": {"command": f"echo {n}", "exit_code": 0, "result_excerpt": "ok",
                      "stdout_len": 2, "stderr_len": 0, "op_type": "read"},
        "critic": {
            "scores": scores,
            "suggestions": suggestions,
            "blocking": blocking,
            "rubric_rule_hits": defaultdict(list),
        },
        "decision": decision,
    }


# ─── Trace loading ───────────────────────────────────────────────────────────

def load_traces(audit_dir: Path = AUDIT_DIR, use_fake: bool = False) -> list[dict]:
    if use_fake:
        return _fake_traces()
    pattern = audit_dir / TRACER_PATTERN
    files = sorted(glob.glob(str(pattern)))
    traces = []
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                trace = json.load(f)
                trace["__filename"] = fp
                traces.append(trace)
        except (json.JSONDecodeError, OSError):
            pass
    return traces


# ─── Timestamp extraction ─────────────────────────────────────────────────────

def trace_timestamp(trace: dict, filename: str = "") -> datetime | None:
    """Parse YYYYMMDD-HHMMSS from trace filename or trace['ts'] field."""
    ts = trace.get("ts") or trace.get("started_at")
    if ts:
        for fmt in ("%Y%m%d-%H%M%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(str(ts), fmt)
            except ValueError:
                continue
    # derive from filename
    import re
    m = re.search(r"(\d{8}-\d{6})", filename)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d-%H%M%S")
        except ValueError:
            pass
    return None


# ─── Blockers / Majors extraction ───────────────────────────────────────────

_BLOCKER_KEYWORDS = ("blocker", "critical", "safety", "abort", "fail")
_MAJOR_KEYWORDS = ("major", "error", "drift", "missing", "invalid")


def _tag_suggestions(suggestions: list[str]) -> tuple[list[str], list[str]]:
    blockers, majors = [], []
    for s in suggestions:
        low = s.lower()
        if any(k in low for k in _BLOCKER_KEYWORDS):
            blockers.append(s)
        elif any(k in low for k in _MAJOR_KEYWORDS):
            majors.append(s)
    return blockers, majors


def _extract_issue_types(suggestions: list[str]) -> list[str]:
    """Normalize suggestions to short type tags for distribution counting."""
    types = []
    for s in suggestions:
        low = s.lower()
        if "yaml" in low or "drift" in low or "schema" in low:
            types.append("yaml_python_drift")
        elif "auth" in low or "credential" in low or "secret" in low:
            types.append("auth_credential")
        elif "param" in low or "argument" in low or "flag" in low:
            types.append("invalid_params")
        elif "rubric" in low or "compliance" in low or "spec_compliance" in low:
            types.append("spec_compliance")
        # NOTE: trace/idempot must come BEFORE the broad spec/file/ref/missing
        # bucket — "missing RequestId" and "missing ClientToken" contain "missing"
        # but are traceability/idempotency issues, not spec file reference issues.
        elif "trace" in low or "audit" in low or "log" in low:
            types.append("traceability")
        elif "idempot" in low:
            types.append("idempotency")
        # Only use the broad bucket for genuinely spec/file/ref/path-not-found patterns
        elif any(_ in low for _ in ["spec", "file", "ref"]) and "missing" not in low:
            types.append("spec_file_refs_missing")
        elif "error" in low or "code" in low:
            types.append("error_handling")
        else:
            types.append("other")
    return types


# ─── Metrics ─────────────────────────────────────────────────────────────────

def aggregate(traces: list[dict], use_fake: bool = False,
               evidence_jsonl: str = "") -> dict:
    if not traces:
        return {}

    n = len(traces)
    skill_counter = Counter(t.get("skill", "unknown") for t in traces)

    # decisions & final outcomes
    decisions_all: list[str] = []   # every iter decision per trace
    final_statuses: list[str] = []
    retry_count = 0
    pass_count = 0
    abort_count = 0
    max_iter_count = 0
    blocker_types: Counter = Counter()
    major_types: Counter = Counter()
    issues_by_trace: list[int] = []   # blockers+majors per trace

    for trace in traces:
        final = trace.get("final", {})
        status = final.get("status", "UNKNOWN")
        final_statuses.append(status)
        if status == "PASS":
            pass_count += 1
        elif status == "MAX_ITER":
            max_iter_count += 1
        elif status == "ABORT":
            abort_count += 1

        blockers_this_trace: list[str] = []
        majors_this_trace: list[str] = []

        for it in trace.get("iterations", []):
            decision = it.get("decision", "")
            decisions_all.append(decision)
            if decision == "RETRY":
                retry_count += 1

            suggestions = it.get("critic", {}).get("suggestions", [])
            b, m = _tag_suggestions(suggestions)
            blockers_this_trace.extend(b)
            majors_this_trace.extend(m)
            for t in _extract_issue_types(suggestions):
                if t not in ("other",) and (b or m):
                    # only count if actually tagged blocker/major
                    if t in ("traceability", "idempotency", "spec_compliance", "error_handling"):
                        major_types[t] += 1
                    else:
                        blocker_types[t] += 1

        issues_by_trace.append(len(blockers_this_trace) + len(majors_this_trace))

    # timestamps for MTTR and trend
    ts_map: dict[str, datetime] = {}
    for trace in traces:
        ts = trace_timestamp(trace)
        fn = trace.get("__filename", "")
        ts2 = trace_timestamp(trace, fn)
        key = ts or ts2
        if key:
            status = trace.get("final", {}).get("status", "")
            ts_map[key] = status

    # MTTR: for each PASS that took >1 iter, compute time diff
    # (No real timestamps in traces → report N/A with explanation)
    mttr_n = sum(1 for t in traces
                 if t.get("final", {}).get("status") == "PASS"
                 and len(t.get("iterations", [])) > 1)
    mttr_avg = "N/A (trace files lack started_at/finished_at — use real GCL runner timestamps)"

    # commits / files: not tracked in current schema → N/A
    commits_avg = "N/A (schema does not track commits)"
    files_avg = "N/A (schema does not track files_changed)"

    # trend: sorted by time, last N
    sorted_ts = sorted(ts_map.items())
    trend_seq = [s for _, s in sorted_ts]

    # retry rate (traces with at least one RETRY)
    traces_with_retry = sum(1 for d in decisions_all if d == "RETRY")
    retry_rate = f"{traces_with_retry}/{len(decisions_all)} iters had RETRY"

    return {
        "total_traces": n,
        "skill_distribution": dict(skill_counter.most_common(5)),
        "final_pass_count": pass_count,
        "final_max_iter_count": max_iter_count,
        "final_abort_count": abort_count,
        "final_pass_rate": f"{pass_count/n*100:.1f}%",
        "final_max_iter_rate": f"{max_iter_count/n*100:.1f}%",
        "final_abort_rate": f"{abort_count/n*100:.1f}%",
        "retry_count": retry_count,
        "total_iters": len(decisions_all),
        "retry_rate": retry_rate,
        "blocker_types_top5": dict(blocker_types.most_common(5)),
        "major_types_top5": dict(major_types.most_common(5)),
        "issues_per_trace_avg": f"{sum(issues_by_trace)/n:.2f}" if n else "0",
        "mttr_drifts_fixed": mttr_n,
        "mttr_note": mttr_avg,
        "commits_avg": commits_avg,
        "files_avg": files_avg,
        "trend_last20": trend_seq[-20:],
        "trend_note": "Each entry = final status per trace, oldest→newest",
        "suggestion_top3": _collect_suggestion_top3(evidence_jsonl) if evidence_jsonl else {},
        "fix_coverage": _compute_fix_coverage(evidence_jsonl) if evidence_jsonl else {},
    }


# ─── Markdown report ─────────────────────────────────────────────────────────

def render(metrics: dict) -> str:
    if not metrics:
        return "No traces found. Run a GCL Loop first."

    lines = [
        "# GCL Loop Aggregate Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        "**Source**: `audit-results/gcl-trace-*.json`  ",
        "",
        "---",
        "",
        "## 累计统计",
        "",
        "| 指标 | 值 |",
        "|------|----|",
        f"| 累计 GCL Loop 数 | {metrics['total_traces']} |",
        f"| 总 iteration 轮次 | {metrics['total_iters']} |",
        f"| 最终 PASS | {metrics['final_pass_count']} ({metrics['final_pass_rate']}) |",
        f"| 最终 MAX_ITER | {metrics['final_max_iter_count']} ({metrics['final_max_iter_rate']}) |",
        f"| 最终 ABORT | {metrics['final_abort_count']} ({metrics['final_abort_rate']}) |",
        f"| RETRY 触发率 | {metrics['retry_rate']} |",
        "",
        "## Skill 分布 (Top 5)",
        "",
        "| Skill | Count |",
        "|-------|-------|",
    ]
    for skill, cnt in metrics["skill_distribution"].items():
        lines.append(f"| {skill} | {cnt} |")

    lines += [
        "",
        "## BLOCKER 类型分布 (Top 5)",
        "",
    ]
    bt = metrics["blocker_types_top5"]
    if bt:
        lines += ["| 类型 | 次数 |", "|------|------|"]
        for t, c in bt.items():
            lines.append(f"| {t} | {c} |")
    else:
        lines.append("*无 BLOCKER 记录*")

    lines += [
        "",
        "## MAJOR 类型分布 (Top 5)",
        "",
    ]
    mt = metrics["major_types_top5"]
    if mt:
        lines += ["| 类型 | 次数 |", "|------|------|"]
        for t, c in mt.items():
            lines.append(f"| {t} | {c} |")
    else:
        lines.append("*无 MAJOR 记录*")

    lines += [
        "",
        "## 产出指标",
        "",
        "| 指标 | 值 |",
        "|------|----|",
        f"| 平均每 trace 问题数 | {metrics['issues_per_trace_avg']} |",
        f"| drift→fix 次数 (MTTR样本) | {metrics['mttr_drifts_fixed']} |",
        f"| MTTR | {metrics['mttr_note']} |",
        f"| 平均 commits/trace | {metrics['commits_avg']} |",
        f"| 平均落盘文件/trace | {metrics['files_avg']} |",
        "",
        "## PASS 趋势 (最近 20 次, 旧→新)",
        "",
        "```",
        "  ".join(metrics["trend_last20"]) if metrics["trend_last20"] else "N/A",
        "```",
        "",
        f"> **Note**: {metrics['trend_note']}",
    ]

    # ── suggestion Top-3 per type ──────────────────────────────────────────
    s3 = metrics.get("suggestion_top3")
    if s3:
        lines += [
            "",
            "## BLOCKER / MAJOR 精确 Suggestion Top-3",
            "",
        ]
        for category, items in sorted(s3.items(), key=lambda x: -sum(c for _, c in x[1])):
            if not items:
                continue
            lines.append(f"### {category}")
            lines.append("")
            lines.append("| Suggestion | 次数 |")
            lines.append("|------------|------|")
            for msg, cnt in items[:3]:
                escaped = msg.replace("|", "&#124;")
                lines.append(f"| {escaped} | {cnt} |")
            lines.append("")

    # ── fix coverage ───────────────────────────────────────────────────────
    fc = metrics.get("fix_coverage")
    if fc:
        lines += [
            "",
            "## Auto-fix 覆盖率",
            "",
            "| 类别 | 已有值 | 缺失(可补) | 覆盖率 |",
            "|------|--------|------------|--------|",
        ]
        for cat, vals in sorted(fc.items()):
            present = vals["present"]
            missing = vals["missing"]
            total = present + missing
            rate = f"{present/total*100:.1f}%" if total else "N/A"
            lines.append(f"| {cat} | {present} | {missing} | {rate} |")
        lines.append("")

    # ── next-run optimization suggestions ─────────────────────────────────
    lines += [
        "## 下次 GCL 优化建议",
        "",
        ("- **traceability**: Generator 输出应包含 `RequestId`（从 tccli JSON 响应中提取） "
         f"共 {sum(c for _, c in s3.get('traceability', [])) if s3 else 'N/A'} 次缺失 → 更新 skill generator 模板. "
         "临时修复: `scripts/auto_fix_gcl_blockers.py --dry-run` 补默认值"),
        ("- **idempotency**: Generator 应为每个请求生成并跟踪 `ClientToken`（UUID） "
         f"共 {sum(c for _, c in s3.get('idempotency', [])) if s3 else 'N/A'} 次缺失 → skill generator 模板需在每次 tccli 调用前生成 ClientToken"),
        ("- **auth_credential**: `exit_code=-2` 表示命令被 skill harness 拒绝 "
         f"共 {sum(c for _, c in s3.get('auth_credential', [])) if s3 else 'N/A'} 次 → 检查 skill 权限或命令语法. 此类型无法自动修复，需人工排查"),
    ]

    return "\n".join(lines)


# ─── Suggestion Top-3 collector ───────────────────────────────────────────

def _collect_suggestion_top3(evidence_jsonl: str) -> dict[str, list[tuple[str, int]]]:
    """Read evidence JSONL, return {type: [(msg, count), ...]} for BLOCKER/MAJOR types."""
    type_suggestions: dict[str, list[str]] = defaultdict(list)
    try:
        with open(evidence_jsonl, encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                iters = d.get("trace", {}).get("iterations", [])
                for it in iters:
                    c = it.get("critic", {})
                    for s in c.get("suggestions", []):
                        low = s.lower()
                        if "requestid" in low or ("trace" in low and "missing" in low):
                            type_suggestions["traceability"].append(s)
                        elif "clienttoken" in low or ("idempot" in low and "missing" in low) or s == "set ClientToken":
                            type_suggestions["idempotency"].append(s)
                        elif "exit_code" in low or "credentials" in low:
                            type_suggestions["auth_credential"].append(s)
    except (OSError, json.JSONDecodeError):
        pass
    result = {}
    for t, msgs in type_suggestions.items():
        result[t] = Counter(msgs).most_common(3)
    return result


# ─── Fix coverage ─────────────────────────────────────────────────────────────

_TRACER_FIELDS = ("started_at", "finished_at", "commits", "files_changed")


def _compute_fix_coverage(evidence_jsonl: str) -> dict[str, dict[str, int]]:
    """Count present/missing TRACER_FIELDS across all traces."""
    counts: dict[str, dict[str, int]] = {f: {"present": 0, "missing": 0} for f in _TRACER_FIELDS}
    try:
        with open(evidence_jsonl, encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                for field in _TRACER_FIELDS:
                    if field in d:
                        counts[field]["present"] += 1
                    else:
                        counts[field]["missing"] += 1
    except (OSError, json.JSONDecodeError):
        pass
    return counts


# ─── Self-test ────────────────────────────────────────────────────────────────

def self_test() -> bool:
    traces = _fake_traces()
    m = aggregate(traces, use_fake=True)
    # verify counts
    ok = True
    checks = [
        ("total_traces == 10", m["total_traces"] == 10),
        ("final_pass_count == 8", m["final_pass_count"] == 8),   # 5 one-shot + 2 two-iter PASS + 1 blocker-fix PASS
        ("final_max_iter_count == 2", m["final_max_iter_count"] == 2),
        ("final_abort_count == 0", m["final_abort_count"] == 0),  # no ABORT in fake traces
        ("retry_count >= 5", m["retry_count"] >= 5),
        ("blocker_types has yaml_python_drift", "yaml_python_drift" in m["blocker_types_top5"]),
        ("spec_file_refs_missing in blocker_types", "spec_file_refs_missing" in m["blocker_types_top5"]),
        ("mttr_drifts_fixed == 3", m["mttr_drifts_fixed"] == 3),  # 3 PASS in >1 iter (2 drift + 1 blocker)
    ]
    for label, result in checks:
        status = "PASS" if result else "FAIL"
        if not result:
            ok = False
        print(f"  [{status}] {label}")
    return ok


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate GCL Loop traces")
    parser.add_argument("--self-test", action="store_true", help="Run self-test with fake traces")
    parser.add_argument("--dir", type=Path, default=AUDIT_DIR,
                        help=f"audit-results directory (default: {AUDIT_DIR})")
    args = parser.parse_args()

    if args.self_test:
        print("Running self-test...")
        ok = self_test()
        print("Self-test " + ("PASSED" if ok else "FAILED"))
        sys.exit(0)

    evidence_jsonl = str(args.dir / "evidence-local.jsonl")
    traces = load_traces(args.dir)
    metrics = aggregate(traces, evidence_jsonl=evidence_jsonl)
    print(render(metrics))
    sys.exit(0)


if __name__ == "__main__":
    main()
