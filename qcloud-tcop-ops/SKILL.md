---
name: qcloud-tcop-ops
description: >-
  Tencent Cloud Optimization Platform (TCOP) — cost optimization, resource optimization,
  and architecture optimization analysis. Use when the user asks to analyze cloud costs,
  identify idle or under-utilized resources, get right-sizing recommendations, evaluate
  reserved instance or savings plan coverage, review architecture against Well-Architected
  best practices, or generate optimization reports and action plans. Covers cost analysis
  (trends, anomalies, waste detection), resource optimization (right-sizing, idle detection,
  lifecycle management), and architecture review (reliability, security, cost, efficiency).
  Triggers on keywords: TCOP, 云优化平台, 优化平台, cost optimization, 成本优化,
  资源优化, 架构优化, 闲置资源, 降本增效, 规格推荐, savings plan, 预留实例,
  Well-Architected review, 卓越架构评估.
license: MIT
compatibility: >-
  Python 3.8+ runtime (for SDK with tencentcloud-sdk-python >= 3.1.0),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-07-08"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "TCOP (Tencent Cloud Optimization Platform) — API version <!-- TBD: verify API version when publicly documented -->"
  cli_applicability: "sdk-only"
  cli_support_evidence: >-
    tccli does not ship a `tcop` subcommand as of 2026-07-08.
    Verified via `tccli tcop help` returning "Invalid choice".
    All operations require tencentcloud-sdk-python (API calls via common pattern).
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  related_skills:
    - qcloud-finops-ops   # 反向：TCOP 成本分析需要 FinOps 的精细化账单数据
    - qcloud-monitor-ops  # 反向：TCOP 资源优化需要 Monitor 的指标数据
    - qcloud-cvm-ops      # 委托：右 sizing 执行
    - qcloud-cdb-ops      # 委托：闲置 CDB 处理
    - qcloud-clb-ops      # 委托：CLB 相关优化执行
    - qcloud-well-architected-review  # 委托：卓越架构评估
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud Optimization Platform (TCOP) Operations Skill

## Overview

Tencent Cloud Optimization Platform (TCOP / 腾讯云优化平台) is a unified optimization
service that helps users reduce cloud costs, improve resource utilization, and align
architecture with best practices. TCOP provides analysis and recommendations across
three dimensions:

| Dimension | Focus | Typical Output |
|-----------|-------|----------------|
| **Cost** | Spending analysis, anomaly detection, waste identification, reserved instance / savings plan recommendations | Cost trend report, savings opportunity list, RI coverage analysis |
| **Resource** | Idle/low-utilization detection, right-sizing, lifecycle optimization | Idle resource list, right-sizing recommendations, release suggestions |
| **Architecture** | Well-Architected Framework assessment (reliability, security, cost, efficiency) | Assessment scorecard, improvement action plan |

This skill is an **operational runbook** for agents: explicit scope, credential rules,
pre-flight checks, **SDK-first execution** (tccli does not support this product),
response validation, and failure recovery. **Do not use the web console as the primary
agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

**Product page**: https://cloud.tencent.com/product/tcop
**Console**: https://console.cloud.tencent.com/tcop

### CLI applicability (repository policy)

- **`cli_applicability: sdk-only`:** Official `tccli` does **not** expose this product.
  **No** `references/cli-usage.md` is required. SDK/API remains mandatory for all
  operations. Verified via `tccli tcop help` returning "Invalid choice".

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT with precise TCOP keywords; delegate CVM/CDB/CLB right-sizing execution to product skills |
| 2 | **Structured I/O** | `{{env.*}}` for credentials (never ask user), `{{user.*}}` for analysis params, `{{output.*}}` from API responses |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight -> Execute (SDK) -> Validate -> Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | 10+ product-specific error codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | TCOP optimization analysis only; cross-product delegation to `qcloud-cvm-ops`, `qcloud-finops-ops`, etc. |

### Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Architecture assessment identifies reliability gaps, SLA risks, single points of failure | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Security posture review, compliance gap analysis, best practice recommendations | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Core capability: cost analysis, waste detection, RI/Savings Plan optimization | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Resource utilization analysis, right-sizing, performance-to-cost ratio optimization | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "TCOP", "云优化平台", "优化平台", "Tencent Cloud Optimization Platform"
- Task involves cost analysis, optimization recommendations, resource right-sizing, idle detection
- Task keywords: 成本优化, 资源优化, 架构优化, 闲置资源, 降本增效, 规格推荐, savings plan, 预留实例, Well-Architected review, 卓越架构评估
- User asks for optimization reports, cost trend analysis, or waste identification
- User wants to review architecture against best practices

### SHOULD NOT Use This Skill When

- Task is purely billing query / FinOps data access -> delegate to: `qcloud-finops-ops`
- Task is resource CRUD (create/delete/modify CVM/CDB/CLB etc.) -> delegate to: the relevant product skill
- Task is CAM / permission model -> delegate to: `qcloud-cam-ops`
- Task is real-time monitoring metrics -> delegate to: `qcloud-monitor-ops`
- User insists on **console-only** flows with no API -> state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- If TCOP identifies a cost optimization opportunity for CVM, delegate right-sizing execution to `qcloud-cvm-ops`.
- If TCOP identifies a CDB idle resource, delegate to `qcloud-cdb-ops` for lifecycle management.
- Multi-product optimization: analyze via TCOP, then delegate per resource type.
- Proactive inspection (read-only) -> invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) -> invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **TCOP (Optimization Platform)**
> return `{{output.product_assessment}}`.
> **sdk-only:** No `tccli` -- use `Describe*` via `tencentcloud-sdk-python` only.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `account-wide` |

