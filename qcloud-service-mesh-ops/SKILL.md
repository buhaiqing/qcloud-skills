---
name: qcloud-service-mesh-ops
description: >-
  Use when the user needs to create, configure, or troubleshoot Tencent Cloud
  Service Mesh (TCM), Istio-based service mesh, Sidecar injection, traffic
  governance, canary deployment, mTLS, or distributed tracing. User mentions
  服务网格, TCM, Istio, Sidecar, 流量治理, 灰度发布, mTLS, 链路追踪,
  service mesh, traffic management. Not for K8s cluster node management (use
  `qcloud-tke-ops`), application monitoring (use `qcloud-monitor-ops`), or
  network ACLs (use `qcloud-vpc-ops`).
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-07-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/product/1261"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli tcm help` — CLI exposes CreateMesh, DeleteMesh,
    DescribeMesh, DescribeMeshList, LinkClusterList, ModifyMesh,
    ModifyTracingConfig, and related operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  gcl: required
  gcl_max_iter: 2
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud Service Mesh (TCM) Operations Skill

## Overview

Tencent Cloud Mesh (TCM) is a fully managed Istio-compatible service mesh service. It provides traffic governance, security policies (mTLS), and observability for microservices running on TKE clusters.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** `tccli tcm` covers mesh operations. You **MUST** ship `references/cli-usage.md` and document **both** the SDK and `tccli` step for every operation.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use with service mesh triggers; K8s nodes → `qcloud-tke-ops`; monitoring → `qcloud-monitor-ops` |
| 2 | **Structured I/O** | `{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders with TCM API field types |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute (CLI + SDK) → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 10 TCM-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | Service mesh lifecycle and configuration only; underlying K8s → `qcloud-tke-ops` |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-cluster mesh, failover configuration, circuit breaker | `references/well-architected-assessment.md` |
| **安全性 (Security)** | mTLS encryption, authorization policies, cert rotation | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Sidecar resource optimization, selective injection | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Canary deployment, traffic mirroring, cache strategy | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "服务网格" OR "TCM" OR "Istio" OR "Sidecar"
- Task keywords: 流量治理, 灰度发布, 金丝雀发布, mTLS, 服务间加密, 链路追踪, traffic management, canary deployment
- User asks to create mesh, configure traffic rules, enable Sidecar injection, set up mTLS

### SHOULD NOT Use This Skill When

- Task is **K8s cluster node management** → delegate to `qcloud-tke-ops`
- Task is **application monitoring / alerting** → delegate to `qcloud-monitor-ops`
- Task is **VPC network ACLs / security groups** → delegate to `qcloud-vpc-ops`
- Task is **container image registry** → delegate to `qcloud-tke-ops` (TCR)

### Delegation Rules

- Underlying K8s cluster operations: use `qcloud-tke-ops`
- Monitoring metrics and alerts: use `qcloud-monitor-ops`
- VPC/network configuration: use `qcloud-vpc-ops`
- Distributed tracing storage: use `qcloud-cls-ops` (if CLS is used)

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.mesh_name}}` | User-supplied mesh name | Ask once; reuse |
| `{{user.mesh_id}}` | Mesh unique ID | Ask once or derive from `DescribeMeshList` |
| `{{user.cluster_id}}` | TKE cluster ID to link | Ask once; verify cluster exists |
| `{{user.namespace}}` | K8s namespace for Sidecar injection | Ask once; default `default` |
| `{{output.mesh_id}}` | From API response | Parse per API spec |
| `{{output.cluster_link_status}}` | From API response | Parse per API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning:** NEVER expose `TENCENTCLOUD_SECRET_KEY` in output.

## JSON Path Reference

| Path | Maps To |
|------|---------|
| `mesh.id` | `$.Response.MeshList[*].MeshId` |
| `mesh.name` | `$.Response.MeshList[*].MeshName` |
| `mesh.status` | `$.Response.MeshList[*].MeshStatus` |
| `cluster.link_status` | `$.Response.LinkedClusterSet[*].Status` |
| `sidecar.inject_status` | `$.Response.SidecarInjectStatus` |

## Quick Start

### What This Skill Does
Enables you to create and manage Tencent Cloud Service Mesh (TCM) — configure traffic governance, mTLS encryption, Sidecar injection, and observability for microservices.

### Prerequisites
- [ ] `tccli` CLI installed
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION`
- [ ] Existing TKE cluster to link with mesh

### Verify Setup
```bash
tccli tcm DescribeMeshList --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Your First Command
```bash
# Create a service mesh
tccli tcm CreateMesh \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --MeshName "my-mesh" \
  --MeshVersion "1.18.1-istio"
```

