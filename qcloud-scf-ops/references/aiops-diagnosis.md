# SCF AIOps Diagnosis — Delegation Stub

> **Do not run multi-metric correlation or cross-layer RCA from this file.** Delegate to [`qcloud-aiops-diagnosis`](../../qcloud-aiops-diagnosis/SKILL.md) (read-only); execute fixes via this skill per bundle recommendations.

## When to Delegate

| User intent | Delegate to | Pass variables |
|-------------|-------------|----------------|
| Error / timeout / throttle spike root cause | `qcloud-aiops-diagnosis` | `function_name`, `scf_namespace`, `resource_type=scf`, `time_range` |
| Cold start / InitDuration / first-invocation latency | `qcloud-aiops-diagnosis` | + `anomaly_mode=baseline_primary` if no clear window |
| Concurrency / account throttle (429) | `qcloud-aiops-diagnosis` | + Monitor `QCE/SCF` Throttle metric context |
| Downstream DB/VPC timeout in function logs | `qcloud-aiops-diagnosis` | + downstream `resource_id` if known (Rule O → H/I/G) |
| Alarm storm with SCF + API GW / trigger context | `qcloud-aiops-diagnosis` | + trigger type, optional `load_balancer_id` |

## When to Stay in SCF Skill

- Function CRUD, code deploy, version/alias, trigger CRUD
- Timeout/memory/concurrency **config change** after RCA identifies fix
- Single documented SCF error with known fix → [`troubleshooting.md`](troubleshooting.md)
- CAM/VPC-only issues → respective product skills

## Return Contract

AIOps returns Event Bundle, RCA Bundle, or Anomaly Bundle per [`output-schemas.md`](../../qcloud-aiops-diagnosis/references/output-schemas.md). Product RCA uses **Rule O** in [`product-rca-rules.md`](../../qcloud-aiops-diagnosis/references/product-rca-rules.md).

## SCF-Specific Correlation Hints (Reference Only)

| Pattern | Primary Metric | Correlated | Typical fix (this skill) |
|---------|---------------|------------|--------------------------|
| Code exception | Error ↑ | Stack in GetFunctionLogs | Fix code / redeploy |
| Timeout budget | Duration at ceiling | Downstream errors in logs | Raise timeout or fix deps |
| Cold start | Duration spike (first inv) | InitDuration in logs | Reduce package / provisioned concurrency |
| Throttle | Throttle ↑ | 429 in logs | Raise concurrency / reserved config |
| Downstream DB | Error ↑ | CDB/Redis metrics (Rule H/I) | Fix downstream; not SCF-only |

Full workflow: [`qcloud-aiops-diagnosis/references/diagnostic-workflows.md`](../../qcloud-aiops-diagnosis/references/diagnostic-workflows.md) Workflow 9 → Rule O.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-13 | Initial stub — Rule O reverse delegation (Phase F) |