**Allowed:** SDK `Describe*` / list APIs only -- no mutation operations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract**
-> [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md)
(`product: tcop`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Default `ap-guangzhou` if skill allows |
| `{{user.analysis_period}}` | Analysis time range (e.g. last-30d, last-90d) | Ask once; default last-30d |
| `{{user.product_filter}}` | Filter to specific product (e.g. cvm, cdb, all) | Ask once; default all products |
| `{{user.optimization_goal}}` | Optimization objective (cost/resource/architecture) | Ask once; infer from context |
| `{{user.report_format}}` | Output format (summary/detail/json) | Ask once; default summary |
| `{{output.report_summary}}` | From last API JSON response | Parse per API response path |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected
> interactively when missing.

> **Security Warning (Credential Masking -- MANDATORY):** **NEVER** log, print, or expose
> `TENCENTCLOUD_SECRET_KEY`, `SecretKey`, or any credential field value.

| Execution Path | Safe Pattern | Unsafe Pattern |
|----------------|-------------|----------------|
| Console output | `TENCENTCLOUD_SECRET_KEY=<masked>` | `TENCENTCLOUD_SECRET_KEY=abc123...` |
| Error messages | `Error: API call failed (credential omitted)` | `Error: InvalidSecretKey ... actual key...` |
| Log files | `[INFO] Credentials configured: Key=***` | `[INFO] Secret Key: abc123...` |
| Verification | `test -n "$TENCENTCLOUD_SECRET_KEY" && echo "Key is set"` | `echo $TENCENTCLOUD_SECRET_KEY` |
| Python SDK | `SecretKey=os.environ.get("...")` (env read safe) | `print(f"Config: {config}")` |

> **If any execution flow violates this rule, the skill SHALL be blocked from merge as a security incident.**

## API and Response Conventions

- **Service**: `tcop` | **Endpoint**: `tcop.tencentcloudapi.com` (expected; <!-- TBD: confirm when API docs published -->)
- **Errors**: Map SDK/HTTP errors to `code` / `message` fields per standard Tencent Cloud pattern.
- **Timestamps**: ISO 8601 format when API returns strings (e.g. `2026-04-28T00:00:00+08:00`).
- **Idempotency**: Analysis operations are idempotent; mutation operations are not.

### Response Field Table

| Operation | JSON Path (expected) | Type | Description |
|-----------|---------------------|------|-------------|
| DescribeOptimizationReport | `$.Response.ReportId` | string | Report ID |
| DescribeOptimizationReport | `$.Response.TotalSavings` | string | Estimated monthly savings |
| DescribeCostAnalysis | `$.Response.TotalCost` | string | Total cost in period |
| DescribeRightSizingRecommendations | `$.Response.RecommendationSet[]` | array | Right-sizing suggestions |
| DescribeIdleResources | `$.Response.IdleResourceSet[]` | array | Idle/unused resources |
| DescribeWasteAnalysis | `$.Response.WasteItemSet[]` | array | Waste items with amounts |
| DescribeSavingsPlanCoverage | `$.Response.CoverageRate` | string | Savings plan coverage rate |

> **Note:** TCOP API endpoints and response shapes are subject to change as the product evolves.
> Verify against official API documentation at time of use.

## Quick Start

### What This Skill Does
Analyze cloud costs, detect idle/under-utilized resources, get right-sizing recommendations,
evaluate savings plan coverage, and review architecture against Well-Architected best practices
on Tencent Cloud using the Python SDK (sdk-only product — no tccli support).

### Prerequisites
- [ ] Python 3.8+ runtime for SDK
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION` (default: ap-guangzhou)

### Verify Setup
```bash
python3 -c "import tencentcloud.common; print('TencentCloud SDK: OK')"
test -n "$TENCENTCLOUD_SECRET_ID" && echo "SecretId: set"
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "SecretKey: set"
```

### Your First Command
-> SDK code examples in [references/sdk-code-examples.md](references/sdk-code-examples.md)

```bash
# Quick cost analysis
python3 -c "
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

cred = credential.Credential(
    os.environ.get('TENCENTCLOUD_SECRET_ID'),
    os.environ.get('TENCENTCLOUD_SECRET_KEY')
)
# TCOP API client (adjust _v20250430 if version differs)
from tencentcloud.tcop import tcop_client, models
client = tcop_client.TcopClient(cred, os.environ.get('TENCENTCLOUD_REGION', 'ap-guangzhou'))
req = models.DescribeCostAnalysisRequest()
req.Period = 'last-30d'
resp = client.DescribeCostAnalysis(req)
print(json.dumps(resp.to_json_string(), indent=2))
"
```
### Next Steps
- [Core Concepts](references/core-concepts.md) — TCOP architecture and optimization dimensions
- [Common Operations](#execution-flows) — Full execution flows for each analysis type
- [Troubleshooting](references/troubleshooting.md) — Error remediation and common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Cost analysis | Analyze spending by product/project/region | Low | None |
| Waste detection | Identify idle/unused resources generating cost | Low | None |
| Right-sizing recommendations | Suggest instance spec changes for better utilization | Low | None |
| Savings plan coverage | Analyze RI/savings plan coverage and recommend | Low | None |
| Resource optimization | Identify idle resources with release suggestions | Low | None |
| Architecture assessment | Well-Architected framework review | Medium | None |
| Optimization report | Generate consolidated optimization report | Medium | None |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight -> Execute (SDK) -> Validate -> Recover**.
Do not skip phases.

Since `cli_applicability: sdk-only`, only SDK paths are documented.
See [references/sdk-code-examples.md](references/sdk-code-examples.md) for complete code examples.

### Operation: DescribeCostAnalysis

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python` | Version >= 3.1.0 | `pip install tencentcloud-sdk-python` |
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` | Non-empty | HALT; user configures env |
| Region | `TENCENTCLOUD_REGION` set or use default | Valid region | Suggest ap-guangzhou |

#### Execution -- Python SDK
-> SDK code examples in [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Verify `resp.TotalCost` is a numeric string.
2. Parse `resp.ProductCostSet[]` for per-product breakdown.
3. On success, present summary with total cost, top spenders, and period-over-period change.
4. On terminal failure, go to **Failure Recovery**.

#### Present to User

| Field | Path (expected) | Notes |
|-------|----------------|-------|
| Total cost | `$.Response.TotalCost` | Formatted with currency unit |
| Period | `$.Response.StartDate` / `$.Response.EndDate` | ISO 8601 |
| Top products | `$.Response.ProductCostSet[].ProductName` | Sorted by cost desc |
| MoM change | `$.Response.MonthOverMonth` | Percentage change |
| Anomaly count | `$.Response.AnomalyCount` | Number of anomalies detected |

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|---------------|-------------|---------|--------------|-------------|
| `InvalidParameter` | 0 | -- | Fix period/region parameter | `[ERROR] InvalidParameter: Check analysis period and region.` |
| `InvalidSecretKey` | 0 | -- | HALT | `[ERROR] Invalid credentials. Check TENCENTCLOUD_SECRET_KEY.` |
| `RequestLimitExceeded` | 3 | exponential | Back off; retry | `Rate limit. Retrying in {backoff}s...` |
| `InternalError` | 3 | 2s/4s/8s | Retry; escalate with RequestId | `[ERROR] InternalError: Server error. RequestId: {RequestId}` |

---

### Operation: DescribeRightSizingRecommendations

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Product filter set | `{{user.product_filter}}` | Specific product or "all" | Default to all products |

#### Execution -- Python SDK
-> SDK code examples in [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Verify `resp.RecommendationSet[]` is an array.
2. Each item should have `CurrentSpec`, `RecommendedSpec`, `EstimatedSavings`.
3. Present recommendations grouped by product.

#### Present to User

| Field | Path (expected) | Notes |
|-------|----------------|-------|
| Resource ID | `$.Response.RecommendationSet[].ResourceId` | ins-xxx / cdb-xxx format |
| Product | `$.Response.RecommendationSet[].Product` | cvm / cdb / clb etc. |
| Current spec | `$.Response.RecommendationSet[].CurrentSpec` | e.g. S5.LARGE8 |
| Recommended spec | `$.Response.RecommendationSet[].RecommendedSpec` | e.g. S5.MEDIUM4 |
| Monthly savings | `$.Response.RecommendationSet[].EstimatedMonthlySavings` | Estimated cost reduction |
| Confidence | `$.Response.RecommendationSet[].Confidence` | high/medium/low |
| Reason | `$.Response.RecommendationSet[].Reason` | e.g. "CPU avg utilization < 20%" |

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT; no resources found for given filter |
| `RequestLimitExceeded` | 3 | Exponential backoff |

---

### Operation: DescribeIdleResources

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Analysis period | `{{user.analysis_period}}` | last-30d (default) | Use default |

#### Execution -- Python SDK
-> SDK code examples in [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Verify `resp.IdleResourceSet[]` is a non-empty array.
2. Each item should have utilization metrics.
3. Estimate total waste and present grouped by product.

#### Present to User

| Field | Path (expected) | Notes |
|-------|----------------|-------|
| Resource ID | `$.Response.IdleResourceSet[].ResourceId` | Resource identifier |
| Type | `$.Response.IdleResourceSet[].ResourceType` | CVM / CDB / CLB / CBS / etc. |
| Idle metric | `$.Response.IdleResourceSet[].IdleMetric` | e.g. "CPU < 5% for 30 days" |
| Days idle | `$.Response.IdleResourceSet[].IdleDays` | Number of days considered idle |
| Monthly cost | `$.Response.IdleResourceSet[].MonthlyCost` | Current monthly spend |
| Recommended action | `$.Response.IdleResourceSet[].RecommendedAction` | Release / Stop / Downsize |
| Action summary | `$.Response.TotalWasteMonthly` | Total monthly waste estimate |

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `InvalidParameter` | 0 | Fix period parameter |
| `MissingParameter` | 0 | Ensure product filter is set |
| `RequestLimitExceeded` | 3 | Exponential backoff |

---

### Operation: DescribeSavingsPlanCoverage

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Coverage scope | `{{user.product_filter}}` | all or specific | Default all |

#### Execution -- Python SDK
-> SDK code examples in [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Present to User

| Field | Path (expected) | Notes |
|-------|----------------|-------|
| Overall coverage | `$.Response.CoverageRate` | Percentage (e.g. "65%") |
| On-demand spend | `$.Response.OnDemandSpend` | Monthly on-demand cost |
| Committed spend | `$.Response.CommittedSpend` | Monthly committed cost |
| Uncovered resources | `$.Response.UncoveredResourceSet[]` | Resources without coverage |
| Recommendations | `$.Response.RecommendationSet[]` | Purchase suggestions |
| Recommended savings | `$.Response.EstimatedMonthlySavings` | If purchasing additional plans |

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | No billing data found |
| `RequestLimitExceeded` | 3 | Exponential backoff |

---

### Operation: DescribeWasteAnalysis

#### Execution -- Python SDK
-> SDK code examples in [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Present to User

| Field | Path (expected) | Notes |
|-------|----------------|-------|
| Waste category | `$.Response.WasteItemSet[].Category` | idle / oversized / unattached / etc. |
| Waste amount | `$.Response.WasteItemSet[].MonthlyWaste` | Monthly waste estimate |
| Resource count | `$.Response.WasteItemSet[].ResourceCount` | Affected resources |
| Top action items | `$.Response.WasteItemSet[].ActionItems` | Priority actions |

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `InvalidParameter` | 0 | Check period parameter |
| `RequestLimitExceeded` | 3 | Exponential backoff |

---

### Operation: DescribeArchitectureAssessment

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Assessment scope | `{{user.product_filter}}` | all or specific | Default all |

#### Execution -- Python SDK
-> SDK code examples in [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Present to User

| Field | Path (expected) | Notes |
|-------|----------------|-------|
| Overall score | `$.Response.TotalScore` | 0-100 |
| Reliability score | `$.Response.PillarScores.Reliability` | 0-100 |
| Security score | `$.Response.PillarScores.Security` | 0-100 |
| Cost score | `$.Response.PillarScores.Cost` | 0-100 |
| Efficiency score | `$.Response.PillarScores.Efficiency` | 0-100 |
| Top risks | `$.Response.RiskSet[]` | High-priority risks |
| Improvement plan | `$.Response.ImprovementPlan[]` | Action items per pillar |

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | No resources to assess |
| `RequestLimitExceeded` | 3 | Exponential backoff |

---

### Operation: GenerateOptimizationReport

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Report period | `{{user.analysis_period}}` | last-30d (default) | Use default |
| Report type | `{{user.report_format}}` | summary / detail / json | Default summary |

#### Execution -- Python SDK
-> SDK code examples in [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `resp.ReportId` for retrieval.
2. Poll `DescribeOptimizationReport` until status = `COMPLETED` (interval: 5s, max: 120s).
3. Present report summary including total savings opportunities and per-category breakdown.

#### Present to User

| Field | Path (expected) | Notes |
|-------|----------------|-------|
| Report ID | `$.Response.ReportId` | For reference |
| Report status | `$.Response.Status` | RUNNING / COMPLETED / FAILED |
| Total savings | `$.Response.TotalPotentialSavings` | Estimated monthly savings |
| Cost savings | `$.Response.CostSavings` | Cost optimization items |
| Resource savings | `$.Response.ResourceSavings` | Resource optimization items |
| Architecture risks | `$.Response.ArchitectureRisks` | Architecture issues found |
| Report URL | `$.Response.ReportUrl` | Link to console report |

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `InvalidParameter` | 0 | Fix report parameters |
| `RequestLimitExceeded` | 3 | Exponential backoff |
| `InternalError` | 3 | Retry; escalate with RequestId |

---

## Prerequisites

1. **Install Python SDK** (required -- tccli does not support this product):

   ```bash
   pip install tencentcloud-sdk-python
   python3 --version  # Must be >= 3.8
   ```

2. **Configure Credentials** -- Environment variables (recommended for Agent execution):

   ```bash
   export TENCENTCLOUD_SECRET_ID="{{env.TENCENTCLOUD_SECRET_ID}}"
   export TENCENTCLOUD_SECRET_KEY="{{env.TENCENTCLOUD_SECRET_KEY}}"
   export TENCENTCLOUD_REGION="{{env.TENCENTCLOUD_REGION}}"
   ```

3. **Verify Configuration**:

   ```bash
   python3 -c "
   import tencentcloud.common
   print('TencentCloud SDK: OK')
   "
   test -n "$TENCENTCLOUD_SECRET_ID" && echo 'SecretId: set'  # safe: no value echo
   ```

> **Security:** Never commit `.env` to version control. All credentials use `{{env.*}}`
> placeholders -- never real values.

## Reference Directory

- [Core Concepts](references/core-concepts.md) -- TCOP architecture and optimization dimensions
- [API & SDK Usage](references/api-sdk-usage.md) -- Full SDK examples for TCOP operations
- [SDK Code Examples](references/sdk-code-examples.md) -- Runnable Python scripts for each flow
- [Troubleshooting Guide](references/troubleshooting.md) -- Error remediation playbook
- [Proactive Inspection](references/proactive-inspection.md) -- Inspection integration for `qcloud-proactive-inspection`
- [GCL Rubric](references/rubric.md) -- Quality Gate scoring dimensions
- [GCL Prompt Templates](references/prompt-templates.md) -- Generator/Critic/Orchestrator templates
- [Eval Queries](assets/eval_queries.json) -- Test prompts for skill validation
- [Example Configuration](assets/example-config.yaml) -- Analysis parameter templates
- [Well-Architected Assessment](references/well-architected-assessment.md) -- 4-pillar audit checklist

## Operational Best Practices

- **Least privilege:** CAM policies scoped to `tcop:*` actions only.
- **Periodic analysis:** Run cost analysis at least monthly to catch anomalies early.
- **Action tracking:** Log optimization recommendations and track closure rate.
- **Right-sizing workflow:** Always validate with 30-day utilization data before resizing.
- **Cross-skill integration:** Use `qcloud-cvm-ops` / `qcloud-cdb-ops` / `qcloud-clb-ops` to execute right-sizing actions.

---

## Error Code Reference

### Category Legend

| Category | Retry Policy |
|----------|-------------|
| **HALT** | Non-retryable — stop and escalate |
| **RETRY** | Retryable (3x with exponential backoff) |
| **FIX** | Input/configuration error — fix and retry |

### Auth & Credential Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidSecretKey` | Credential secret key invalid | HALT — regenerate in CAM console |
| `InvalidSecretId` | Credential ID invalid or deleted | HALT — check CAM for active keys |
| `OperationDenied` | Account not authorized for TCOP | HALT — enable TCOP in console |

### Parameter & Resource Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter` | Parameter validation failed | FIX — check parameter format per spec |
| `InvalidParameterValue` | Parameter value out of range | FIX — adjust value (e.g., period 7-365 days) |
| `MissingParameter` | Required parameter missing | FIX — check request object fields |
| `ResourceNotFound` | Target resource not found | FIX — verify resource ID or product filter |
| `UnsupportedOperation` | Operation not supported in region/account | FIX — switch region or check eligibility |

### Rate Limit & Server Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `RequestLimitExceeded` | API rate limit exceeded | RETRY — exponential backoff |
| `InternalError` | Server-side error | RETRY — retry 2s/4s/8s; escalate with RequestId if persists |

---

## Safety Gates

TCOP is primarily a **read-only analysis** product. No destructive operations exist
in this skill. However, when generating optimization recommendations that involve
resource modification:

1. Always present recommendations as **proposed actions** only -- never execute directly.
2. If the user wants to act on a recommendation, delegate to the appropriate product skill
   (e.g., `qcloud-cvm-ops` for instance right-sizing).
3. Before delegating, ensure the user has reviewed and confirmed the recommendation.

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

> **Read-only advisory skill.** No destructive operations exist. GCL
> applicability is **optional** per AGENTS.md §8. Quality Gate is for
> SDK correctness and recommendation accuracy.

| Property | Value | Source |
|---|---|---|---|
| GCL applicability | **optional** | Read-only advisory: no destructive operations |
| `max_iterations` | **1** | Lightweight runbook validation |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 TCOP-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | Per AGENTS.md |

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "req-abc123",
    "TotalCost": "12345.67",
    "Period": {
      "StartDate": "2026-06-08",
      "EndDate": "2026-07-08"
    },
    "ProductCostSet": [
      {
        "ProductName": "CVM",
        "Cost": "5000.00",
        "Percentage": "40.5"
      },
      {
        "ProductName": "CDB",
        "Cost": "3000.00",
        "Percentage": "24.3"
      }
    ],
    "MonthOverMonth": "+5.2%",
    "AnomalyCount": 3
  }
}
```

Error responses:

```json
{
  "Response": {
    "RequestId": "req-abc123",
    "Error": {
      "Code": "InvalidParameter",
      "Message": "Parameter Period format invalid. Use 'last-Nd' or ISO date range."
    }
  }
}
```

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-07-08 | Self-review fixes: added related_skills, restructured error codes with Category Legend, created missing references (rubric.md, prompt-templates.md, proactive-inspection.md), added example-config.yaml, fixed import time in sdk-code-examples, replaced TBD placeholders with HTML comments |
| 1.0.0 | 2026-07-08 | Initial skill generated from qcloud-skill-generator template |
