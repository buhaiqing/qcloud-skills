---
name: qcloud-well-architected-review
description: >-
  Use when the user needs to review, audit, or assess Tencent Cloud architecture
  against the Well-Architected Framework — reliability assessment (backup/recovery,
  DR runbook, multi-AZ), security audit (CAM permissions, credential management,
  network isolation), cost optimization (idle resource detection, right-sizing),
  or efficiency improvement (batch operations, automation). Orchestrates read-only
  assessment by delegating product discovery to qcloud-cvm-ops, qcloud-clb-ops,
  qcloud-cdb-ops, qcloud-redis-ops, qcloud-tke-ops, qcloud-vpc-ops, qcloud-cos-ops,
  qcloud-es-ops, qcloud-mongodb-ops, qcloud-postgres-ops, qcloud-ssl-ops, qcloud-cdn-ops,
  qcloud-agsx-ops, qcloud-cam-ops, qcloud-monitor-ops, and qcloud-finops-ops workers;
  aggregates four-pillar scores and cross-product findings. Also triggers on architecture
  review requests, compliance checks, or performance/cost analysis. Not for resource CRUD
  (use product ops skills) or proactive inspection (use qcloud-proactive-inspection).
license: MIT
compatibility:
  - tccli >= 3.0
  - python >= 3.8
  - tencentcloud-api-credentials
metadata:
  author: qcloud
  version: "1.3.3"
  last_updated: "2026-06-09"
  type: cross-cutting-assessment
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  tags:
    - tencent-cloud
    - well-architected
    - assessment
    - architecture-review
    - orchestrator
  requirements:
    - tccli
    - jq
  python_version_minimum: "3.8"
  api_profile: "Tencent Cloud Well-Architected Framework (multi-product orchestration)"
  cli_applicability: "cli-only"
  cli_support_evidence: >-
    Orchestrator skill: does NOT execute product Describe* directly. Delegates
    read-only assessment to product worker skills (each verified via tccli help).
    Orchestrator only aggregates worker output and runs cross-product analysis.
  related_skills:
    - qcloud-cvm-ops
    - qcloud-clb-ops
    - qcloud-cdb-ops
    - qcloud-redis-ops
    - qcloud-tke-ops
    - qcloud-vpc-ops
    - qcloud-cos-ops
    - qcloud-es-ops
    - qcloud-mongodb-ops
    - qcloud-postgres-ops
    - qcloud-ssl-ops
    - qcloud-cdn-ops
    - qcloud-agsx-ops
    - qcloud-cam-ops
    - qcloud-monitor-ops
    - qcloud-finops-ops
    - qcloud-proactive-inspection
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

# Tencent Cloud Well-Architected Review Skill

## Overview

This skill is the **orchestrator** for four-pillar Well-Architected assessments on Tencent Cloud. It **does not** inline product `tccli` commands — it **delegates read-only discovery and pillar scoring** to product worker skills, then aggregates results, runs cross-product correlation, and produces the final report.

**Orchestrator vs Worker:**

| Role | Skill | Responsibility |
|------|-------|----------------|
| **Orchestrator** | `qcloud-well-architected-review` (this skill) | Scope, worker dispatch, score aggregation, cross-product analysis, report |
| **Worker** | `qcloud-cvm-ops`, `qcloud-clb-ops`, `qcloud-es-ops`, `qcloud-mongodb-ops`, … | Product-specific read APIs, pillar checklists, `{{output.product_assessment}}` |

**Four Pillars:** Reliability · Security · Cost · Efficiency

### Core Principle

**Delegate → Aggregate → Correlate → Report**

