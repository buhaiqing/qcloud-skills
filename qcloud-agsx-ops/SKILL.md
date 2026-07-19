---
name: qcloud-agsx-ops
description: >-
  Use when the user asks to operate Tencent Cloud Agent Sandbox (AGSX / Agent Runtime), including creating, describing, updating, or deleting sandbox tools and sandbox instances; managing API keys; integrating with e2b-code-interpreter SDK; troubleshooting sandbox startup failures, quota errors, or connection issues; or performing well-architected assessments on agent sandbox deployments. Covers browser sandboxes, code sandboxes, and custom sandboxes. Activates on keywords: AGSX, Agent Runtime, agent sandbox, 代码沙箱, 浏览器沙箱, 沙箱实例, sandbox tool, sandbox instance, e2b sandbox, tencentags. Triggers on API names: CreateSandboxTool, DescribeSandboxToolList, UpdateSandboxTool, DeleteSandboxTool, StartSandboxInstance, DescribeSandboxInstanceList, StopSandboxInstance, CreateAPIKey, DeleteAPIKey, CreatePreCacheImageTask.
license: Apache-2.0
compatibility: >-
  Python 3.8+ runtime (for SDK with tencentcloud-sdk-python >= 3.0.1300),
  valid API credentials, network access to ags.tencentcloudapi.com.
metadata:
  author: qcloud
  version: "1.5.0"
  last_updated: "2026-07-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "2025-09-20"
  cli_applicability: "sdk-only"
  cli_support_evidence: >-
    tccli does not ship an `ags` subcommand as of 2026-05-28.
    Verified via `tccli ags help` returning "Invalid product".
    All operations require tencentcloud-sdk-python (ags module).
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
    - E2B_API_KEY
    - E2B_DOMAIN
  related_skills:
    - qcloud-vpc-ops          # 委托：VPC 网络配置
    - qcloud-cam-ops          # 委托：权限策略配置
    - qcloud-cls-ops          # 委托：日志分析查询
    - qcloud-monitor-ops      # 委托：监控告警配置
    - qcloud-tke-ops          # 委托：TKE/CVM/SCF 计算资源
    - qcloud-finops-ops       # 反向：成本优化分析
    - qcloud-tcop-ops         # 反向：资源优化与架构评估
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud AGSX (Agent Sandbox) Operations Skill

## Overview

Tencent Cloud Agent Runtime (AGSX) is a serverless sandbox service for AI Agent code execution and browser automation. AGSX provides 100ms cold start, 24h max lifecycle, and full e2b-protocol compatibility. Sandbox instances are created only via API/SDK/MCP (console is read-only).

This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **SDK-first execution** (tccli does not support this product), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

**Product page**: https://cloud.tencent.com/product/agsx
**API docs**: https://cloud.tencent.com/document/api/1814
**Console**: https://console.cloud.tencent.com/ags/sandbox

### CLI applicability (repository policy)

- **`cli_applicability: sdk-only`:** Official `tccli` does **not** expose this product. **No** `references/cli-usage.md` is required. SDK/API remains mandatory for all operations. Verified via `tccli ags help` returning "Invalid product".

## Five Core Standards (Quality Gates)

> See [shared-skills-boilerplate.md](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates).

### Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Reliability** | Multi-AZ region, retry on RequestLimitExceeded, instance health probes | `references/well-architected-assessment.md` |
| **Security** | CAM policies, API key rotation, credential masking, VPC isolation | `references/well-architected-assessment.md` |
| **Cost** | Terminate idle instances, monitor sandbox-hours, right-size specs | `references/well-architected-assessment.md` |
| **Efficiency** | Image prewarming, connection pooling, batch instance creation | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "AGSX", "Agent Runtime", "Agent Sandbox", "代码沙箱", "浏览器沙箱", "沙箱实例"
- Task involves CRUD or lifecycle on **SandboxTool**, **SandboxInstance**, **APIKey**, or **Image** resources
- Task keywords: sandbox tool, sandbox instance, e2b sandbox, tencentags, code interpreter sandbox, browser sandbox
- User asks to deploy, configure, troubleshoot, or monitor AGSX **via API, SDK, or automation**

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops`
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops`
- Task is about TKE / CVM / SCF compute → delegate to: `qcloud-tke-ops`
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### Delegation Rules

- If AGSX sandbox requires VPC access, configure VPC via `qcloud-vpc-ops` before sandbox creation.
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs.
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below.

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **AGSX (Agent Sandbox)**; return `{{output.product_assessment}}`.
> **sdk-only:** No `tccli` — use `Describe*` via `tencentcloud-sdk-python` only.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `account-wide` |

