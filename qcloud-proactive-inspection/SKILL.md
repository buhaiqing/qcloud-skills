---
name: qcloud-proactive-inspection
description: >-
  Use when the user needs to run proactive inspections, scheduled audits,
  resource health checks, or generate inspection reports for Tencent Cloud
  resources. Triggers on "做一次巡检", "生成巡检报告", "健康检查", "资源审计",
  "排查潜在风险", "compliance audit", or any scenario requiring systematic
  Discovery → Collection → Detection → Diagnosis → Report workflow across
  CVM, Redis, CDB, ES, TKE, CLB, VPC, COS products. Not for reactive
  incident response (use qcloud-aiops-diagnosis) or live resource CRUD
  (use product-specific ops skills).
license: MIT
compatibility: >-
  Tencent Cloud CLI (`tccli`), Python 3.8+ runtime for metric collection
  and report generation, valid API credentials, network access to Tencent
  Cloud endpoints.
metadata:
  author: qcloud
  version: "1.3.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: cross-cutting-inspection
  python_version_minimum: "3.8"
  api_profile: "Multi-product Describe* operations + Monitor API"
  cli_applicability: "cli-first"
  cli_support_evidence: >-
    Uses tccli Describe* across all Tencent Cloud products for resource
    enumeration and configuration audit. Python SDK for batch metric
    collection and report generation.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  related_skills:
    - qcloud-finops-ops   # 反向：finops 异常检测（HIGH 置信度）可自动派发巡检工单到本 skill
---

# Tencent Cloud Proactive Inspection Skill

## Overview

This skill implements the **five-step closed-loop proactive inspection workflow**:

```
Discovery → Collection → Detection → Diagnosis → Report
  (发现)      (采集)      (检测)       (诊断)       (报告)
```

It enables agents to systematically inspect Tencent Cloud resources for potential issues **before they become incidents**, generating structured reports with risk assessments and remediation recommendations.

**Operates independently** for scheduled inspections, or as a **delegated target** from product-specific ops skills for proactive health checks.

### Core Principle

**Proactive > Reactive.** Inspect resources regularly using configurable thresholds, detect anomalies early, diagnose root causes, and report actionable findings.

### Boundary vs Well-Architected Review

| Skill | Purpose | Output |
|-------|---------|--------|
| **This skill** (`qcloud-proactive-inspection`) | Threshold-based health check (CPU/disk/expiry) | Inspection report with Warning/Critical |
| **`qcloud-well-architected-review`** | Four-pillar scored architecture assessment | `product_assessment` JSON + architecture report |

Route **「做一次架构审查 / Well-Architected 评估」** → `qcloud-well-architected-review`, **not** this skill.

## Product Skill Delegation (Discovery)

> Prefer **product ops skills** for read-only discovery/collection. Inline `tccli` in Step 1 below is **fallback** when no product skill exists.

| `{{user.products}}` | delegate-to | Product checklist |
|---------------------|-------------|-------------------|
| `cvm` | `qcloud-cvm-ops` | [proactive-inspection.md](../qcloud-cvm-ops/references/proactive-inspection.md) |
| `clb` | `qcloud-clb-ops` | [proactive-inspection.md](../qcloud-clb-ops/references/proactive-inspection.md) |
| `cdb` | `qcloud-cdb-ops` |同上 |
| `redis` | `qcloud-redis-ops` |同上 |
| `tke` | `qcloud-tke-ops` |同上 |
| `vpc` | `qcloud-vpc-ops` |同上 |
| `cos` | `qcloud-cos-ops` |同上 |
| `es` / `mongodb` / `postgres` | respective ops skill | Product detection rules |
| `ckafka` / `scf` / `cls` / `cbs` | respective ops skill |同上 |
| `cdn` / `ssl` / `agsx` | respective ops skill |同上 |
| billing slice | `qcloud-finops-ops` | Spend anomaly in inspection checklist |
| metrics | `qcloud-monitor-ops` | GetMonitorData for Step 2 collection |

**Output contract:** each product returns `{{output.inspection_findings}}` per [inspection-output-schema.md](references/inspection-output-schema.md).

Pass `{{user.mode}}=inspection-readonly` (implicit); product skills MUST NOT mutate resources during inspection delegation.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When
- User requests proactive inspection: "帮我做一次巡检"
- User needs scheduled audit: "每周做一次资源审计"
- User wants health report: "生成一份健康报告"
- Pre-production review: "上线前做一次全面检查"
- Compliance audit: "做一次安全合规检查"
- Risk identification: "有哪些潜在风险"

### SHOULD NOT Use This Skill When
- Active incident response → delegate to qcloud-aiops-diagnosis
- Architecture design review → delegate to qcloud-well-architected-review
- Resource CRUD operations → delegate to product-specific ops skill
- Single resource troubleshooting → use product-specific skill directly
- 协同场景：`qcloud-finops-ops` 检测到 HIGH 置信度账单异常时，自动派发巡检工单到本 skill；本 skill 巡检清单内置"账单检查"项

