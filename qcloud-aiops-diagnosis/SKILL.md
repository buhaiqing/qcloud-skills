---
name: qcloud-aiops-diagnosis
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
  version: "1.5.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: cross-cutting-diagnosis
  python_version_minimum: "3.8"
  api_profile: "Tencent Cloud Monitor API + product-specific Diagnose APIs"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Uses tccli monitor DescribeBaseMetrics/GetMonitorData for metric queries,
    tccli monitor DescribeAlarmHistories for alarm analysis,
    plus product-specific read-only Describe* APIs.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  related_skills:
    - qcloud-finops-ops   # 反向：异常账单根因分析可与本 skill 协同（finops 触发，aiops 提供多指标诊断）
    - qcloud-tke-ops       # 反向：TKE 告警降噪与事件聚合能力集成（tke 触发告警风暴，aiops 提供聚合诊断）
    - qcloud-monitor-ops   # 反向：Monitor 告警历史与指标查询被 aiops 告警聚合管道使用
    - qcloud-cvm-ops       # 反向：节点/实例压力证据与 VM 诊断建议委托
    - qcloud-clb-ops       # 反向：CLB 5xx/backend health 与 TKE 后端链路关联
    - qcloud-vpc-ops       # 反向：变更关联 Rule F4 网络/SG 证据委托只读采集
    - qcloud-cam-ops       # 反向：CloudAudit 凭证/权限类变更证据
    - qcloud-cdb-ops       # 反向：Rule H CDB 慢查询/连接链只读证据与修复委托
    - qcloud-redis-ops     # 反向：Rule I Redis 内存/连接风暴诊断委托
    - qcloud-es-ops        # 反向：Rule J ES 集群红黄/索引延迟诊断委托
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

## Quick Start

### What This Skill Does
Diagnoses incidents and aggregates noisy alarms into evidence-backed findings. For TKE alarm storms, it produces an Event Bundle with root alarm, output-only symptom de-prioritization, confidence, evidence, data quality, and delegated recommendations. For multi-source incidents spanning Pod, Node, CLB, and CVM, it performs cross-layer topology linking, hypothesis scoring, and produces an RCA Bundle with ranked root cause candidates and verification steps (see [`multi-source-rca.md`](references/multi-source-rca.md)). **Change correlation** (CloudAudit + CLS rollout events) and a unified **Incident Timeline** narrative link deployments/config changes to symptoms (see [`change-correlation.md`](references/change-correlation.md), [`incident-timeline.md`](references/incident-timeline.md)). **Dynamic baseline anomaly detection** compares metrics against yesterday/last-week same windows before applying static thresholds (see [`anomaly-detection.md`](references/anomaly-detection.md)). **Product RCA rules** (CDB/Redis/ES) and **VPC network path diagnosis** (Rule G) extend cross-layer coverage (see [`product-rca-rules.md`](references/product-rca-rules.md), [`network-rca.md`](references/network-rca.md)).

### Prerequisites
- [ ] `tccli` available for read-only Monitor/TKE/CLS queries
- [ ] Credentials configured in environment; never print secret values
- [ ] Region and time window known (`{{env.TENCENTCLOUD_REGION}}`, `{{user.time_range}}`)

### First Diagnostic Request

```text
Analyze TKE alarm storm for cluster {{user.cluster_id}} in the last {{user.time_range}} and output an Event Bundle.
```

```text
Diagnose CLB 5xx by correlating with backend pod/node/CVM evidence for cluster {{user.cluster_id}} and output an RCA Bundle.
```

```text
Pod CrashLoopBackOff started right after a deployment — correlate CloudAudit/CLS change events and output RCA Bundle with Incident Timeline.
```

```text
Scan CVM {{user.resource_id}} for baseline anomalies in {{user.time_range}} (vs yesterday and last week) and output Anomaly Bundle.
```

```text
CDB 慢查询导致应用超时 — 关联 CLB 5xx 和 VPC 网络路径，输出 RCA Bundle（Rule H + Rule G）。
```

### Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|---|---|---|
| Reliability | TKE alarm grouping, root-vs-symptom event bundling, evidence-backed data quality | `references/alarm-handling.md` |
| Security | Read-only collection; credential masking; no mutation | `references/rubric.md` |
| Cost | Capacity/cost signals delegated to FinOps or product skill | `references/delegation-matrix.md` |
| Efficiency | Alarm dedupe, baseline-first anomaly (fewer false positives), storm bundling | `references/alarm-handling.md`, `references/anomaly-detection.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When
- User reports performance issues: "服务很慢", "CPU 飙高", "内存爆了"
- User reports connection issues: "连不上了", "Connection refused", "超时"
- Alarm storm: "告警太多了", "一直在报警"
- TKE alarm aggregation: "TKE 告警风暴", "告警降噪", "告警聚合", "事件聚合", "node not ready 告警", "pod crash 告警太多", "CLB 5xx 关联 TKE 诊断"
- Multi-source root cause: "多源根因", "Pod Node CLB CVM 关联诊断", "跨层根因定位", "CLB 5xx 根因是 Pod 还是 Node", "节点压力导致 Pod 崩溃", "CVM 饱和导致 TKE 异常", "跨产品关联分析"
- Log analysis: "分析下这些日志有什么问题"
- Root cause request: "帮我找下根因", "为什么会这样"
- Proactive anomaly: "有什么异常需要关注的", "指标同比昨天异常", "动态基线检测", "是不是周期性高峰", "CPU 没超 90% 但比平时高很多"
- Baseline anomaly scan: "同环比异常扫描", "输出 Anomaly Bundle", "和上周比有没有异常"
- Change correlation: "发布后出现故障", "刚改完配置就挂了", "deployment 后 CLB 5xx", "变更导致回归", "CloudAudit 查下最近谁改了什么"
- Incident timeline: "按时间线梳理故障经过", "变更和告警的先后顺序", "输出 incident timeline"
- CDB/Redis/ES RCA: "数据库慢查询根因", "Redis 内存暴涨连接打满", "ES 集群变红", "CDB 导致 CLB 超时"
- Network path RCA: "连不上但实例正常", "安全组变更后超时", "VPC 路由问题", "NAT 网关异常", "Node NotReady 但 CVM 正常是不是网络"
- Product skill delegates intelligent diagnosis here

### SHOULD NOT Use This Skill When
- User needs resource CRUD → delegate to product-specific ops skill
- User asks about architecture design → delegate to qcloud-well-architected-review
- User requests cost analysis / 异常账单根因 → delegate to `qcloud-finops-ops`
- 协同场景：`qcloud-finops-ops` 触发异常检测后，可调用本 skill 做多指标根因分析（CPU 飙高 + 账单上涨的联合诊断）
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
| `{{user.cluster_id}}` | User | TKE cluster ID for alarm aggregation | `cls-xxxxxx` |
| `{{user.time_start}}` | User | Aggregation window start (ISO 8601; convert to epoch seconds for Monitor/CLS queries) | `2026-06-09T10:00:00+08:00` |
| `{{user.time_end}}` | User | Aggregation window end (ISO 8601; convert to epoch seconds for Monitor/CLS queries) | `2026-06-09T11:00:00+08:00` |
| `{{user.time_start_epoch}}` | Derived/User | Aggregation start as Unix epoch seconds for `DescribeAlarmHistories` / `SearchLog` | `1780970400` |
| `{{user.time_end_epoch}}` | Derived/User | Aggregation end as Unix epoch seconds for `DescribeAlarmHistories` / `SearchLog` | `1780974000` |
| `{{user.tke_event_logset_id}}` | User | Optional CLS logset ID that owns the TKE Kubernetes event topic | `logset-xxxxxx` |
| `{{user.tke_event_topic_id}}` | User | Optional CLS topic ID for TKE Kubernetes events | `topic-xxxxxx` |
| `{{user.node_pool_id}}` | User | Optional TKE node pool ID for capacity detail | `np-xxxxxx` |
| `{{user.addon_name}}` | User | Optional TKE addon name for addon degradation analysis | `coredns` |
| `{{user.pod_cpu_filter}}` | User | Optional CPU filter required only for best-effort `DescribePodsBySpec` fallback | `0.5` |
| `{{user.pod_memory_filter}}` | User | Optional memory filter required only for best-effort `DescribePodsBySpec` fallback | `1` |
| `{{user.load_balancer_id}}` | User | Optional CLB ID for 5xx/backend health correlation | `lb-xxxxxx` |
| `{{user.instance_id}}` | User | Optional CVM instance ID for node-level RCA correlation | `ins-xxxxxx` |
| `{{user.namespace}}` | User | Optional K8s namespace for workload-scoped change correlation | `prod` |
| `{{user.workload}}` | User | Optional Deployment/StatefulSet name for Rule F matching | `api-deploy` |
| `{{user.app_log_topic_id}}` | User | Optional CLS topic for app config-change log patterns | `topic-xxxxxx` |
| `{{user.baseline_yesterday_start}}` | Derived | Yesterday baseline window start (ISO; `time_start` − 24h) | `2026-06-08T10:00:00+08:00` |
| `{{user.baseline_yesterday_end}}` | Derived | Yesterday baseline window end (ISO; `time_end` − 24h) | `2026-06-08T11:00:00+08:00` |
| `{{user.baseline_week_start}}` | Derived | Last-week baseline window start (ISO; `time_start` − 7d) | `2026-06-02T10:00:00+08:00` |
| `{{user.baseline_week_end}}` | Derived | Last-week baseline window end (ISO; `time_end` − 7d) | `2026-06-02T11:00:00+08:00` |
| `{{user.anomaly_mode}}` | User | `baseline_primary` (default) or `static_only` | `baseline_primary` |
| `{{user.vpc_id}}` | User | VPC ID for Rule G network path diagnosis | `vpc-xxxxxx` |
| `{{user.security_group_id}}` | User | Optional SG ID when known | `sg-xxxxxx` |
| `{{user.subnet_id}}` | User | Optional subnet ID for route/NAT linkage | `subnet-xxxxxx` |

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | Diagnosis-only scope; delegates mutation to product skills |
| 2 | **Structured I/O** | Symptom input → diagnosis output with severity, cause, fix |
| 3 | **Explicit Actionable Steps** | 5-step workflow: detect → analyze → correlate → diagnose → resolve |
| 4 | **Complete Failure Strategies** | API rate limits, missing metrics fallback, partial data handling, TKE alarm collection failures → partial bundle with degraded-data warning |
| 5 | **Absolute Single Responsibility** | Diagnosis + alarm aggregation + multi-source/product/network RCA; no mutations; fixes delegated to product skills |

## Diagnosis Workflow

### Step 1: Symptom Detection
Classify the symptom into one of four categories:
- **Performance** — Slow response, high latency, CPU/memory spike
- **Availability** — Connection failed, timeout, health check failure
- **Capacity** — Quota exceeded, disk full, bandwidth limit reached
- **Security** — Access denied, unauthorized API calls, credential issues

### Step 2: Metric Analysis
**Baseline-first:** Run dynamic baseline anomaly detection ([`anomaly-detection.md`](references/anomaly-detection.md)) — fetch current, yesterday (−24h), and last-week (−7d) windows via `GetMonitorData`, compute anomaly score, then apply static thresholds only as fallback when baselines are unavailable.

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName CpuUsage \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" \
  --EndTime "{{user.time_end}}" \
  --Period 300
```