### Next Steps
- [Common Operations](#execution-flows) — Create mesh, link cluster, configure Sidecar
- [Troubleshooting](references/troubleshooting.md) — Fix mesh issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateMesh | Create a new service mesh | Medium | Low |
| DescribeMeshList | List all meshes | Low | None |
| DeleteMesh | Delete a mesh | Low | **High** — removes all mesh config |
| LinkClusterList | Link TKE clusters to mesh | Medium | Medium |
| UnlinkCluster | Unlink cluster from mesh | Medium | Medium |
| ModifyMesh | Update mesh configuration | Medium | Medium |
| ModifyTracingConfig | Configure distributed tracing | Medium | Low |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-07-04 | GCL rubric/prompt-templates aligned to Tier A standard (rubric: 8 sections, prompt-templates: 7 sections with TE-6 backbone). |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

### Operation: Create Mesh

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` etc. | Non-empty | HALT; user configures env |
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Mesh version | Check available versions | Version supported | Use supported version |
| Cluster exists | `tccli tke DescribeClusters` | Cluster ACTIVE | Create cluster first |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli tcm CreateMesh \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --MeshName "{{user.mesh_name}}" \
  --MeshVersion "1.18.1-istio"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.mesh_id}}` from `$.Response.MeshId`.
2. Poll `DescribeMeshList` until `MeshStatus = RUNNING`.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.MeshNameExists` | Use a different name |
| `ResourceQuotaExceeded.Mesh` | HALT; raise per-region mesh quota |
| `InvalidParameterValue.MeshVersion` | Use supported version |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Link Cluster to Mesh

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Mesh exists | `DescribeMeshList` | Status RUNNING | Create mesh first |
| Cluster exists | `tccli tke DescribeClusters` | Status RUNNING | Create cluster first |
| Cluster not linked | Check `LinkedClusterSet` | Cluster not in list | Skip if already linked |

#### Execution — CLI

```bash
tccli tcm LinkClusterList \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --MeshId "{{output.mesh_id}}" \
  --ClusterList '["{{user.cluster_id}}"]'
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

Poll `DescribeMesh` until cluster shows in `LinkedClusterSet` with status `RUNNING`.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.Mesh` | Verify mesh ID |
| `ResourceNotFound.Cluster` | Verify cluster ID |
| `OperationDenied.ClusterAlreadyLinked` | Already linked; treat as success |
| `OperationDenied.ClusterStatusNotRunning` | Wait for cluster to be RUNNING |

### Operation: Enable Sidecar Injection

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Mesh exists | `DescribeMeshList` | Status RUNNING | Create mesh first |
| Cluster linked | Check `LinkedClusterSet` | Cluster is linked | Link cluster first |

#### Execution — CLI (via kubectl after mesh setup)

```bash
# Label namespace for automatic Sidecar injection
kubectl label namespace {{user.namespace}} istio-injection=enabled --cluster={{user.cluster_id}}
```

#### Post-execution Validation

Deploy test pod and verify Sidecar container is injected:

```bash
kubectl get pods -n {{user.namespace}} -o jsonpath='{.items[*].spec.containers[*].name}'
# Should show 'istio-proxy' alongside app container
```

### Operation: Delete Mesh

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with the mesh ID and name.
- **MUST** warn: deleting a mesh removes all traffic governance rules, mTLS policies, and observability configs.
- **MUST** unlink all clusters before deletion (or verify they're unlinked).

#### Execution — CLI

```bash
# 1. Unlink all clusters first
tccli tcm UnlinkCluster \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --MeshId "{{output.mesh_id}}" \
  --ClusterId "{{user.cluster_id}}"

# 2. Delete mesh
tccli tcm DeleteMesh \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --MeshId "{{output.mesh_id}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

Poll `DescribeMeshList`; expect mesh absent within 60s.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.Mesh` | Already deleted; treat as success |
| `OperationDenied.MeshHasLinkedClusters` | Unlink all clusters first |
| `OperationDenied.MeshHasResources` | Remove mesh resources first |

## Error Code Reference (TCM-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.MeshNameExists` | Mesh name already exists | Use a different name |
| `InvalidParameterValue.MeshVersion` | Unsupported mesh version | Check supported versions |
| `ResourceNotFound.Mesh` | Mesh ID not found | Verify mesh ID |
| `ResourceNotFound.Cluster` | Cluster ID not found | Verify cluster ID |
| `ResourceQuotaExceeded.Mesh` | Mesh quota exceeded | HALT; raise quota |
| `OperationDenied.MeshAlreadyExists` | Mesh already exists | Use existing or rename |
| `OperationDenied.ClusterAlreadyLinked` | Cluster already linked | Treat as success |
| `OperationDenied.ClusterStatusNotRunning` | Cluster not in RUNNING state | Wait for cluster |
| `OperationDenied.MeshHasLinkedClusters` | Cannot delete with linked clusters | Unlink first |
| `OperationDenied.MeshHasResources` | Mesh has active resources | Clean up first |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Exponential backoff (3x) |

## Safety Gates (Destructive Operations)

Every **DeleteMesh** MUST have:

1. Explicit user confirmation with mesh ID
2. Dependency check (linked clusters, mesh resources)
3. Pre-warning about configuration loss
4. Post-delete verification (poll until absent)

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)**. The Quality Gate
is a **runtime** scoring layer that audits each TCM execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, TCM-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteMesh`, `UnlinkCluster` | **yes** | Irreversible; removes mesh config or severs cluster link |
| Sensitive mutating: `ModifyMesh` (version/config change) | **yes** | Configuration drift risk |
| Mutating: `CreateMesh`, `LinkClusterList` | **yes** | Cost/state-change risk |
| Read-only: `DescribeMesh`, `DescribeMeshList`, `ModifyTracingConfig` | optional (max_iter=1) | Polling tails are part of the parent op |

### Decision flow (first match wins)

1. **Safety = 0** OR any rubric rule violation on destructive op ⇒ **ABORT** (no partial result). Missing user confirmation for DeleteMesh ⇒ ABORT.
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

---

## Prerequisites

1. **Install `tccli` CLI:**

```bash
pip install tccli
tccli version
```

2. **Configure Credentials:**

```bash
export TENCENTCLOUD_SECRET_ID="AKID..."
export TENCENTCLOUD_SECRET_KEY="..."
export TENCENTCLOUD_REGION="ap-guangzhou"
```

3. **Verify:**

```bash
tccli tcm DescribeMeshList --Region "{{env.TENCENTCLOUD_REGION}}"
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Integration](references/integration.md)
- [Prompt Templates](references/prompt-templates.md) — GCL skeletons
- [Rubric](references/rubric.md) — GCL scoring
