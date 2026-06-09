# Cross-Product Analysis (Orchestrator-Only)

> Executed by `qcloud-well-architected-review` **after** worker skills return
> `{{output.product_assessment}}`. Workers MUST NOT perform cross-product correlation.

---

## 1. Correlation patterns

| Pattern | Worker inputs | Orchestrator check |
|---------|---------------|-------------------|
| CVM + CLB HA | `cvm` AZ distribution + `clb` target health | CLB backends span ≥2 AZs when CVM is multi-AZ |
| CVM + VPC exposure | `cvm` public IP count + `vpc` SG rules | Public IPs justified; SG not `0.0.0.0/0` on admin ports |
| Data + backup | `cdb`/`redis` backup status + `cvm` snapshot policy | Production tier has backup on all stateful services |
| Cost + monitor | `finops` spend signal + `monitor` CPU idle | Idle instances flagged in both cost and monitor workers |
| Security baseline | `cam` least-privilege + all product workers | No worker reports open SG while cam reports wildcard policies |
| CKafka + consumer apps | `ckafka` lag/RF + `scf`/`cvm` workers | Production topics RF≥2; sustained lag has scaling plan |
| SCF + triggers | `scf` DLQ/retry + `ckafka`/`cos` workers | Async functions have DLQ; trigger sources healthy |
| CLS + audit | `cls` retention/shipping + `cam` worker | Audit logsets retained; shipping to COS for DR |
| CBS orphan + FinOps | `cbs` unattached disks + `finops` spend | Orphan disks flagged in both cost and storage workers |
| CBS + CVM overlap | `cbs` + `cvm` workers | Attached-disk backup scored in CVM; orphan/unattached in CBS — dedupe findings in report |

---

## 2. Conflict resolution

When worker recommendations conflict, apply SKILL.md priority:

**Security > Reliability > Cost > Efficiency**

Document trade-offs explicitly in the final report (e.g., multi-AZ increases cost).

---

## 3. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-06-09 | Initial cross-product correlation guide |
| 1.1.0 | 2026-06-09 | CKafka/SCF/CLS/CBS patterns; CBS–CVM dedupe note |
