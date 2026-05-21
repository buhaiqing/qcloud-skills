---
name: qcloud-monitor-ops
description: >-
  Use when the user needs to configure, manage, or troubleshoot Tencent Cloud
  Monitoring (云监控, 腾讯云可观测平台) — alarm policies, metrics, dashboards,
  and observability. User mentions Monitor, 云监控, 腾讯云可观测平台, TCOP,
  alarm, alert, 告警, metric, 指标, dashboard, 监控, observability, or describes
  product-specific scenarios (e.g., setting up alerts, querying metrics,
  alarm policy configuration, dashboard creation, event monitoring, AIOps,
  proactive inspection) even without naming the product directly. Not for
  billing, CAM, or cloud product operations (use product-specific ops skills).
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-monitor),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-21"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/248"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli monitor help` - CLI exposes CreateAlarmPolicy,
    DescribeAlarmPolicies, ModifyAlarmPolicyStatus, DeleteAlarmPolicy,
    GetMonitorData, DescribeAlarmHistories, DescribeAllNamespaces, and 30+ more.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud Monitoring (云监控) Operations Skill

## Overview

Tencent Cloud Observability Platform (TCOP, 腾讯云可观测平台, 云监控) provides comprehensive monitoring across metrics, traces, logs, and events. Combines visualization and alerting capabilities for unified observability, improving operational efficiency. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

> **AIOps Integration:** This is a monitoring skill. It MUST follow [AIOps Best Practices](../qcloud-skill-generator/references/aiops-best-practices.md) for alarm storm handling, multi-metric correlation, proactive inspection, and diagnostic delegation.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` supports monitoring. You **MUST** ship **`references/cli-usage.md`** and document **both** CLI and SDK paths for each operation. CLI is **primary**; SDK handles complex parameter scenarios.

## Five Core Standards (Quality Gates)

Every generated skill MUST satisfy these five standards:

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use with triggers (Monitor, 云监控, alarm, metric) and delegation (product ops → respective skills) |
| 2 | **Structured I/O** | Placeholders (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) typed per operation |
| 3 | **Explicit Actionable Steps** | Pre-flight → Execute → Validate → Recover, numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy ≥ 12 codes; HALT vs retry per error |
| 5 | **Absolute Single Responsibility** | One product (Monitor), resources (AlarmPolicy, Metric); product ops delegated |

### Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Alarm policy redundancy, dashboard failover, metric retention policies | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions for alarm policies, sensitive metric masking, notification channel security | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Alarm policy optimization, dashboard resource efficiency, storage tiering | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch alarm operations, scheduled metric queries, automation integration | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Monitor" OR "云监控" OR "腾讯云可观测平台" OR "TCOP" OR "告警" OR "Alarm" OR "监控" OR "Metric" OR "指标"
- Task involves **Alarm Policy CRUD** (CreateAlarmPolicy, DescribeAlarmPolicies, ModifyAlarmPolicyStatus, DeleteAlarmPolicy)
- Task involves **Metric Query** (GetMonitorData, DescribeAlarmMetrics, DescribeAllNamespaces)
- Task involves **Alarm History** (DescribeAlarmHistories, DescribeAlarmNotifyHistories)
- Task involves **Notification Templates** (CreateAlarmNotice, DescribeAlarmNotices)
- Task keywords: alert, alarm, notification, threshold, dashboard, observability, proactive inspection, health check, performance monitoring, AIOps
- User asks to configure, manage, or troubleshoot monitoring **via API, SDK, CLI, or automation**

### SHOULD NOT Use This Skill When

- Task is **product-specific operations** → delegate to product ops skill:
  - CVM → `qcloud-cvm-ops`
  - CLB → `qcloud-clb-ops`
  - MySQL → `qcloud-mysql-ops`
  - VPC → `qcloud-vpc-ops`