**Allowed:** SDK `Describe*` / list APIs only — **no** DeleteAgentPool/Create/Modify sandbox mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: agsx`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Default `ap-guangzhou` if skill allows |
| `{{env.E2B_API_KEY}}` | Sandbox runtime API key | NEVER ask the user; fail if unset |
| `{{env.E2B_DOMAIN}}` | Sandbox endpoint domain | Default `ap-guangzhou.tencentags.com` |
| `{{user.tool_name}}` | User-supplied tool name | Ask once; reuse |
| `{{user.tool_id}}` | User-supplied tool ID (stool-xxx) | Ask once; reuse |
| `{{user.instance_id}}` | User-supplied instance ID (si-xxx) | Ask once; reuse |
| `{{user.image_id}}` | User-supplied image ID (img-xxx) | Ask once; reuse |
| `{{output.resource_id}}` | From last API JSON response | Parse per API spec response path |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY`, `E2B_API_KEY`, or any credential field value.

| Execution Path | Safe Pattern | Unsafe Pattern |
|----------------|-------------|----------------|
| Console output | `E2B_API_KEY=<masked>` | `E2B_API_KEY=ak-abc123...` |
| Error messages | `Error: API call failed (credential omitted)` | `Error: InvalidSecretKey ... actual key...` |
| Log files | `[INFO] Credentials configured: Key=***` | `[INFO] Secret Key: abc123...` |
| Verification | `test -n "$E2B_API_KEY" && echo "Key is set"` | `echo $E2B_API_KEY` |
| Python SDK | `SecretKey=os.environ.get("...")` (env read safe) | `print(f"Config: {config}")` |

> **If any execution flow violates this rule, the skill SHALL be blocked from merge as a security incident.**

## API and Response Conventions

- **Service**: `ags` | **Version**: `2025-09-20` | **Endpoint**: `ags.tencentcloudapi.com`
- **Errors**: Map SDK errors to `code` / `message` fields per spec. Tencent Cloud uses `Response.Error` pattern.
- **Timestamps**: ISO 8601 format when API returns strings.
- **Idempotency**: CreateSandboxTool with duplicate ToolName returns `ResourceAlreadyExists`.

### Response Field Table (TE-4)

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateSandboxTool | `$.Response.ToolId` | string | New tool ID (stool-xxx) |
| StartSandboxInstance | `$.Response.InstanceId` | string | New instance ID (si-xxx) |
| CreateAPIKey | `$.Response.ApiKey` | string | Runtime API key (shown only once) |
| CreatePreCacheImageTask | `$.Response.RequestId` | string | Request tracking ID |
| Describe* | `$.Response.*Set[]` | array | Resource list |
| Delete/Stop | `$.Response.RequestId` | string | Request tracking ID |

### State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateSandboxTool | — | `AVAILABLE` | 5s | 120s |
| StartSandboxInstance | — | `RUNNING` | 2s | 60s |
| StopSandboxInstance | `RUNNING` | absent | 5s | 60s |
| DeleteSandboxTool | `AVAILABLE` | absent | 5s | 60s |

## Quick Start

