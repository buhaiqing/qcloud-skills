# Efficiency Pillar — Orchestrator Guide

> **Orchestrator-only.** Automation, batch ops, and API patterns are **delegated** to
> product worker skills.

---

## 1. Worker mapping

| Product | delegate-to | Assessment reference |
|---------|-------------|---------------------|
| CVM | `qcloud-cvm-ops` | Batch ops, auto-scaling, scheduling |
| CLB | `qcloud-clb-ops` | Listener/target batch patterns |
| TKE | `qcloud-tke-ops` | HPA, CI/CD, cluster automation |
| CDB / Redis | respective ops skill | Parameter templates, batch maintenance |
| ES / MongoDB / PostgreSQL | respective ops skill | Index/sharding ops, maintenance windows |
| CDN | `qcloud-cdn-ops` | Cache purge automation, origin pull patterns |
| SSL | `qcloud-ssl-ops` | Auto-renewal, cert deployment automation |
| AGSX | `qcloud-agsx-ops` | Batch sandbox, image prewarm (SDK) |
| COS | `qcloud-cos-ops` | Lifecycle automation |

Pass `{{user.mode}}=well-architected-readonly`, `{{user.pillars}}` includes `efficiency`.

---

## 2. Orchestrator checks

- Pagination completeness: workers must report if discovery was partial
- IaC / CI/CD signals: aggregate from worker `findings` — orchestrator does not scan repos

---

## 3. Scoring rubric

| Score | Criteria |
|-------|----------|
| 90-100 | Full automation; batch ops; auto-scaling |
| 70-89 | Partial automation |
| 50-69 | Mostly manual |
| < 50 | Console-only operations |

---

## 4. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-21 | Initial pillar with inline Python/CLI |
| 1.1.0 | 2026-06-09 | Delegated to product workers |