- Task is purely billing → `qcloud-billing-ops` (when present)
- Task is CAM only → `qcloud-cam-ops` (when present)
- User wants **console-only** → state limitation; no undocumented HTTP steps

### Delegation Matrix

| Metric Namespace | Product Skill | Delegation Trigger |
|------------------|---------------|-------------------|
| `QCE/CVM` | `qcloud-cvm-ops` | CPU/Memory/Disk metrics → CVM operations |
| `QCE/LB_PUBLIC` | `qcloud-clb-ops` | CLB connection/traffic → CLB operations |
| `QCE/CDB` | `qcloud-mysql-ops` | MySQL slow query → MySQL operations |
| `QCE/REDIS` | `qcloud-redis-ops` | Redis metrics → Redis operations |
| `QCE/VPC` | `qcloud-vpc-ops` | VPC flow metrics → VPC operations |

**Rule:** Monitor skill handles alarm/metric configuration. Product ops skills handle resource operations based on alarm findings.

## Variable Convention

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From environment | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From environment | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From environment | Default `ap-guangzhou` if unset |
| `{{user.namespace}}` | Monitor namespace | Ask once; options: QCE/CVM, QCE/LB_PUBLIC, etc. |
| `{{user.metric_name}}` | Metric name | Ask once; suggest based on namespace |
| `{{user.policy_name}}` | Alarm policy name | Ask once; reuse |
| `{{user.policy_id}}` | Alarm policy ID | Ask once; reuse |
| `{{user.threshold}}` | Alarm threshold | Ask once; default per metric |
| `{{user.namespace}}` | Metric namespace | Ask once; list via DescribeAllNamespaces |
| `{{user.dimension_name}}` | Dimension key | Ask once; InstanceId, LoadBalancerId, etc. |
| `{{user.dimension_value}}` | Dimension value | Ask once; specific resource ID |
| `{{output.policy_id}}` | From CreateAlarmPolicy | Parse `$.Response.PolicyId` |
| `{{output.request_id}}` | From any response | Parse `$.Response.RequestId` |

## API and Response Conventions

- **API spec**: https://cloud.tencent.com/document/api/248
- **Errors**: `Response.Error.Code` / `Response.Error.Message` pattern
- **Timestamps**: ISO 8601 format

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|----------|------|-------------|
| CreateAlarmPolicy | `$.Response.PolicyId` | string | New policy ID |
| DescribeAlarmPolicies | `$.Response.Policies[0].PolicyId` | string | Policy ID |
| DescribeAlarmPolicies | `$.Response.Policies[0].PolicyName` | string | Policy name |
| GetMonitorData | `$.Response.MetricDataPoints[0].Values` | array | Metric values |
| DescribeAlarmHistories | `$.Response.Histories[0].AlarmId` | string | Alarm record ID |

## Quick Start

### What This Skill Does
Configure alarms, query metrics, manage dashboards, and troubleshoot monitoring on Tencent Cloud.

### Prerequisites
- [ ] `tccli` CLI installed
- [ ] Credentials configured
- [ ] Region set

### Verify Setup
```bash
tccli monitor DescribeAllNamespaces --Region ap-guangzhou
```

### Your First Command
```bash
# List alarm policies
tccli monitor DescribeAlarmPolicies --Region {{env.TENCENTCLOUD_REGION}}
```

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateAlarmPolicy | Create alarm policy | Medium | Low |
| DescribeAlarmPolicies | List alarm policies | Low | None |
| ModifyAlarmPolicyStatus | Enable/disable policy | Low | Medium |
| DeleteAlarmPolicy | Remove alarm policy | Low | **High** |
| GetMonitorData | Query metric data | Medium | None |
| DescribeAlarmHistories | View alarm history | Low | None |

---

## Execution Flows

### Operation: Create Alarm Policy

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| SDK | `pip show tencentcloud-sdk-python-monitor` | Installed | Document install |
| CLI | `tccli version` | OK | Document CLI |
| Credentials | Check env vars | Non-empty | HALT |
| Namespace valid | DescribeAllNamespaces | Namespace exists | Suggest valid |

