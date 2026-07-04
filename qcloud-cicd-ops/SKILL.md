---
name: qcloud-cicd-ops
description: >-
  Use when the user needs to create, configure, trigger, or troubleshoot CI/CD
  pipelines, code repositories, artifact repositories, or automated deployments
  on Tencent Cloud. User mentions CI/CD, 流水线, 持续集成, 持续部署, DevOps,
  自动化部署, pipeline, build, deploy automation. Not for application runtime
  monitoring (use `qcloud-monitor-ops`), K8s cluster operations (use
  `qcloud-tke-ops`), or serverless function deployment (use `qcloud-scf-ops`).
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-07-03"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/product/"
  cli_applicability: "sdk-only"
  cli_support_evidence: >-
    Verified via `tccli codepipeline help` and `tccli coding help` — both return
    "Invalid choice". `tccli cloudstudio help` is available but covers IDE
    workspaces, not CI/CD pipelines. CI/CD operations require Python SDK or
    CODING DevOps platform API directly.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  gcl: required
  gcl_max_iter: 2
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CI/CD Pipeline Operations Skill

## Overview

CI/CD (Continuous Integration / Continuous Deployment) pipelines automate the build, test, and deployment lifecycle. This skill covers Tencent Cloud CI/CD operations via Python SDK and API, including Cloud Studio workspaces integration where applicable.

### CLI applicability (repository policy)

- **`cli_applicability: sdk-only`:** `tccli` does NOT expose CI/CD pipeline operations. You **MUST NOT** ship `references/cli-usage.md` for CI/CD operations. Use Python SDK (`tencentcloud-sdk-python`) or direct API calls for all operations. `cloudstudio` CLI is available for IDE workspace management only.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with CI/CD-specific triggers; K8s deploy → delegate to `qcloud-tke-ops`; SCF deploy → delegate to `qcloud-scf-ops` |
| 2 | **Structured I/O** | `{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders with pipeline API field types |
| 3 | **Explicit Actionable Steps** | Every pipeline op: Pre-flight → Execute (SDK) → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 10 CI/CD-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | CI/CD pipeline + code repository + artifact repository only; K8s deploy → `qcloud-tke-ops`; Serverless → `qcloud-scf-ops` |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Pipeline retry strategy, multi-stage approval, artifact versioning | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Credential management in pipeline, code scanning integration | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Pipeline runner cost, build cache optimization | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Parallel stages, cache strategy, pipeline template reuse | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CI/CD pipeline" OR "流水线" OR "持续集成" OR "持续部署" OR "DevOps"
- Task keywords: pipeline, build, deploy automation, artifact, code repository, 构建, 部署, 制品库
- User asks to create, trigger, or troubleshoot an automated build/deploy pipeline

### SHOULD NOT Use This Skill When

- Task is **K8s cluster management** → delegate to `qcloud-tke-ops`
- Task is **serverless function deployment** → delegate to `qcloud-scf-ops`
- Task is **application monitoring / alerting** → delegate to `qcloud-monitor-ops`
- Task is **container image registry** → delegate to `qcloud-tke-ops` (TCR)

### Delegation Rules

- Pipeline deploy-to-TKE: use `qcloud-tke-ops` for the K8s deployment step
- Pipeline deploy-to-SCF: use `qcloud-scf-ops` for the function update step
- Multi-product pipeline: handle each product with its skill; pipeline orchestrates the flow

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.pipeline_name}}` | User-supplied pipeline name | Ask once; reuse |
| `{{user.pipeline_id}}` | Pipeline unique ID | Ask once or derive from API |
| `{{user.repo_url}}` | Code repository URL | Ask once; verify format |
| `{{user.branch}}` | Git branch for pipeline trigger | Ask once; default `main` |
| `{{output.pipeline_id}}` | From API response | Parse per API spec |
| `{{output.build_id}}` | From API response | Parse per API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning:** NEVER expose `TENCENTCLOUD_SECRET_KEY` in output. Use `test -n "$TENCENTCLOUD_SECRET_KEY"` for verification only.

## JSON Path Reference

| Path | Maps To |
|------|---------|
| `pipeline.id` | `$.Response.PipelineId` |
| `pipeline.name` | `$.Response.PipelineName` |
| `pipeline.status` | `$.Response.PipelineStatus` |
| `build.id` | `$.Response.BuildId` |
| `build.status` | `$.Response.BuildStatus` |
| `build.log` | `$.Response.BuildLog` |

## Quick Start

### What This Skill Does
Enables you to create, trigger, and manage CI/CD pipelines — automate build, test, and deployment workflows on Tencent Cloud.

