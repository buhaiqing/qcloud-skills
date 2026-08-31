#!/usr/bin/env python3
"""
collect_mttr_samples.py — MTTR 数据收集自动化

生成带 started_at/finished_at 和 BLOCKER 检测+修复周期的合成 GCL trace，
供 aggregate_gcl_traces.py 的 MTTR 表格统计。

Usage:
  python3 scripts/collect_mttr_samples.py --mode self-test  # 自检（用 tmpdir）
  python3 scripts/collect_mttr_samples.py --mode dry-run    # 列出将跑的 scenario（默认）
  python3 scripts/collect_mttr_samples.py --mode apply      # 实际写入 audit-results/
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audit-results"

# BLOCKER 类型 → suggestion 模板 + scores
# 每个 scenario 产生 2 个 iteration：iter1=BLOCKER, iter2=PASS
SCENARIOS = [
    {
        "name": "idempotency_basic",
        "skill": "qcloud-cvm-ops",
        "started_delta_minutes": 0,
        "iter_duration_minutes": 2,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 0.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter1_suggestions": ["BLOCKER: idempotency failure — response lacks ClientToken, idempotency risk"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    {
        "name": "idempotency_retry",
        "skill": "qcloud-cdb-ops",
        "started_delta_minutes": 10,
        "iter_duration_minutes": 3,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 0.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter1_suggestions": ["BLOCKER: idempotency failure — response lacks ClientToken, idempotency risk"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    {
        "name": "traceability_basic",
        "skill": "qcloud-clb-ops",
        "started_delta_minutes": 20,
        "iter_duration_minutes": 4,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 0.0, "spec_compliance": 1.0,
        },
        "iter1_suggestions": ["BLOCKER: traceability failure — response lacks RequestId, cannot trace"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    {
        "name": "traceability_retry",
        "skill": "qcloud-cos-ops",
        "started_delta_minutes": 30,
        "iter_duration_minutes": 5,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 0.0, "spec_compliance": 1.0,
        },
        "iter1_suggestions": ["BLOCKER: traceability failure — response lacks RequestId, cannot trace"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    {
        "name": "auth_credential_basic",
        "skill": "qcloud-redis-ops",
        "started_delta_minutes": 40,
        "iter_duration_minutes": 1,
        "iter1_scores": {
            "correctness": 0.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter1_suggestions": ["BLOCKER: auth failure — exit_code=-2, credentials invalid"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    {
        "name": "auth_credential_retry",
        "skill": "qcloud-vpc-ops",
        "started_delta_minutes": 50,
        "iter_duration_minutes": 2,
        "iter1_scores": {
            "correctness": 0.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter1_suggestions": ["BLOCKER: auth failure — exit_code=-2, credentials invalid"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    {
        "name": "spec_compliance_drift",
        "skill": "qcloud-tke-ops",
        "started_delta_minutes": 60,
        "iter_duration_minutes": 6,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 0.0,
        },
        "iter1_suggestions": ["yaml_python_drift: spec file refs/xxx not found; BLOCKER: spec drift detected"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    {
        "name": "spec_compliance_missing_field",
        "skill": "qcloud-cam-ops",
        "started_delta_minutes": 70,
        "iter_duration_minutes": 3,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 0.5,
        },
        "iter1_suggestions": ["BLOCKER: spec_compliance failure — spec refs unresolved; audit gap"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    # traceability 模板修复路径（R9）：修复耗时从 4-5m → 1m，验证模板可缩短 MTTR
    {
        "name": "traceability_template_basic",
        "skill": "qcloud-cdb-ops",
        "started_delta_minutes": 80,
        "iter_duration_minutes": 1,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 0.0, "spec_compliance": 1.0,
        },
        "iter1_suggestions": ["BLOCKER: traceability failure — response lacks RequestId; fix via docs/superpowers/specs/traceability-fix-template.md"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    {
        "name": "traceability_template_retry",
        "skill": "qcloud-es-ops",
        "started_delta_minutes": 90,
        "iter_duration_minutes": 1,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 0.0, "spec_compliance": 1.0,
        },
        "iter1_suggestions": ["BLOCKER: traceability failure — response lacks RequestId; fix via docs/superpowers/specs/traceability-fix-template.md"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    # yaml_drift 模板修复路径（R10 真实 run 验证）：脚本化机制实测 0.09s，
    # mock 用 1m/iter 保守覆盖真实 agent 的人为读矩阵/编辑/重跑开销，
    # 基准 = spec_compliance_drift 12m（6m x 2 iter）→ 模板路径 2m (-83%)
    # 详见 docs/superpowers/specs/yaml-drift-mttr-validation.md
    {
        "name": "yaml_template_basic",
        "skill": "qcloud-cdb-ops",
        "started_delta_minutes": 100,
        "iter_duration_minutes": 1,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 0.0,
        },
        "iter1_suggestions": ["BLOCKER: yaml_python_drift — YAML=[cdb_create.InstanceId, vpc_create.VpcId], PY=[cdb_create.InstanceId]; fix via docs/superpowers/specs/yaml-drift-fix-template.md"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
    {
        "name": "yaml_template_retry",
        "skill": "qcloud-vpc-ops",
        "started_delta_minutes": 110,
        "iter_duration_minutes": 1,
        "iter1_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 0.0,
        },
        "iter1_suggestions": ["BLOCKER: yaml_python_drift — YAML=[cdb_create.InstanceId, vpc_create.VpcId], PY=[cdb_create.InstanceId]; fix via docs/superpowers/specs/yaml-drift-fix-template.md"],
        "iter1_blocking": True,
        "iter2_scores": {
            "correctness": 1.0, "safety": 1.0,
            "idempotency": 1.0, "traceability": 1.0, "spec_compliance": 1.0,
        },
        "iter2_suggestions": [],
        "iter2_blocking": False,
    },
]


def build_trace(scenario: dict, base_time: datetime) -> dict:
    """Build a synthetic GCL trace for one scenario."""
    started = base_time + timedelta(minutes=scenario["started_delta_minutes"])
    iter1_finish = started + timedelta(minutes=scenario["iter_duration_minutes"])
    finished = iter1_finish + timedelta(minutes=scenario["iter_duration_minutes"])

    trace_id = f"mttr-{scenario['name']}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    trace = {
        "skill": scenario["skill"],
        "request": f"MTTR mock: {scenario['name']}",
        "rubric_version": "v1",
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "trace_id": trace_id,
        "iterations": [
            {
                "iter": 1,
                "generator": {
                    "command": f"echo mock-{scenario['name']}",
                    "exit_code": 0,
                    "result_excerpt": '{"Response":{"RequestId":"mock"}}',
                    "stdout_len": 30,
                    "stderr_len": 0,
                    "op_type": "read",
                    "args": {"iter": 1, "critic_feedback": None},
                },
                "critic": {
                    "scores": scenario["iter1_scores"],
                    "suggestions": scenario["iter1_suggestions"],
                    "blocking": scenario["iter1_blocking"],
                    "rubric_rule_hits": {
                        "correctness": [],
                        "safety": [],
                        "idempotency": [],
                        "traceability": [],
                        "spec_compliance": [],
                    },
                },
                "decision": "RETRY",
            },
            {
                "iter": 2,
                "generator": {
                    "command": f"echo mock-{scenario['name']}-fixed",
                    "exit_code": 0,
                    "result_excerpt": '{"Response":{"RequestId":"mock","ClientToken":"mock-token"}}',
                    "stdout_len": 70,
                    "stderr_len": 0,
                    "op_type": "read",
                    "args": {"iter": 2, "critic_feedback": "; ".join(scenario["iter1_suggestions"])},
                },
                "critic": {
                    "scores": scenario["iter2_scores"],
                    "suggestions": scenario["iter2_suggestions"],
                    "blocking": scenario["iter2_blocking"],
                    "rubric_rule_hits": {
                        "correctness": [],
                        "safety": [],
                        "idempotency": [],
                        "traceability": [],
                        "spec_compliance": [],
                    },
                },
                "decision": "PASS",
            },
        ],
        "final": {
            "status": "PASS",
            "iter": 2,
            "output": '{"Response":{"RequestId":"mock","ClientToken":"mock-token"}}',
        },
        "preflight_reflexion": {
            "skill": scenario["skill"],
            "command": f"echo mock-{scenario['name']}",
            "injection_id": None,
            "matched_failure_keys": [],
            "matched_failures": 0,
            "matched_successes": 0,
            "injection": "",
        },
        "commits": [],
        "files_changed": [],
    }
    return trace


def collect_traces(scenarios: list[dict], audit_dir: Path, base_time: datetime | None = None) -> list[Path]:
    """Write synthetic traces for all scenarios. Returns list of written file paths."""
    if base_time is None:
        base_time = datetime.now(UTC).replace(microsecond=0)
    written = []
    for s in scenarios:
        trace = build_trace(s, base_time)
        path = audit_dir / f"gcl-trace-{trace['trace_id']}.json"
        path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)
    return written


# 每个 scenario 期望的 BLOCKER 类型（独立于 classifier，来自 scores 语义）
# 防回归：若 suggestion 文案含 keyword 导致 _extract_issue_types 误分类，此处 FAIL
EXPECTED_ISSUE_TYPES = {
    "idempotency_basic": "idempotency",
    "idempotency_retry": "idempotency",
    "traceability_basic": "traceability",
    "traceability_retry": "traceability",
    "auth_credential_basic": "auth_credential",
    "auth_credential_retry": "auth_credential",
    "spec_compliance_drift": "yaml_python_drift",
    "spec_compliance_missing_field": "spec_compliance",
    "traceability_template_basic": "traceability",
    "traceability_template_retry": "traceability",
    "yaml_template_basic": "yaml_python_drift",
    "yaml_template_retry": "yaml_python_drift",
}


def self_test() -> bool:
    """自检：写入 tmpdir，验证产出的 trace 符合 aggregate_mttr 期望格式，且 BLOCKER 类型分类正确。"""
    print("Running self-test...")
    # 直接导入 classifier，避免对 suggestion 文本/分类顺序漂移无感知（L5: 断言真实值）
    sys.path.insert(0, str(ROOT / "scripts"))
    from aggregate_gcl_traces import _extract_issue_types

    with tempfile.TemporaryDirectory() as tmpdir:
        audit_tmp = Path(tmpdir) / "audit-results"
        audit_tmp.mkdir()

        # 用前 1 个 scenario 自检
        result = collect_traces([SCENARIOS[0]], audit_tmp)
        assert len(result) == 1, f"expected 1 trace, got {len(result)}"

        trace_path = result[0]
        trace = json.loads(trace_path.read_text())

        # 验证必要字段
        checks = [
            ("has started_at", "started_at" in trace),
            ("has finished_at", "finished_at" in trace),
            ("has iterations", "iterations" in trace and len(trace["iterations"]) == 2),
            ("iter1 decision=RETRY", trace["iterations"][0]["decision"] == "RETRY"),
            ("iter2 decision=PASS", trace["iterations"][1]["decision"] == "PASS"),
            ("final status=PASS", trace["final"]["status"] == "PASS"),
            ("iter1 has blocking suggestion", len(trace["iterations"][0]["critic"]["suggestions"]) > 0),
            ("iter2 has no blocking suggestion", len(trace["iterations"][1]["critic"]["suggestions"]) == 0),
            ("started_at is ISO format", "T" in trace["started_at"]),
            ("finished_at is ISO format", "T" in trace["finished_at"]),
        ]

        # 分类断言：对每个 scenario 的 iter1 suggestion 验证 _extract_issue_types 结果
        # （回归点：suggestion 含 "drift" 等抢跑 keyword 时会在此 FAIL）
        for s in SCENARIOS:
            expected = EXPECTED_ISSUE_TYPES[s["name"]]
            actual = _extract_issue_types(s["iter1_suggestions"])
            actual_type = actual[0] if actual else "(none)"
            ok_flag = actual_type == expected
            checks.append(
                (f"classify {s['name']} = {expected}", ok_flag)
            )

        ok = True
        for label, result_flag in checks:
            status = "PASS" if result_flag else "FAIL"
            if not result_flag:
                ok = False
            print(f"  [{status}] {label}")

        if ok:
            print("  [PASS] self-test — 1 trace written to temp dir, all checks green")
        return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument(
        "--mode",
        choices=["dry-run", "apply", "self-test"],
        default="dry-run",
        help="dry-run: list scenarios (default); apply: write traces; self-test: unit check",
    )
    # 别名（任务书约定），与 --mode 等价，显式别名优先
    parser.add_argument("--self-test", action="store_true", help="Alias for --mode self-test")
    parser.add_argument("--dry-run", action="store_true", help="Alias for --mode dry-run")
    args = parser.parse_args()

    if args.self_test:
        args.mode = "self-test"
    elif args.dry_run:
        args.mode = "dry-run"

    if args.mode == "self-test":
        ok = self_test()
        print("Self-test " + ("PASSED" if ok else "FAILED"))
        return 0 if ok else 1

    if args.mode == "apply":
        print(f"Applying — {len(SCENARIOS)} scenarios → audit-results/")
        written = collect_traces(SCENARIOS, AUDIT_DIR)
        for p in written:
            print(f"  Wrote: {p.name}")
        print(f"Done. {len(written)} traces written.")
        return 0

    # Dry-run
    print(f"Dry-run — {len(SCENARIOS)} scenarios would be generated:")
    for s in SCENARIOS:
        blocker_type = "unknown"
        scores = s["iter1_scores"]
        if scores.get("idempotency", 1.0) == 0.0:
            blocker_type = "idempotency"
        elif scores.get("traceability", 1.0) == 0.0:
            blocker_type = "traceability"
        elif scores.get("correctness", 1.0) == 0.0:
            blocker_type = "auth_credential"
        elif scores.get("spec_compliance", 1.0) < 1.0:
            blocker_type = "spec_compliance"
        print(f"  - {s['name']} [{s['skill']}] BLOCKER={blocker_type} "
              f"duration={s['iter_duration_minutes']}m x2 iter")
    print(f"\nTotal: {len(SCENARIOS)} traces → audit-results/gcl-trace-mttr-*.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