#### Execution — CLI

```bash
tccli monitor CreateAlarmPolicy \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Module "monitor" \
  --PolicyName "{{user.policy_name}}" \
  --Namespace "{{user.namespace}}" \
  --ConditionTemplateId "" \
  --Conditions "[{\"CalcType\":\"Greater\",\"CalcValue\":\"{{user.threshold}}\",\"ContinueTime\":60,\"MetricName\":\"{{user.metric_name}}\"}]"
```

#### Post-execution Validation

1. Capture `{{output.policy_id}}` from `$.Response.PolicyId`
2. Verify policy via DescribeAlarmPolicy

#### Failure Recovery

| Error | Max retries | Backoff | Action |
|-------|-------------|---------|--------|
| `InvalidParameter` | 0 | — | Fix parameters |
| `FailedOperation.AlertPolicyCreateFailed` | 3 | exponential | Retry |
| `AuthFailure.AccessCAMFail` | 0 | — | HALT; check CAM |

### Operation: Describe Alarm Policies

```bash
tccli monitor DescribeAlarmPolicies \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Module "monitor" \
  --Namespace "{{user.namespace}}"
```

### Operation: Get Monitor Data

#### Execution

```bash
tccli monitor GetMonitorData \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Namespace "{{user.namespace}}" \
  --MetricName "{{user.metric_name}}" \
  --Dimensions "[{\"Name\":\"{{user.dimension_name}}\",\"Value\":\"{{user.dimension_value}}\"}]" \
  --StartTime "2026-05-20T00:00:00+08:00" \
  --EndTime "2026-05-21T00:00:00+08:00" \
  --Period 300
```

### Operation: Delete Alarm Policy

#### Safety Gate

- **MUST** confirm: delete policy `{{user.policy_id}}` (irreversible)
- **MUST NOT** proceed without explicit user assent

```bash
tccli monitor DeleteAlarmPolicy \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Module "monitor" \
  --PolicyIds "[\"{{user.policy_id}}\"]"
```

---

## AIOps Integration Patterns

### Alarm Storm Handling

When alarm storm detected (>50 alarms in 5 minutes):

1. **Aggregation**: Group alarms by root cause pattern
2. **Delegation**: Forward to product ops skill for diagnosis
3. **Suppression**: Temporary policy adjustment (requires CAM permission)

### Multi-Metric Correlation

For complex diagnostics:

| Namespace | Correlation Matrix |
|-----------|-------------------|
| `QCE/CVM` | CPUUsage → MemUsage → DiskUsage |
| `QCE/LB_PUBLIC` | Connection → Traffic → HealthStatus |
| `QCE/CDB` | CpuUseRate → MemoryUseRate → SlowQuery |

### Proactive Inspection

Five-step flow per [Proactive Inspection Template](../qcloud-skill-generator/templates/proactive-inspection.md):

1. Discovery → 2. Collection → 3. Detection → 4. Diagnosis → 5. Report

---

## Error Code Reference

### Category Legend

| Category | Retry Policy |
|----------|-------------|
| **HALT** | Non-retryable — stop and escalate |
| **RETRY** | Retryable (3x with exponential backoff) |
| **FIX** | Input/configuration error — fix and retry |

### Auth & Permission Errors

| Code | Meaning | Policy | Action |
|------|---------|--------|--------|
| `AuthFailure.AccessCAMFail` | CAM access failed | HALT | Verify CAM roles & policies |
| `UnauthorizedOperation.CamNoAuth` | No CAM permission | HALT | Check principal — grant `QcloudMonitorFullAccess` or custom policy |
| `AuthFailure.InvalidAuthorization` | Invalid Authorization header | FIX | Re-sign request per TC3-HMAC-SHA256 |
| `AuthFailure.SecretIdNotFound` | SecretId does not exist | HALT | Verify credentials in `TENCENTCLOUD_SECRET_ID` |