### Prerequisites
- [ ] Python 3.8+ installed
- [ ] `tencentcloud-sdk-python` installed: `pip install tencentcloud-sdk-python`
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
python3 -c "import tencentcloud.common.credential; print('SDK OK')"
```

### Your First Command
→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Next Steps
- [Common Operations](#execution-flows) — Create, trigger, monitor pipelines
- [Troubleshooting](references/troubleshooting.md) — Fix pipeline failures

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreatePipeline | Create a new CI/CD pipeline | Medium | Low |
| DescribePipelines | List / describe pipelines | Low | None |
| DeletePipeline | Delete a pipeline | Low | **High** — removes automation |
| StartPipeline | Trigger a pipeline run | Low | Low |
| StopPipeline | Stop a running pipeline | Low | Medium |
| DescribeBuildLogs | View build logs | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-03 | Initial CI/CD skill, SDK-only execution. Scope: pipeline CRUD, trigger/monitor, code repository integration, artifact management. Delegates K8s deploy to `qcloud-tke-ops`, SCF deploy to `qcloud-scf-ops`. |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (SDK) → Validate → Recover**.

### Operation: Create Pipeline

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` etc. | Non-empty | HALT; user configures env |
| SDK installed | `python3 -c "import tencentcloud"` | Exit code 0 | `pip install tencentcloud-sdk-python` |
| Name uniqueness | Query existing pipelines via API | No existing pipeline with same name | Use different name |

#### Execution — Python SDK

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.pipeline_id}}` from API response.
2. Poll Describe API until `PipelineStatus = ACTIVE`.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.PipelineNameExists` | Use a different name |
| `ResourceQuotaExceeded.Pipeline` | HALT; raise per-region pipeline quota |
| `InvalidSecretKey` | HALT; fix credentials |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Trigger Pipeline

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Pipeline exists | Query pipeline by `{{user.pipeline_id}}` | Status ACTIVE | HALT; create pipeline first |

#### Execution — Python SDK

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

Poll Describe API until build completes:

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.Pipeline` | Verify pipeline ID |
| `OperationDenied.PipelineRunning` | Wait for current build to complete |
| `InvalidParameter.BranchNotFound` | Check branch exists in repo |

### Operation: Describe Pipelines

#### Execution — Python SDK

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: Delete Pipeline

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with the pipeline ID and name.
- **MUST** warn: deleting a pipeline removes all automation; any running builds will be cancelled.
- **MUST** list any dependent resources (webhooks, triggers) that will become orphaned.

#### Execution — Python SDK

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

Poll Describe API for the ID; expect absent within 30s.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.Pipeline` | Already deleted; treat as success |
| `OperationDenied.PipelineRunning` | Stop running build first |

## Error Code Reference (CI/CD-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.PipelineNameExists` | Pipeline name already exists | Use a different name |
| `InvalidParameter.BranchNotFound` | Specified branch not found in repo | Check branch name |
| `ResourceNotFound.Pipeline` | Pipeline ID not found | Verify pipeline ID |
| `ResourceNotFound.Project` | Project not found | Verify project ID |
| `ResourceQuotaExceeded.Pipeline` | Pipeline quota exceeded | HALT; raise quota |
| `OperationDenied.PipelineRunning` | Pipeline is already running | Wait for completion |
| `OperationDenied.PipelineSuspended` | Pipeline is suspended | Resume pipeline first |
| `OperationDenied.NotAuthorized` | Insufficient permissions | HALT; check CAM permissions |
| `InternalError.BuildFailed` | Build failed due to script error | Check build logs for details |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Exponential backoff (3x) |
| `InternalError` | Server error | Retry with RequestId (3x) |

## Safety Gates (Destructive Operations)

Every **DeletePipeline** MUST have:

1. Explicit user confirmation with pipeline ID
2. Dependency check (running builds; dependent webhooks)
3. Pre-warning about automation loss
4. Post-delete verification (poll until absent)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** quality gate for all mutation operations.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | frontmatter `gcl: required` |
| max_iterations | **2** | frontmatter `gcl_max_iter: 2` |
| Rubric instance | `references/rubric.md` | 5 dimensions, CI/CD-specific safety rules |
| Prompt templates | `references/prompt-templates.md` | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | per AGENTS.md §7 |

### When the loop runs

| Operation | Loop required? | Reason |
|---|---|---|
| `CreatePipeline` | Yes | Creates new automation |
| `DeletePipeline` | Yes (blocking) | Removes automation, cancels builds |
| `StartPipeline` | Yes (blocking) | Triggers builds, may cause duplicate runs |
| `StopPipeline` | Yes (blocking) | Aborts running builds |
| `DescribePipelines` | No | Read-only |
| `DescribeBuildLogs` | No | Read-only |

### Decision flow (first match wins)

1. **Safety=0** → `ABORT` — immediate halt, no output
2. **current_iter >= max_iterations** → `MAX_ITER` — return best result, blocking=true
3. **All thresholds met** → `PASS` — output accepted
4. **Otherwise** → `RETRY` — inject suggestions, increment iter

---

## Prerequisites

1. **Install Python SDK:**

```bash
pip install tencentcloud-sdk-python
```

2. **Configure Credentials:**

```bash
export TENCENTCLOUD_SECRET_ID="AKID..."
export TENCENTCLOUD_SECRET_KEY="..."
export TENCENTCLOUD_REGION="ap-guangzhou"
```

3. **Verify:**

```bash
python3 -c "from tencentcloud.common import credential; print('OK')"
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Integration](references/integration.md)

> Note: This skill uses `cli_applicability: sdk-only` as `tccli codepipeline` is not available. CLI operations are not documented.
