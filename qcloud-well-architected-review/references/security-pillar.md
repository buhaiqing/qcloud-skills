# Security Pillar — Orchestrator Guide

> **Orchestrator-only.** CAM, network isolation, and product encryption checks are
> **delegated** to worker skills.

---

## 1. Worker mapping

| Scope | delegate-to | Assessment reference |
|-------|-------------|---------------------|
| CAM / IAM (account-wide) | `qcloud-cam-ops` | `references/well-architected-assessment.md` |
| VPC / SG / NACL | `qcloud-vpc-ops` | `references/well-architected-assessment.md` |
| CVM | `qcloud-cvm-ops` | SSH keys, SG attachment, encryption |
| CLB | `qcloud-clb-ops` | HTTPS, cert, listener exposure |
| CDB / Redis / TKE / COS | respective `qcloud-*-ops` | Product `well-architected-assessment.md` |
| MongoDB / PostgreSQL / ES | `qcloud-mongodb-ops`, `qcloud-postgres-ops`, `qcloud-es-ops` | Data-layer encryption, network isolation |
| SSL / CDN (TLS edge) | `qcloud-ssl-ops`, `qcloud-cdn-ops` | Cert expiry, HTTPS, access control |

Pass `{{user.mode}}=well-architected-readonly`, `{{user.pillars}}` includes `security`.

**CAM worker** focuses on: least privilege, wildcard policies, MFA, key age (read-only List/Get APIs).

---

## 2. Orchestrator checks

| Check | Source |
|-------|--------|
| SG `0.0.0.0/0` vs CAM wildcard | [cross-product-analysis.md](cross-product-analysis.md) |
| Public IP justification | Correlate `cvm` + `vpc` worker findings |

---

## 3. Scoring rubric

| Score | Criteria |
|-------|----------|
| 90-100 | CAM + network workers pass; encryption at rest + transit |
| 70-89 | Role-based access; minor public exposure justified |
| 50-69 | Basic SG; gaps in encryption or MFA |
| < 50 | Default VPC, open SG, credentials at risk |

---

## 4. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-21 | Initial pillar with inline CLI |
| 1.1.0 | 2026-06-09 | Delegated to cam/vpc/product workers |