### Alarm Policy Lifecycle

| Code | Meaning | Policy | Action |
|------|---------|--------|--------|
| `FailedOperation.AlertPolicyCreateFailed` | Create alarm policy failed | RETRY | Retry — if persists, check policy name uniqueness |
| `FailedOperation.AlertPolicyDeleteFailed` | Delete alarm policy failed | RETRY | Retry — verify policy still exists |
| `FailedOperation.AlertPolicyModifyFailed` | Modify alarm policy failed | RETRY | Retry — log diff of attempted changes |
| `FailedOperation.AlertPolicyDescribeFailed` | Describe alarm policy failed | RETRY | Retry — check policy ID validity |
| `FailedOperation.AlertFilterRuleDeleteFailed` | Delete filter rule failed | RETRY | Retry — verify rule ID |
| `FailedOperation.AlertTriggerRuleDeleteFailed` | Delete trigger rule failed | RETRY | Retry — verify trigger ID |
| `InvalidParameterValue.DashboardNameExists` | Dashboard name duplicate | FIX | Use unique dashboard name |

### Data & Query Errors

| Code | Meaning | Policy | Action |
|------|---------|--------|--------|
| `FailedOperation.DataQueryFailed` | Data query failed | RETRY | Retry — may be transient backend load |
| `FailedOperation.DataColumnNotFound` | Data column not found | FIX | Verify metric/column name in namespace |
| `FailedOperation.DataTableNotFound` | Data table not found | FIX | Verify namespace is correct |
| `FailedOperation.DimQueryRequestFailed` | Dimension query failed | RETRY | Retry — check dimension parameters |
| `FailedOperation.DruidQueryFailed` | Druid query analysis failed | RETRY | Retry — timeout or backend shuffle |
| `FailedOperation.DivisionByZero` | Division by zero in query | FIX | Review metric expression logic |
| `LimitExceeded.LimitedAccess` | Request limited | RETRY | Reduce query concurrency or instance count |
| `LimitExceeded.MetricQuotaExceeded` | Metric quota exceeded | HALT | Remove unregistered metrics from request |

### Database & Backend Internal Errors

| Code | Meaning | Policy | Action |
|------|---------|--------|--------|
| `FailedOperation.DbQueryFailed` | DB query failed | RETRY | Transient — retry |
| `FailedOperation.DbRecordCreateFailed` | Create DB record failed | RETRY | Retry — check payload |
| `FailedOperation.DbRecordDeleteFailed` | Delete DB record failed | RETRY | Retry — verify record exists |
| `FailedOperation.DbRecordUpdateFailed` | Update DB record failed | RETRY | Retry — log update payload |
| `FailedOperation.DbTransactionBeginFailed` | DB transaction start failed | RETRY | Transient — retry |
| `FailedOperation.DbTransactionCommitFailed` | DB transaction commit failed | RETRY | Transient — retry |
| `FailedOperation.DoHTTPTransferFailed` | Backend HTTP timeout | RETRY | Transient — retry; if persists, check backend |
| `FailedOperation.DoTRPCTransferFailed` | Network RPC error | RETRY | Transient — retry |
| `InternalError.DependsApi` | Dependent API error | HALT | Escalate — dependent service failure |
| `InternalError.DependsDb` | Dependent DB error | HALT | Escalate — database incident |
| `InternalError.DependsMq` | Dependent MQ error | HALT | Escalate — message queue incident |
| `InternalError.ExeTimeout` | Execution timeout | RETRY | Retry — split into smaller batches |
| `InternalError.System` | Internal system error | HALT | Escalate — platform bug |

### STS, Tag & TKE Integration