1. Resolve scope and select worker skills per [Product Worker Registry](#product-worker-registry)
2. Invoke each worker in read-only mode (`{{user.mode}}=well-architected-readonly`)
3. Aggregate worker `{{output.product_assessment}}` payloads ([schema](references/worker-output-schema.md))
4. Run [cross-product analysis](references/cross-product-analysis.md)
5. Fill [report template](assets/report-template.md) with weighted scores and recommendations

## Quick Start

### What This Skill Does

Orchestrates read-only Well-Architected assessment across products — **workers execute**, this skill **aggregates** into a scored report.

### Prerequisites

- [ ] Worker skills available for products in scope (see registry below)
- [ ] `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`, `TENCENTCLOUD_REGION` set (workers use these)
- [ ] Optional thresholds: [`assets/example-config.yaml`](assets/example-config.yaml)

### First Step (orchestrator)

1. Ask user for scope: products, pillars, region
2. **delegate-to** `qcloud-cvm-ops` with `{{user.mode}}=well-architected-readonly` (example for CVM-only review)
3. Collect `{{output.product_assessment}}` and proceed to aggregation

### Output

[`assets/report-template.md`](assets/report-template.md) · Worker contract: [`references/worker-output-schema.md`](references/worker-output-schema.md)

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When
- User asks "帮我看看当前架构是否有问题" or "do an architecture review"
- User requests security audit, cost waste analysis, reliability / SPOF check, or optimization review
- Product-specific skill delegates architecture assessment to this orchestrator
- Multi-product Well-Architected review with unified scoring is needed

### SHOULD NOT Use This Skill When
- User needs resource CRUD → **delegate-to** product ops skill (mutation)
- User asks billing detail only → **delegate-to** `qcloud-finops-ops`
- User wants proactive inspection / 巡检 → **delegate-to** `qcloud-proactive-inspection`
- User needs CAM/VPC/CLB **changes** → **delegate-to** `qcloud-cam-ops`, `qcloud-vpc-ops`, `qcloud-clb-ops`

## Variables

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Tencent Cloud Secret ID | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Secret Key (masked in output) | `***` |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region code | `ap-guangzhou` |
| `{{user.products}}` | User | Comma-separated product codes | `cvm,clb,cdb` |
| `{{user.scope}}` | User | `single-resource` or `account-wide` | `account-wide` |
| `{{user.pillars}}` | User | `all` or subset | `reliability,security` |
| `{{user.config_path}}` | User | Thresholds YAML | `assets/example-config.yaml` |
| `{{user.mode}}` | Orchestrator → Worker | Always `well-architected-readonly` when dispatching workers | `well-architected-readonly` |
| `{{output.worker_results}}` | Aggregated | Array of worker `product_assessment` objects | JSON array |
| `{{output.overall_score}}` | Computed | Weighted four-pillar score | `82` |
| `{{output.assessment_date}}` | Computed | ISO 8601 timestamp | `2026-06-09T10:00:00+08:00` |

### Credential Masking (MANDATORY)

**NEVER** expose `TENCENTCLOUD_SECRET_KEY` in reports or traces. Workers and orchestrator MUST use `<masked>`. Scan final report before output.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | Orchestrator only; mutations delegated to product skills |
| 2 | **Structured I/O** | Worker schema + `{{user.*}}` / `{{output.*}}` conventions |
| 3 | **Explicit Actionable Steps** | Pre-flight → Delegate → Aggregate → Validate → Recover |
| 4 | **Complete Failure Strategies** | Orchestrator error table + worker errors in `product_assessment.errors` |
| 5 | **Absolute Single Responsibility** | Cross-product assessment orchestration only |

## Assessment Workflow

### Pre-flight

1. Verify credentials exist (existence check only — workers run `tccli`).
2. Resolve `{{user.products}}`, `{{user.pillars}}`, `{{user.scope}}`; load `{{user.config_path}}` if set.
3. Map products → worker skills via [Product Worker Registry](#product-worker-registry).
4. Surface scope to user; list products/pillars that will be skipped.

### Execute — Delegate to Workers

For **each** product in scope, load the worker skill and invoke **Read-Only Assessment Mode**:

```text
delegate-to: qcloud-{product}-ops
inputs:
  user.mode: well-architected-readonly
  user.pillars: {{user.pillars}}
  user.scope: {{user.scope}}
  env.TENCENTCLOUD_REGION: {{env.TENCENTCLOUD_REGION}}
expected_output: {{output.product_assessment}}  # see worker-output-schema.md
```

**Cross-cutting workers** (invoke when pillar requires):

| Pillar | Extra delegate-to |
|--------|-------------------|
| Security (account) | `qcloud-cam-ops` |
| Security (network) | `qcloud-vpc-ops` |
| Cost (billing) | `qcloud-finops-ops` (read-only DescribeBill* / DescribeCost*) |
| Cost / Reliability (metrics) | `qcloud-monitor-ops` (GetMonitorData, alarm coverage) |

Workers execute product `Describe*` / `GetMonitorData` per their `references/well-architected-assessment.md`. **Orchestrator MUST NOT duplicate those commands.**

Pillar orchestration guides (worker mapping only — no inline CLI):
- [Reliability](references/reliability-pillar.md) · [Security](references/security-pillar.md) · [Cost](references/cost-pillar.md) · [Efficiency](references/efficiency-pillar.md)

### Execute — Aggregate & Correlate

1. Collect all `{{output.product_assessment}}` into `{{output.worker_results}}`
2. Per pillar: average worker scores (equal weight per product unless single-product scope)
3. Apply [cross-product-analysis.md](references/cross-product-analysis.md)
4. Fill [report-template.md](assets/report-template.md)

### Validate

- Each pillar: score OR **NOT ASSESSED** (from worker `status=not_assessed`)
- Findings include confidence HIGH/MEDIUM/LOW
- No credential leaks; cross-pillar conflicts documented

### Recover

| Situation | Action |
|-----------|--------|
| Worker returns `status=ERROR` | Log error; mark product skipped; continue other workers |
| Worker missing for product | NOT ASSESSED; recommend adding worker skill |
| All workers fail | HALT; see Error Code Reference |

## Product Worker Registry

| `user.products` code | delegate-to | Worker section |
|---------------------|-------------|----------------|
| `cvm` | `qcloud-cvm-ops` | `## Read-Only Assessment Mode` |
| `clb` | `qcloud-clb-ops` |同上 |
| `cdb` | `qcloud-cdb-ops` |同上 |
| `redis` | `qcloud-redis-ops` |同上 |
| `tke` | `qcloud-tke-ops` |同上 |
| `vpc` | `qcloud-vpc-ops` |同上 |
| `cos` | `qcloud-cos-ops` |同上 |
| `es` | `qcloud-es-ops` |同上 |
| `mongodb` | `qcloud-mongodb-ops` |同上 |
| `postgres` | `qcloud-postgres-ops` |同上 |
| `ssl` | `qcloud-ssl-ops` |同上 |
| `cdn` | `qcloud-cdn-ops` |同上 |
| `agsx` | `qcloud-agsx-ops` |同上 (sdk-only worker) |
| `finops` | `qcloud-finops-ops` | Cost/billing worker (§ Worker Output Contract) |
| _(security)_ | `qcloud-cam-ops` | Cross-cutting |
| _(metrics)_ | `qcloud-monitor-ops` | Cross-cutting (GetMonitorData, alarms) |

Output contract: [worker-output-schema.md](references/worker-output-schema.md) (v1.1) — each worker implements **Worker Output Contract** in its `references/well-architected-assessment.md`.

## Error Code Reference

> Orchestrator-level errors. Product API errors are captured in worker `errors[]`.

| Code | Recovery | Action |
|------|----------|--------|
| `WORKER_UNAVAILABLE` | SKIP | Product skill missing; mark NOT ASSESSED |
| `WORKER_PARTIAL` | CONTINUE | Use partial `product_assessment`; flag in report |
| `WORKER_TIMEOUT` | RETRY | Re-dispatch worker once |
| `AGGREGATION_EMPTY` | HALT | No worker results — check scope |
| `SCHEMA_MISMATCH` | FIX | Worker output missing required schema fields |
| `AuthFailure` | HALT | Credentials invalid for workers |
| `DELEGATION_VIOLATION` | HALT | Orchestrator ran product Describe* directly — use worker |
| `CREDENTIAL_LEAK` | HALT | Secret in report — redact and abort publish |

Extended worker API errors: see each worker skill's Error Code Reference.

## Overall Architecture Score

```
overall_score = (reliability * 0.30) + (security * 0.30) + (cost * 0.20) + (efficiency * 0.20)
```

Exclude `not_assessed` pillars from weight denominator; document excluded pillars in report.

| Pillar | Weight |
|--------|--------|
| Reliability | 30% |
| Security | 30% |
| Cost | 20% |
| Efficiency | 20% |

**Conflict priority:** Security > Reliability > Cost > Efficiency

## Delegation Matrix (Bidirectional)

### Inbound — product skills delegate TO this orchestrator

| Source Skill | Delegates To | Trigger |
|-------------|-------------|---------|
| qcloud-cvm-ops | qcloud-well-architected-review | User requests architecture review during CVM work |
| qcloud-redis-ops | qcloud-well-architected-review | Security/cost assessment |
| qcloud-tke-ops | qcloud-well-architected-review | Reliability/efficiency review |
| qcloud-cdb-ops | qcloud-well-architected-review | Full architecture audit |
| qcloud-clb-ops | qcloud-well-architected-review | Multi-product review |
| qcloud-vpc-ops | qcloud-well-architected-review | Network security audit |
| qcloud-cos-ops | qcloud-well-architected-review | Storage optimization review |
| qcloud-monitor-ops | qcloud-well-architected-review | Monitoring coverage review |
| qcloud-es-ops | qcloud-well-architected-review | ES cluster architecture / snapshot audit |
| qcloud-mongodb-ops | qcloud-well-architected-review | MongoDB HA / backup assessment |
| qcloud-postgres-ops | qcloud-well-architected-review | PostgreSQL reliability / security review |
| qcloud-ssl-ops | qcloud-well-architected-review | Certificate expiry / TLS coverage audit |
| qcloud-cdn-ops | qcloud-well-architected-review | CDN security / cost / cache efficiency |
| qcloud-agsx-ops | qcloud-well-architected-review | Agent sandbox architecture review |

### Outbound — this orchestrator delegate-to workers

| Orchestrator Need | delegate-to | Mode |
|-------------------|-------------|------|
| Product discovery & pillar checks | `qcloud-{product}-ops` | `well-architected-readonly` |
| CAM / IAM audit | `qcloud-cam-ops` | `well-architected-readonly` |
| Billing / TCO | `qcloud-finops-ops` | read-only billing APIs |
| Metrics / alarm coverage | `qcloud-monitor-ops` | `GetMonitorData`, DescribeAlarm* |
| Resource mutations from findings | product ops skill | **normal mode** (user must confirm) |

## Anti-Patterns

| Anti-Pattern | Correction |
|-------------|------------|
| Orchestrator runs `tccli cvm DescribeInstances` | delegate-to `qcloud-cvm-ops` Read-Only Assessment Mode |
| Duplicate CLI in pillar docs | Use pillar guides for worker mapping only |
| Score pillar without worker evidence | NOT ASSESSED |
| Worker executes Run/Modify/Delete during assessment | HALT worker; read-only only |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial four-pillar assessment |
| 1.1.0 | 2026-06-04 | GCL rollout |
| 1.2.0 | 2026-06-09 | Quick Start, error table, GCL templates |
| 1.3.0 | 2026-06-09 | Orchestrator + Worker architecture |
| 1.3.1 | 2026-06-09 | Worker registry: es, mongodb, postgres, ssl, cdn, agsx |
| 1.3.2 | 2026-06-09 | worker-output-schema v1.1; product well-architected-assessment.md aligned |
| 1.3.3 | 2026-06-09 | `qcloud-finops-ops` well-architected-assessment.md (Cost worker) |

## Quality Gate (GCL)

| Property | Value |
|---|---|
| GCL applicability | **optional** |
| `max_iterations` | **5** |
| Rubric | [`references/rubric.md`](references/rubric.md) |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) |

### Safety rules (rubric §5)

1. Scope clarity — NOT ASSESSED for skipped pillars/products
2. Read-only delegation — workers only; orchestrator does not mutate
3. No false certainty — confidence on every finding
4. Cross-pillar consistency — document trade-offs
5. Worker registry respect — only listed delegate-to targets

**Advisory/read-only.** No hard ABORT on Safety=0 except credential leak or mutation.

---

## See also

- [worker-output-schema.md](references/worker-output-schema.md) — worker return contract
- [cross-product-analysis.md](references/cross-product-analysis.md) — orchestrator correlation
- [troubleshooting.md](references/troubleshooting.md) — delegation failures