## Variables

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Tencent Cloud Secret ID | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Tencent Cloud Secret Key | `***` (masked) |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region code | `ap-guangzhou` |
| `{{user.products}}` | User | Products to inspect (cvm, redis, cdb, tke, etc.) | `cvm,redis` |
| `{{user.thresholds}}` | User | Custom thresholds override | JSON |
| `{{user.report_format}}` | User | Output format (markdown, json) | `markdown` |

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | Read-only inspection scope; delegates mutation to product skills |
| 2 | **Structured I/O** | Product input → inspection report output with structured findings |
| 3 | **Explicit Actionable Steps** | 5-step workflow: each step has numbered operations |
| 4 | **Complete Failure Strategies** | API rate limit handling, partial resource skip, retry logic |
| 5 | **Absolute Single Responsibility** | One skill = proactive inspection only |

## Inspection Workflow

### Step 1: Discovery (发现)

**Primary path:** For each product in `{{user.products}}`, **delegate-to** the product ops skill (see [Product Skill Delegation](#product-skill-delegation-discovery)) for read-only resource enumeration.

**Fallback path** (product skill unavailable): direct `tccli Describe*` with pagination:
```bash
# Discover CVM instances
tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 100

# Discover Redis instances
tccli redis DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 100

# Tag-based discovery
tccli cvm DescribeInstances \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --Filters '[{"Name":"tag:Environment","Values":["Production"]}]'
```

### Step 2: Collection (采集)
Collect metrics for each discovered resource:
- CPU usage, memory usage, disk I/O, network throughput
- Connection counts, QPS, latency percentiles
- Configuration state (security groups, backup status, expiry dates)

### Step 3: Detection (检测)
Apply detection rules against collected metrics:
- **CPU threshold**: > 90% sustained = Warning, > 97% = Critical
- **Memory threshold**: > 90% = Warning, > 95% = Critical
- **Disk threshold**: > 85% = Warning, > 95% = Critical
- **Connection threshold**: > 80% of max = Warning
- **Expiry detection**: Resources expiring < 30 days = Warning

### Step 4: Diagnosis (诊断)
For each detected anomaly, apply root cause analysis:
- CPU spike → check network, queries, deployments
- Memory growth → check for leaks, cache growth
- Disk usage → check logs, temp files, backups

### Step 5: Report (报告)
Generate structured inspection report with:
- Executive summary (overall health score, risk count)
- Detail breakdown per resource
- Prioritized remediation recommendations
- Actionable items table

## Configurable Thresholds

Default thresholds (override via `{{user.thresholds}}`):

| Metric | Warning | Critical | Unit |
|--------|---------|----------|------|
| CPU Usage | 90 | 97 | % |
| Memory Usage | 90 | 95 | % |
| Disk Usage | 85 | 95 | % |
| Disk Remaining | 100 | 50 | GB |
| Connection Ratio | 80 | 90 | % |
| QPS Drop | 30 | 50 | % from baseline |

## Anti-Patterns

| Anti-Pattern | Manifestation | Correction |
|-------------|---------------|------------|
| Incomplete discovery | Missing some resources | Always paginate, use tag filters |
| Threshold fatigue | Too many false positives | Use sustained thresholds, not instant |
| Report without action | Listing problems without fixes | Every finding must have remediation |
| One-time inspection | Not establishing regularity | Recommend inspection schedule |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial release — 5-step inspection pipeline (Discovery → Collection → Detection → Diagnosis → Report) |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 rules: run idempotency, read-only collection, credential safety, snapshot timing, report path security), `references/prompt-templates.md`. `max_iter=3` per AGENTS.md §8 |
| 1.2.0 | 2026-06-09 | Product skill delegation for Discovery; boundary vs `qcloud-well-architected-review` |
| 1.3.0 | 2026-06-09 | `inspection-output-schema.md`; 20 product `proactive-inspection.md` checklists |
| 1.4.0 | 2026-06-13 | GCL Phase 3: embed `gcl-quality-summary` in inspection report (`reporting.md`) |

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **recommended** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### Safety rules (rubric §4)

1. **Run idempotency** — check duplicate scope/time within 1h; track inspection ID
2. **Read-only collection** — no mutations; no alarm/notification triggers
3. **Credential safety** — mask secrets in report output
4. **Snapshot clarity** — surface time range; add "state as of <timestamp>"
5. **Report path security** — no world-readable paths; no public upload without confirmation

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

---

For detailed inspection patterns, see:
- [inspection-output-schema.md](references/inspection-output-schema.md) — Product → orchestrator handoff JSON
- [Discovery Patterns](references/discovery.md) — Resource enumeration techniques
- [Collection Methods](references/collection.md) — Metric collection patterns
- [Detection Rules](references/detection.md) — Anomaly detection thresholds
- [Diagnosis Workflows](references/diagnosis.md) — Root cause analysis per anomaly
- [Reporting Templates](references/reporting.md) — Report generation and formats (incl. GCL quality §Phase 3)
