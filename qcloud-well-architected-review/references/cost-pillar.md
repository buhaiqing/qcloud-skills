# Cost Pillar — Orchestrator Guide

> **Orchestrator-only.** Idle detection, right-sizing, and billing analysis are
> **delegated** to worker skills.

---

## 1. Worker mapping

| Scope | delegate-to | Assessment reference |
|-------|-------------|---------------------|
| Billing / TCO / spend trends | `qcloud-finops-ops` | `references/well-architected-assessment.md` §2 Cost |
| CPU/memory idle metrics | `qcloud-monitor-ops` | `GetMonitorData` via `references/well-architected-assessment.md` |
| CVM right-sizing / stopped instances | `qcloud-cvm-ops` | Cost section in `well-architected-assessment.md` |
| CLB / CDB / Redis / TKE / COS / ES / MongoDB / PostgreSQL | respective `qcloud-*-ops` | Product cost checklist |
| CKafka / SCF / CLS / CBS | `qcloud-ckafka-ops`, `qcloud-scf-ops`, `qcloud-cls-ops`, `qcloud-cbs-ops` | Retention, idle resources, orphan disks |
| CDN | `qcloud-cdn-ops` | Traffic / cache hit / bandwidth waste |
| AGSX | `qcloud-agsx-ops` | Sandbox-hours / idle pool (SDK read-only) |

Pass `{{user.mode}}=well-architected-readonly`, `{{user.pillars}}` includes `cost`.

> **API note:** Metric idle detection uses `GetMonitorData` (monitor worker or product worker) — not `DescribeBaseMetrics`.

---

## 2. Orchestrator checks

| Check | Source |
|-------|--------|
| FinOps spend spike vs monitor idle | [cross-product-analysis.md](cross-product-analysis.md) |
| Cost vs reliability trade-offs | Flag multi-AZ cost impact explicitly |

---

## 3. Scoring rubric

| Score | Criteria |
|-------|----------|
| 90-100 | Right-sized; prepaid where stable; no idle resources |
| 70-89 | Mostly optimized; some on-demand for stable workloads |
| 50-69 | Mixed models; idle resources unaddressed |
| < 50 | All on-demand; significant waste |

---

## 4. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-21 | Initial pillar with inline CLI |
| 1.1.0 | 2026-06-09 | Delegated to finops/monitor/product workers |
