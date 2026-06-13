# CBS AIOps Diagnosis — Delegation Stub

> **Do not run cross-product RCA from this file.** Delegate to [`qcloud-aiops-diagnosis`](../../qcloud-aiops-diagnosis/SKILL.md).

## When to Delegate

| User intent | Pass variables |
|-------------|----------------|
| Disk I/O latency spike with app impact | `resource_id` (CVM attached to disk), `resource_type=cvm`, `time_range` |
| CBS performance correlated with CVM/CLB symptoms | + `instance_id`, `load_balancer_id` if known |
| Baseline anomaly on disk metrics | `anomaly_mode=baseline_primary` |

## When to Stay in CBS Skill

- Disk create/attach/detach/resize/snapshot/terminate
- CBS-specific quota and billing item ops

## Return Contract

See [`output-schemas.md`](../../qcloud-aiops-diagnosis/references/output-schemas.md). Apply disk fixes via this skill per AIOps recommendations.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-13 | Initial stub (fixes broken link from SKILL.md) |
