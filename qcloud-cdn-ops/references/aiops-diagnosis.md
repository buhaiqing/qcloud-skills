# CDN AIOps Diagnosis — Delegation Stub

> **Do not run multi-metric correlation or origin-layer RCA from this file.** Delegate to [`qcloud-aiops-diagnosis`](../../qcloud-aiops-diagnosis/SKILL.md) (read-only); execute CDN/origin fixes via this skill or origin product skills per bundle recommendations.

## When to Delegate

| User intent | Delegate to | Pass variables |
|-------------|-------------|----------------|
| Origin 5xx / StatusCode5XX spike RCA | `qcloud-aiops-diagnosis` | `domain`, `resource_type=cdn`, `time_range` |
| Cache hit rate drop + bandwidth surge | `qcloud-aiops-diagnosis` | + optional purge/change window for Rule F2 |
| Edge latency (CdnResponseTime) root cause | `qcloud-aiops-diagnosis` | + origin type if known (COS/CVM/CLB) |
| Cross-layer origin failure (COS/CVM/CLB) | `qcloud-aiops-diagnosis` | Rule P → K/A/G cross-links |
| Baseline anomaly vs week | `qcloud-aiops-diagnosis` | `anomaly_mode=baseline_primary` |

## When to Stay in CDN Skill

- Domain add/delete, cache purge/pre-warm, HTTPS, referer/IP rules
- Origin weight/backup **config change** after RCA identifies fix
- Single documented CDN config error → product troubleshooting flows
- Application-level caching (Redis) → `qcloud-redis-ops`

## Return Contract

AIOps returns Event Bundle, RCA Bundle, or Anomaly Bundle per [`output-schemas.md`](../../qcloud-aiops-diagnosis/references/output-schemas.md). Product RCA uses **Rule P** in [`product-rca-rules.md`](../../qcloud-aiops-diagnosis/references/product-rca-rules.md).

## CDN-Specific Correlation Hints (Reference Only)

| Pattern | Primary Metric | Correlated | Typical fix |
|---------|---------------|------------|-------------|
| Origin 5xx | StatusCode5XX ↑ | Origin health / COS/CVM/CLB metrics | Fix origin; CDN origin config |
| Cache miss storm | CacheHitRate ↓ | Bandwidth ↑; recent purge | Review cache rules / purge scope |
| Origin timeout | CdnResponseTime ↑ | Rule G VPC or origin connect | Fix network or origin capacity |
| Edge-only 5xx | 5xx at CDN | Origin healthy | CDN edge/config regression |

Full workflow: [`qcloud-aiops-diagnosis/references/diagnostic-workflows.md`](../../qcloud-aiops-diagnosis/references/diagnostic-workflows.md) Workflow 9 → Rule P.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-13 | Initial stub — Rule P reverse delegation (Phase F) |
