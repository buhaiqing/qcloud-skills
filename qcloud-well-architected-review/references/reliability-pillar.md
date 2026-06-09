# Reliability Pillar — Orchestrator Guide

> **Orchestrator-only.** Product-specific discovery and scoring are **delegated** to worker
> skills. Do NOT inline `tccli` commands here — use the worker mapping below.

---

## 1. Worker mapping

| Product | delegate-to | Assessment reference |
|---------|-------------|---------------------|
| CVM | `qcloud-cvm-ops` | `references/well-architected-assessment.md` § Reliability |
| CLB | `qcloud-clb-ops` | `references/well-architected-assessment.md` § Reliability |
| CDB | `qcloud-cdb-ops` | `references/well-architected-assessment.md` § Reliability |
| Redis | `qcloud-redis-ops` |同上 |
| TKE | `qcloud-tke-ops` |同上 |
| MongoDB | `qcloud-mongodb-ops` |同上 |
| PostgreSQL | `qcloud-postgres-ops` |同上 |
| ES | `qcloud-es-ops` | Snapshot / multi-node HA |
| COS | `qcloud-cos-ops` |同上 |
| VPC | `qcloud-vpc-ops` | `references/well-architected-assessment.md` § Reliability |
| Monitor (coverage) | `qcloud-monitor-ops` | Alarm/health coverage for reliability signals |

Pass orchestrator inputs: `{{user.mode}}=well-architected-readonly`, `{{user.pillars}}` includes `reliability`.

---

## 2. Orchestrator checks (after workers return)

| Check | Source |
|-------|--------|
| Multi-AZ consistency CVM ↔ CLB | [cross-product-analysis.md](cross-product-analysis.md) |
| Backup gap on stateful services | Merge `cdb` + `redis` + `mongodb` + `postgres` + `es` + `cvm` worker findings |
| Skipped products | Mark reliability pillar `not_assessed` — do not score |

---

## 3. Scoring rubric (orchestrator aggregates worker scores)

| Score | Criteria |
|-------|----------|
| 90-100 | All workers report multi-AZ/backup/DR signals pass |
| 70-89 | Partial multi-AZ or backup configured but untested |
| 50-69 | Single AZ or manual backup only |
| < 50 | No backup / no recovery plan |

---

## 4. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-21 | Initial pillar with inline CLI |
| 1.1.0 | 2026-06-09 | Orchestrator guide; CLI delegated to product workers |