Use `DescribeBaseMetrics` for latest metric names. See [`cli-usage.md`](references/cli-usage.md#dynamic-baseline-metric-windows) for multi-window syntax.

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
| Static-threshold-only | Flagging CPU 85% during daily peak | Run baseline anomaly detection ([`anomaly-detection.md`](references/anomaly-detection.md)) before static thresholds |
| Alarm fatigue | Treating all alarms equally | Categorize, deduplicate, prioritize |
| Missing time context | Analyzing logs without time window | Always use {{user.time_range}} |
| Isolated alarm handling | Treating each TKE alarm in isolation (e.g., separate node NotReady, pod Crash, CLB 5xx) | Correlate by topology/time/resource; bundle as single incident (see [Alarm Handling](references/alarm-handling.md) §4) |
| Single-layer root cause | Attributing CLB 5xx only to CLB config, or OOMKilled only to app bug | Run Multi-Source RCA ([multi-source-rca.md](references/multi-source-rca.md)) across Pod/Node/CLB/CVM; add product rules ([product-rca-rules.md](references/product-rca-rules.md)) or Rule G ([network-rca.md](references/network-rca.md)) when datastore/network involved |
| Network blind spot | Node/CDB healthy but connection timeout | Run Rule G ([network-rca.md](references/network-rca.md)) before blaming application |
| Over-aggregation | Bundling unrelated alarms from different clusters | Use composite grouping keys per §1 TKE Grouping Keys; do not merge across `cluster_id` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial release — multi-metric correlation, root cause analysis, anomaly detection |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md`, `references/prompt-templates.md`. `max_iter=5` per AGENTS.md §8 |
| 1.2.0 | 2026-06-09 | TKE alarm noise reduction & event aggregation + Multi-Source RCA: canonical alarm event model, 6-step aggregation pipeline, output-only noise-reduction policies, 6 TKE incident classes with correlation rules, 4 TKE aggregation flows, Event Bundle output schema; **Multi-Source RCA evidence model**, 6-step RCA pipeline, 5 correlation rules with hypothesis scoring (CLB→Pod/Node, CrashLoopBackOff, PodPending, NodeNotReady, CVM saturation), RCA Bundle output schema with topology links/time alignment/verification steps; added `references/multi-source-rca.md`, updated `cli-usage.md`, `delegation-matrix.md`, `diagnostic-workflows.md`, `eval_queries.json`, `example-config.yaml` |
| 1.3.0 | 2026-06-09 | **Change correlation + Incident Timeline (Phase A):** `references/change-correlation.md` (Change Evidence Model, CloudAudit/CLS collection, Rule F post-change regression), `references/incident-timeline.md` (unified causal narrative schema); RCA Bundle fields `change_timeline`, `likely_change_trigger`, `incident_timeline_ref`; Workflow 7; eval cases for change/timeline triggers |
| 1.4.0 | 2026-06-09 | **Dynamic baseline anomaly detection (Phase B):** `references/anomaly-detection.md` (multi-window baselines, ratio/percentile/slope scoring, Anomaly Bundle); baseline-first Step 2; CLI multi-window `GetMonitorData`; `anomaly_findings` in RCA Bundle |
| 1.5.0 | 2026-06-09 | **Product + network RCA (Phase C):** `references/product-rca-rules.md` (Rules H/I/J CDB/Redis/ES), `references/network-rca.md` (Rule G VPC SG/route/NAT); evidence layers + `product_rca`/`network_rca` bundle fields; Workflow 9 |

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **optional** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **5** | per-skill override |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 rules (read-only skill) |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### Safety rules (rubric §4)

1. **Confidence disclosure** — surface HIGH/MEDIUM/LOW for each finding; no correlation-as-causation
2. **Read-only cross-skill** — no mutations; confirm read-only in trace
3. **Time-range correlation** — surface diagnosis window; warn non-overlapping windows
4. **Data recency** — surface last-updated time; warn stale data
5. **Recommendation boundary** — prefix "RECOMMENDATION (not execution)"; delegate to product skill

**Read-only skill.** No hard ABORT on Safety=0 (no destructive ops).

---

For detailed diagnosis patterns, see:
- [Diagnosis Framework](references/diagnosis-framework.md) — 3D optimization framework
- [Log Intelligence](references/log-intelligence.md) — Pattern recognition, anomaly detection
- [Diagnostic Workflows](references/diagnostic-workflows.md) — Decision trees per symptom
- [Alarm Handling](references/alarm-handling.md) — Storm handling, noise reduction, TKE event aggregation
- [Multi-Source RCA](references/multi-source-rca.md) — Pod/Node/CLB/CVM cross-layer root cause localization, hypothesis scoring, RCA Bundle
- [Change Correlation](references/change-correlation.md) — CloudAudit/CLS change evidence, Rule F post-change regression, lead-lag windows
- [Incident Timeline](references/incident-timeline.md) — Unified time-ordered narrative across alarms, metrics, logs, and changes
- [Anomaly Detection](references/anomaly-detection.md) — Dynamic baselines (yesterday/week), anomaly score, Anomaly Bundle
- [Product RCA Rules](references/product-rca-rules.md) — CDB / Redis / ES correlation rules H/I/J
- [Network RCA](references/network-rca.md) — Rule G VPC security group, route, NAT path diagnosis
- [CLI Usage](references/cli-usage.md) — CLI-first read-only collection and SDK fallback for TKE event bundles and multi-source RCA
- [Delegation Matrix](references/delegation-matrix.md) — Cross-skill diagnosis routing
