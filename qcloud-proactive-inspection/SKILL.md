---
name: qcloud-proactive-inspection
description: >-
  Use when the user needs to run proactive inspections, scheduled audits,
  resource health checks, or generate inspection reports for Tencent Cloud
  resources. Triggers on "做一次巡检", "生成巡检报告", "健康检查", "资源审计",
  "排查潜在风险", "compliance audit", or any scenario requiring systematic
  Discovery → Collection → Detection → Diagnosis → Report workflow across
  CVM, Redis, CDB, ES, TKE, CLB, VPC, COS products. Not for reactive
  incident response (use qcloud-aioops-diagnosis) or live resource CRUD
  (use product-specific ops skills).
license: MIT
compatibility: >-
  Tencent Cloud CLI (`tccli`), Python 3.8+ runtime for metric collection
  and report generation, valid API credentials, network access to Tencent
  Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-21"
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

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When
- User requests proactive inspection: "帮我做一次巡检"
- User needs scheduled audit: "每周做一次资源审计"
- User wants health report: "生成一份健康报告"
- Pre-production review: "上线前做一次全面检查"
- Compliance audit: "做一次安全合规检查"
- Risk identification: "有哪些潜在风险"

### SHOULD NOT Use This Skill When
- Active incident response → delegate to qcloud-aioops-diagnosis
- Architecture design review → delegate to qcloud-well-architected-review
- Resource CRUD operations → delegate to product-specific ops skill
- Single resource troubleshooting → use product-specific skill directly

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
Enumerate all resources to inspect:
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

For detailed inspection patterns, see:
- [Discovery Patterns](references/discovery.md) — Resource enumeration techniques
- [Collection Methods](references/collection.md) — Metric collection patterns
- [Detection Rules](references/detection.md) — Anomaly detection thresholds
- [Diagnosis Workflows](references/diagnosis.md) — Root cause analysis per anomaly
- [Reporting Templates](references/reporting.md) — Report generation and formats