### Prerequisites
- [ ] Python 3.8+ runtime for SDK fallback
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION` (default: ap-guangzhou)

### Verify Setup
```bash
python3 -c "from tencentcloud.ags.v20250920 import ags_client; print('SDK OK')"
test -n "$TENCENTCLOUD_SECRET_ID" && echo "SecretId: set"
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "SecretKey: set"
```

### Your First Command
→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

## Capabilities at a Glance

| Operation | API | Complexity | Risk Level |
|-----------|-----|------------|------------|
| List sandbox tools | DescribeSandboxToolList | Low | None |
| Create sandbox tool | CreateSandboxTool | Medium | Low |
| Update sandbox tool | UpdateSandboxTool | Medium | Medium |
| Delete sandbox tool | DeleteSandboxTool | Low | **High** — irreversible |
| Start sandbox instance | StartSandboxInstance | Medium | Low |
| List sandbox instances | DescribeSandboxInstanceList | Low | None |
| Stop sandbox instance | StopSandboxInstance | Low | **High** — irreversible |
| Pause sandbox instance | PauseSandboxInstance | Low | None |
| Resume sandbox instance | ResumeSandboxInstance | Low | None |
| Create API key | CreateAPIKey | Medium | Low |
| Delete API key | DeleteAPIKey | Low | **High** — irreversible |
| Pre-cache image | CreatePreCacheImageTask | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-28 | Initial skill generated from qcloud-skill-generator template |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions, 5 AGSX-specific safety rules incl. agent-pool cascade, active-agent deletion, force-termination no-rollback, pool config disruption, provisioning cost), `references/prompt-templates.md`. `max_iter=3` per AGENTS.md §8 |
| 1.2.0 | 2026-07-09 | Added `related_skills` to frontmatter (VPC, CAM, CLS, Monitor, FinOps, TCOP) |
| 1.5.0 | 2026-07-09 | TE-6: Error Code Reference table → `references/error-reference.md`; per-op Execution Flows → `references/execution-flows.md`; added JSON Path Conventions (TE-4); removed duplicate Prerequisites; moved Changelog earlier |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (SDK) → Validate → Recover**. Do not skip phases.

Since `cli_applicability: sdk-only`, only SDK paths are documented. See [references/execution-flows.md](references/execution-flows.md) for complete per-operation flows.

### Operation: CreateSandboxTool

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python` | Version ≥ 3.0.1300 | `pip install tencentcloud-sdk-python` |
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` | Non-empty | HALT; user configures env |
| Region | `TENCENTCLOUD_REGION` set or use default | `ap-guangzhou` supported | Suggest valid region |
| Quota | Call DescribeSandboxToolList | Tool count < quota | HALT; user raises quota |

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § CreateSandboxTool.

#### Post-execution Validation

See [execution-flows.md](references/execution-flows.md) § CreateSandboxTool.

#### Failure Recovery

See [execution-flows.md](references/execution-flows.md) § CreateSandboxTool or [error-reference.md](references/error-reference.md).

---

### Operation: DescribeSandboxToolList

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § DescribeSandboxToolList.

#### Present to User

See [execution-flows.md](references/execution-flows.md) § DescribeSandboxToolList.

---

### Operation: UpdateSandboxTool

#### Pre-flight Checks

See [execution-flows.md](references/execution-flows.md) § UpdateSandboxTool.

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § UpdateSandboxTool.

#### Post-execution Validation

See [execution-flows.md](references/execution-flows.md) § UpdateSandboxTool.

#### Failure Recovery

See [execution-flows.md](references/execution-flows.md) § UpdateSandboxTool or [error-reference.md](references/error-reference.md).

---

### Operation: DeleteSandboxTool (SAFETY GATE)

#### Pre-flight (Safety Gate)

See [execution-flows.md](references/execution-flows.md) § DeleteSandboxTool.

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § DeleteSandboxTool.

#### Post-execution Validation

See [execution-flows.md](references/execution-flows.md) § DeleteSandboxTool.

#### Failure Recovery

See [execution-flows.md](references/execution-flows.md) § DeleteSandboxTool or [error-reference.md](references/error-reference.md).

---

### Operation: StartSandboxInstance

#### Pre-flight Checks

See [execution-flows.md](references/execution-flows.md) § StartSandboxInstance.

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § StartSandboxInstance.

#### Post-execution Validation

See [execution-flows.md](references/execution-flows.md) § StartSandboxInstance.

#### Failure Recovery

See [execution-flows.md](references/execution-flows.md) § StartSandboxInstance or [error-reference.md](references/error-reference.md).

---

### Operation: DescribeSandboxInstanceList

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § DescribeSandboxInstanceList.

#### Present to User

See [execution-flows.md](references/execution-flows.md) § DescribeSandboxInstanceList.

---

### Operation: StopSandboxInstance (SAFETY GATE)

#### Pre-flight (Safety Gate)

See [execution-flows.md](references/execution-flows.md) § StopSandboxInstance.

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § StopSandboxInstance.

#### Post-execution Validation

See [execution-flows.md](references/execution-flows.md) § StopSandboxInstance.

#### Failure Recovery

See [execution-flows.md](references/execution-flows.md) § StopSandboxInstance or [error-reference.md](references/error-reference.md).

---

### Operation: CreateAPIKey

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § CreateAPIKey.

#### Post-execution Validation

See [execution-flows.md](references/execution-flows.md) § CreateAPIKey.

#### Failure Recovery

See [execution-flows.md](references/execution-flows.md) § CreateAPIKey or [error-reference.md](references/error-reference.md).

---

### Operation: DeleteAPIKey (SAFETY GATE)

#### Pre-flight (Safety Gate)

See [execution-flows.md](references/execution-flows.md) § DeleteAPIKey.

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § DeleteAPIKey.

#### Post-execution Validation

See [execution-flows.md](references/execution-flows.md) § DeleteAPIKey.

#### Failure Recovery

See [execution-flows.md](references/execution-flows.md) § DeleteAPIKey or [error-reference.md](references/error-reference.md).

---

### Operation: CreatePreCacheImageTask

#### Pre-flight Checks

See [execution-flows.md](references/execution-flows.md) § CreatePreCacheImageTask.

#### Execution — Python SDK

See [execution-flows.md](references/execution-flows.md) § CreatePreCacheImageTask.

#### Post-execution Validation

See [execution-flows.md](references/execution-flows.md) § CreatePreCacheImageTask.

#### Failure Recovery

See [execution-flows.md](references/execution-flows.md) § CreatePreCacheImageTask or [error-reference.md](references/error-reference.md).

---

## Reference Directory

- [Core Concepts](references/core-concepts.md) — AGSX domain model and sandbox types
- [API & SDK Usage](references/api-sdk-usage.md) — Full SDK examples for all 10 APIs
- [Troubleshooting Guide](references/troubleshooting.md) — Error remediation playbook
- [Monitoring & Alerts](references/monitoring.md) — CLS + CloudMonitor integration
- [Integration](references/integration.md) — e2b SDK + MCP client patterns
- [Well-Architected Assessment](references/well-architected-assessment.md) — 5-pillar audit checklist
- [Example Config](assets/example-config.yaml) — Reference configuration
- [Eval Queries](assets/eval_queries.json) — Test prompts for skill validation
- [Execution Flows](references/execution-flows.md) — Detailed per-operation execution steps
- [Error Reference](references/error-reference.md) — Full AGSX error code taxonomy

## Operational Best Practices

- **Least privilege**: CAM policies scoped to `ags:*` actions only
- **Availability**: Use ap-guangzhou as primary; ap-shanghai as failover
- **Cost**: Terminate idle instances within 5min; right-size specs via monitoring
- **Security**: Rotate API keys quarterly; enable CLS logging on all tools

---

## Safety Gates (Destructive Operations)

Every **Delete**, **Terminate**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier displayed
2. **Dependency check** (active instances under tool, keys in use)
3. **Impact display** (what resources will be affected)
4. **Post-operation verification** (poll until target state reached)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each AGSX execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

> **SDK-only skill.** `tccli` does not ship an `ags` subcommand — all GCL traces use
> `tencentcloud-sdk-python` execution paths. Spec Compliance dimension checks SDK-only
> constraints per [`references/rubric.md`](references/rubric.md) §5.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **recommended** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override (AGENTS.md §8 default for `qcloud-agsx-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 AGSX-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteAgentPool`, `TerminateAgentPool`, `DeleteAgent` (active) | **yes** | Cascade to in-flight executions |
| Sensitive mutating: `TerminateAgentExecution`, `UpdateAgentPoolConfig` (capacity/timeout) | **yes** | No-rollback; kills in-flight agents |
| Mutating: `CreateAgentPool`, `CreateAgent`, `StartAgentExecution` | **yes** | Compute-heavy billing; quota risk |
| Read-only: `DescribeAgentPools`, `DescribeAgents`, `DescribeAgentExecutions` | optional (max_iter=1, no hard abort) | Pre-flight for parent mutations |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result)
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### AGSX-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteSandboxTool` | Tool ID + Name + active instance count (`DescribeSandboxInstanceList` filtered by `ToolId`) echo; ... |
| 2 | `DeleteAgent` (any active agent) / `StopSandboxInstance` | Agent / instance ID + name + status echo; surface remaining TTL (`ExpireAt`); warn that removing ... |
| 3 | `TerminateAgentExecution` / force-stop a running execution | Execution ID + instance ID + start time echoed; warn that force termination does NOT roll back partial ... |
| 4 | `UpdateSandboxTool` (modify `DefaultTimeout`, `ToolType`, capacity, or security config) | Show current config → target config (`DefaultTimeout`, `ToolType`, `MaxConcurrency`, `VpcId`); fo... |
| 5 | `CreateSandboxTool` / `CreateAPIKey` / `StartSandboxInstance` (provisioning new resources) | For `CreateSandboxTool`: surface the tool's `DefaultTimeout` cost implications (sandbox-hours bil... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `DeleteAgentPool` with running agents

| Dimension | Score |
|---|---|
| Correctness | 0.5 (pool deleted, but in-flight agents not surfaced) |
| **Safety** | **0** (rule 1 violated — no agent count echo) |
| Idempotency | 1 |
| Traceability | 0.5 |
| Spec Compliance | 1 (SDK-only path used correctly) |

`decision: ABORT`. Recovery suggestion: "Recreate pool; check orphaned executions via `DescribeAgentExecutions`."

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `DescribeAgentPools` and RETRY on `UpdateAgentPoolConfig` capacity reduction).

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "req-abc123",
    "ToolId": "stool-xxxxxxxx",
    "InstanceId": "si-xxxxxxxx",
    "Status": "RUNNING",
    "ApiKey": "<masked>"
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
      "Message": "Parameter validation failed"
    }
  }
}
```

