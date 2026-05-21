---
name: qcloud-aioops-diagnosis
description: >-
  Use when the user needs intelligent diagnosis, root cause analysis, or anomaly
  detection for Tencent Cloud resources — CPU/memory spikes, connection failures,
  alarm storms, timeout patterns, OOM detection, slow queries, log pattern
  recognition, multi-metric correlation, or proactive anomaly identification.
  Triggers on phrases like "排查问题", "帮我诊断", "CPU 突然飙高", "告警风暴",
  "分析日志异常", "找出根因", or any scenario requiring automated fault detection
  across CVM, Redis, CDB, ES, TKE, CLB, VPC, COS products. Not for live resource
  CRUD operations unless paired with a product-specific ops skill.
license: MIT
compatibility: >-
  Tencent Cloud CLI (`tccli`), Python 3.8+ runtime for metric collection and
  log analysis, valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-21"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: cross-cutting-diagnosis
  python_version_minimum: "3.8"
  api_profile: "Tencent Cloud Monitor API + product-specific Diagnose APIs"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Uses tccli monitor DescribeBaseMetrics for metric queries,
    tccli monitor DescribeAlarmHistory for alarm analysis,
    plus product-specific DescribeDiagnostic APIs.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

# Tencent Cloud AIOps Diagnosis Skill

## Overview

This skill provides **intelligent, automated diagnosis** for Tencent Cloud resources using the **three-dimensional optimization framework**: Fault Diagnosis → Root Cause Localization → Rapid Resolution. It consolidates multi-metric correlation, log intelligence analysis, alarm storm handling, and diagnostic decision trees into a single cross-product diagnosis engine.

**Operates independently** for ad-hoc diagnosis requests, or as a **delegated target** from product-specific ops skills (qcloud-cvm-ops, qcloud-redis-ops, etc.) for intelligent fault analysis.

### Core Pattern

```
Symptom Detection → Metric Analysis → Log Correlation → Diagnosis Conclusion → Resolution Strategy
```

### Three-Dimensional Framework

1. **Fault Diagnosis (故障诊断)** — Symptom categorization, multi-metric correlation, decision trees
2. **Root Cause Localization (根因定位)** — Narrow problem space, identify root cause vs symptoms
3. **Rapid Resolution (快速恢复)** — Prioritized recovery actions, safe rollback paths

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When
- User reports performance issues: "服务很慢", "CPU 飙高", "内存爆了"
- User reports connection issues: "连不上了", "Connection refused", "超时"
- Alarm storm: "告警太多了", "一直在报警"
- Log analysis: "分析下这些日志有什么问题"
- Root cause request: "帮我找下根因", "为什么会这样"
- Proactive anomaly: "有什么异常需要关注的"
- Product skill delegates intelligent diagnosis here

### SHOULD NOT Use This Skill When
- User needs resource CRUD → delegate to product-specific ops skill
- User asks about architecture design → delegate to qcloud-well-architected-review
- User requests cost analysis → delegate to FinOps tools
- Single known issue with documented fix → use product troubleshooting directly

## Variables

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Tencent Cloud Secret ID | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Tencent Cloud Secret Key | `***` (masked) |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region code | `ap-guangzhou` |
| `{{user.resource_id}}` | User | Target resource ID for diagnosis | `ins-xxxxxx` |
| `{{user.resource_type}}` | User | Product type (cvm, redis, cdb, tke, es) | `cvm` |
| `{{user.time_range}}` | User | Diagnosis time window | `1h`, `24h` |
| `{{user.log_source}}` | User | Log collection endpoint | `loki`, `cls` |

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | Diagnosis-only scope; delegates mutation to product skills |
| 2 | **Structured I/O** | Symptom input → diagnosis output with severity, cause, fix |
| 3 | **Explicit Actionable Steps** | 5-step workflow: detect → analyze → correlate → diagnose → resolve |
| 4 | **Complete Failure Strategies** | API rate limits, missing metrics fallback, partial data handling |
| 5 | **Absolute Single Responsibility** | One skill = diagnosis; no resource creation/modification |

## Diagnosis Workflow

### Step 1: Symptom Detection
Classify the symptom into one of four categories:
- **Performance** — Slow response, high latency, CPU/memory spike
- **Availability** — Connection failed, timeout, health check failure
- **Capacity** — Quota exceeded, disk full, bandwidth limit reached
- **Security** — Access denied, unauthorized API calls, credential issues

### Step 2: Metric Analysis
Query relevant metrics for the resource:
```bash
# CVM CPU usage via Monitor API
tccli monitor DescribeBaseMetrics \
  --MetricName CPUUsage \
  --Namespace QCE/CVM \
  --Dimensions '[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]'
```

### Step 3: Log Correlation
Search logs for patterns matching the time window:
- Error spikes, exception traces, timeout patterns
- OOM events, connection refused, slow queries
- See [Log Intelligence](references/log-intelligence.md) for pattern library

### Step 4: Diagnosis
Apply decision tree (see [Diagnosis Framework](references/diagnosis-framework.md)):
```
symptom=performance
  → CPU > 90%?
    → NetworkIn high? → Traffic spike → Scale out / Rate limit
    → NetworkIn normal? → App CPU-bound → Profile / Optimize code
  → MemUsage > 90%?
    → OOM in logs? → Memory leak → Restart + Fix leak
    → No OOM? → Undersized → Right-size
```

### Step 5: Resolution
Provide prioritized recovery actions with effort estimates.

## Anti-Patterns

| Anti-Pattern | Manifestation | Correction |
|-------------|---------------|------------|
| Symptom ≠ root cause | Treating CPU spike as root cause | Drill down to what caused the spike |
| Single-metric tunnel vision | Only looking at CPU | Always correlate 3+ metrics |
| Alarm fatigue | Treating all alarms equally | Categorize, deduplicate, prioritize |
| Missing time context | Analyzing logs without time window | Always use {{user.time_range}} |

---

For detailed diagnosis patterns, see:
- [Diagnosis Framework](references/diagnosis-framework.md) — 3D optimization framework
- [Log Intelligence](references/log-intelligence.md) — Pattern recognition, anomaly detection
- [Diagnostic Workflows](references/diagnostic-workflows.md) — Decision trees per symptom
- [Alarm Handling](references/alarm-handling.md) — Storm handling, noise reduction
- [Delegation Matrix](references/delegation-matrix.md) — Cross-skill diagnosis routing