| Code | Meaning | Policy | Action |
|------|---------|--------|--------|
| `FailedOperation.AccessSTSFail` | STS access failed | HALT | Check temporary credential validity |
| `FailedOperation.AccessTagFail` | Tag service failed | HALT | Check Tag service status |
| `FailedOperation.AccessTKEFail` | TKE cluster access failed | HALT | Verify TKE cluster connectivity |
| `FailedOperation.TKEEndpointStatusError` | TKE endpoint unreachable | HALT | Check TKE cluster APIServer |
| `FailedOperation.TKEResourceConflict` | TKE resource conflict | RETRY | Retry — concurrent update detected |
| `FailedOperation.ClusterNotFound` | Cluster not found | HALT | Verify cluster ID |

### Agent & Instance Errors

| Code | Meaning | Policy | Action |
|------|---------|--------|--------|
| `FailedOperation.AgentNotAllowed` | Agent state disallows operation | FIX | Check agent status via `tccli monitor DescribeMonitorAgents` |
| `FailedOperation.AgentVersionNotSupported` | Agent version too old | FIX | Upgrade agent to latest version |
| `FailedOperation.AgentsNotInUninstallStage` | Agent still running on instance | FIX | Stop agent before uninstall |
| `FailedOperation.InstanceNotFound` | Instance not found | HALT | Verify instance ID |
| `FailedOperation.InstanceNotRunning` | Instance not running | HALT | Check instance power state |
| `FailedOperation.ResourceConflict` | Resource conflict | RETRY | Retry — concurrent modification |
| `FailedOperation.ResourceExist` | Resource already exists | FIX | Use a different name |
| `FailedOperation.ResourceNotFound` | Resource not found | HALT | Verify resource ID/ARN |
| `FailedOperation.ResourceOperating` | Resource being operated | RETRY | Retry — operation in progress |
| `FailedOperation.CreateInstanceLimited` | Instance creation limited | HALT | Check account quota or billing |
| `FailedOperation.DuplicateName` | Duplicate name | FIX | Choose unique name |

### Service Status & Billing

| Code | Meaning | Policy | Action |
|------|---------|--------|--------|
| `FailedOperation.ErrNotOpen` | Service not enabled | HALT | Enable Monitor service |
| `FailedOperation.ErrOwed` | Account in arrears | HALT | Top up account |
| `FailedOperation.ServiceNotEnabled` | Service not enabled | HALT | Activate service |
| `FailedOperation.RegionUnavailable` | Region unavailable | HALT | Select another region |
| `FailedOperation.ZoneUnavailable` | Zone unavailable | HALT | Select another availability zone |
| `ResourceInUse.ResourceExistAlready` | Resource already in use | FIX | Check for existing resource |
| `ResourceNotFound.NotExistTask` | Task does not exist | FIX | Verify task ID |
| `ResourcesSoldOut` | Resources sold out | HALT | Choose another specification or region |
| `OperationDenied` | Operation denied | HALT | Check operation permissions |

## Reference Directory

### Core Documentation
- [Core Concepts](references/core-concepts.md) — Monitoring architecture and namespaces
- [API & SDK Usage](references/api-sdk-usage.md) — Alarm policy APIs and Python SDK
- [CLI Usage](references/cli-usage.md) — `tccli monitor` commands
- [Troubleshooting](references/troubleshooting.md) — Alarm issues and solutions
- [Integration](references/integration.md) — Cross-skill delegation matrix

### Framework Integration
- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar framework for monitoring
- [AIOps Best Practices](references/aiops-best-practices.md) — Alarm storm handling, correlation, proactive inspection
- [FinOps Cost Optimization](references/finops-cost-optimization.md) — Notification costs, budget controls
- [SecOps Security Operations](references/secops-security-operations.md) — CAM policies, webhook security

### Assets
- [Example Configuration](assets/example-config.yaml) — Alarm policy templates with AIOps integration
- [Evaluation Queries](assets/eval_queries.json) — Trigger accuracy test queries