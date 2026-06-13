# CVM AIOps Diagnosis — Delegation Stub

> **Do not run multi-metric correlation or alarm storm logic from this file.** Delegate to the cross-cutting skill [`qcloud-aiops-diagnosis`](../../qcloud-aiops-diagnosis/SKILL.md).

## When to Delegate

| User intent | Delegate to | Pass variables |
|-------------|-------------|----------------|
| CPU/memory spike root cause across metrics | `qcloud-aiops-diagnosis` | `resource_id`, `resource_type=cvm`, `time_range` |
| OOM / performance correlation with logs | `qcloud-aiops-diagnosis` | + `log_source`, CLS topic if known |
| Alarm storm with CVM + CLB/TKE context | `qcloud-aiops-diagnosis` | + `cluster_id`, `load_balancer_id` |
| Baseline anomaly (vs yesterday/week) | `qcloud-aiops-diagnosis` | `anomaly_mode=baseline_primary` |
| Bill + CVM metric joint RCA | `qcloud-aiops-diagnosis` | `finops_handoff`, `handoff_source=finops` |

## When to Stay in CVM Skill

- Instance CRUD, start/stop/reboot, disk attach, snapshot
- Single documented CVM error with known fix → [`troubleshooting.md`](troubleshooting.md)
- CAM/VPC-only issues → respective product skills

## Return Contract

AIOps returns Event Bundle, RCA Bundle, or Anomaly Bundle per [`output-schemas.md`](../../qcloud-aiops-diagnosis/references/output-schemas.md). Execute fixes via this skill using `RECOMMENDATION (not execution)` items and `delegate_to` fields.

## CVM-Specific Correlation Hints (Reference Only)

When AIOps delegates back for CVM mutation, common patterns:

| Pattern | Primary Metric | Correlated | Typical fix |
|---------|---------------|------------|-------------|
| Traffic spike | CpuUsage ↑ | NetworkIn ↑ | Scale out |
| CPU bound | CpuUsage ↑ | NetworkIn stable | Optimize / resize |
| Memory leak | MemUsage ↑↑ | OOM in logs | Restart + fix leak |
| I/O bottleneck | DiskLatency ↑ | DiskIO ↑ | Upgrade disk type |

Full decision trees: [`qcloud-aiops-diagnosis/references/diagnostic-workflows.md`](../../qcloud-aiops-diagnosis/references/diagnostic-workflows.md).

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-06-13 | Replaced 660-line duplicate with delegation stub (TE-6, single responsibility) |
