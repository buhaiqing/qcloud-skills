---
name: qcloud-tke-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud TKE (Tencent Kubernetes Engine) — cluster lifecycle, node pool management,
  addon installation, and Kubernetes cluster diagnostics. User mentions TKE, 容器服务,
  Tencent Kubernetes Engine, k8s, Kubernetes, cluster, node pool, or describes container
  orchestration scenarios even without naming the product directly. Not for billing, CAM,
  VPC-only operations, application-level k8s YAML debugging, or related products that
  have their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-tke),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.2.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/457"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli tke help` - CLI exposes CreateCluster, DescribeClusters,
    DeleteCluster, DescribeClusterInstances, CreateClusterAsGroup,
    DescribeClusterAsGroups, DeleteClusterAsGroups, InstallComponents,
    ModifyClusterAsGroup, DescribeClusterSecurity, SetAddonsRemainQuota,
    and 30+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud TKE Operations Skill

## Overview

TKE (Tencent Kubernetes Engine) is Tencent Cloud's managed Kubernetes service providing container orchestration, node pool management, and cluster lifecycle control. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports TKE. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path; Python SDK is used for edge-case operations CLI doesn't expose.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers (TKE, 容器服务, k8s) and delegation rules (VPC → qcloud-vpc-ops, CLB → qcloud-clb-ops, CVM → qcloud-cvm-ops) |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps for CLI and SDK paths |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 TKE-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (TKE), primary resource model (Cluster); cross-product delegation documented |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ node pools, cluster backup/restore, node auto-repair, self-healing cluster components | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, RBAC configuration, security group rules, cluster credential (kubeconfig) management | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Node type comparison, pay-as-you-go vs prepaid nodes, idle cluster detection, right-sizing node pools | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch cluster operations, auto-scaling via node pool, addon lifecycle management, CI/CD integration | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "TKE" OR "容器服务" OR "Kubernetes" OR "k8s" OR "Tencent Kubernetes Engine"
- Task involves CRUD or lifecycle operations on **TKE Clusters** (CreateCluster, DescribeClusters, DeleteCluster, ModifyCluster)
- Task involves **Node Pools** (CreateClusterAsGroup, DescribeClusterAsGroups, ModifyClusterAsGroup, DeleteClusterAsGroups)
- Task involves **Cluster Instances/Nodes** (DescribeClusterInstances, DeleteClusterInstances, scale nodes)
- Task involves **Addons/Components** (InstallComponents, DescribeClusterAttribute for addon status, SetAddonsRemainQuota)
- Task keywords: create cluster, deploy k8s, kubernetes cluster, node pool, worker node scaling, addon, kubeconfig, container service, kubectl context
- User asks to deploy, configure, troubleshoot, or monitor TKE **via API, SDK, CLI, or automation**
- User describes cluster health issues, node failures, pod scheduling problems without naming product

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **VPC network only** (subnet, route table, NAT gateway) → delegate to: `qcloud-vpc-ops`
- Task is **CLB load balancing** configuration → delegate to: `qcloud-clb-ops`
- Task is **CVM instance** management (worker nodes as bare VMs) → delegate to: `qcloud-cvm-ops`
- Task is **COS object storage** for images/artifacts → delegate to: `qcloud-cos-ops`
- Task is **application-level Kubernetes YAML** (Deployments, Services, Ingress) → application-level tool, not this skill
- Task is cloud **container registry (TCR)** specific → delegate to `qcloud-tcr-ops` (when present)
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- TKE depends on VPC: verify VPC/Subnet/SecurityGroup exist via `qcloud-vpc-ops` before CreateCluster
- TKE uses CLB for Service type LoadBalancer: delegate load balancer operations to `qcloud-clb-ops`
- TKE worker nodes are CVM instances: delegate VM-level operations (SSH, disk, OS) to `qcloud-cvm-ops`
- TKE container images may use COS/TCR: delegate storage/registry to `qcloud-cos-ops` or `qcloud-tcr-ops`
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **TKE**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` and `GetMonitorData` only — **no** DeleteCluster/DeleteNode/Modify mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: tke`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use default `ap-guangzhou` if unset |
| `{{user.vpc_id}}` | User-supplied VPC ID | Ask once; reuse (e.g., `vpc-xxx`) |
| `{{user.subnet_id}}` | User-supplied subnet ID | Ask once; reuse (e.g., `subnet-xxx`) |
| `{{user.cluster_name}}` | User-supplied cluster name | Ask once; reuse |
| `{{user.cluster_id}}` | User-supplied cluster ID (cls-xxx) | Ask once; reuse for subsequent ops |
| `{{user.node_pool_name}}` | User-supplied node pool name | Ask once; reuse |
| `{{user.node_pool_id}}` | User-supplied node pool ID (np-xxx) | Ask once; reuse |
| `{{user.instance_type}}` | User-supplied CVM instance type for nodes | Ask once; suggest standard type |
| `{{user.kubeconfig}}` | User-supplied kubeconfig file path | Ask once; default ~/.kube/config |
| `{{output.cluster_id}}` | From CreateCluster response | Parse `$.Response.ClusterId` |
| `{{output.node_pool_id}}` | From CreateClusterAsGroup response | Parse `$.Response.NodePoolId` |
| `{{output.request_id}}` | From any API response | Parse `$.Response.RequestId` for tracking |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY` in any output. Mask all credentials with `***` or `<masked>`. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅ | `echo $TENCENTCLOUD_SECRET_KEY` ❌

## API and Response Conventions

- **API spec is canonical** for path, query, body fields, enums, and response shapes at https://cloud.tencent.com/document/api/457
- **Errors:** Map SDK/HTTP errors to `code` / `message` fields per spec. Tencent Cloud uses `Response.Error` pattern
- **Timestamps:** ISO 8601 format when API returns strings
- **Async behavior:** Cluster creation is async — poll DescribeClusters until ClusterStatus = `Running`
- **Kubeconfig:** Access token for clusters has a 24-hour expiry; re-fetch via GetClusterEndpoints + DescribeClusterSecurity

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateCluster | `$.Response.ClusterId` | string | New cluster ID (e.g., `cls-xxxxxxxx`) |
| DescribeClusters | `$.Response.Clusters[].ClusterId` | array | Cluster IDs |
| DescribeClusters | `$.Response.Clusters[].ClusterStatus` | string | Cluster lifecycle state |
| DescribeClusters | `$.Response.Clusters[].ClusterName` | string | Cluster name |
| DescribeClusters | `$.Response.Clusters[].ClusterType` | string | Cluster type: MANAGED_TKE / INDEPENDENT |
| CreateClusterAsGroup | `$.Response.NodePoolId` | string | New node pool ID (e.g., `np-xxxxxxxx`) |
| DescribeClusterAsGroups | `$.Response.NodePoolSet[].NodePoolId` | array | Node pool IDs |
| DeleteCluster | `$.Response.RequestId` | string | Request tracking ID |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateCluster | — | `Running` | 10s | 600s |
| DeleteCluster | any stable state | `Deleting` → absent | 10s | 600s |
| CreateClusterAsGroup | — | `Running` | 10s | 300s |
| ModifyClusterAsGroup | any stable state | `Running` | 10s | 300s |

## Quick Start

### What This Skill Does

This skill enables you to deploy, configure, troubleshoot, and monitor TKE (Tencent Kubernetes Engine) clusters on Tencent Cloud using the `tccli` CLI (primary) or `tencentcloud-sdk-python-tke` SDK (fallback).

### Prerequisites

- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`
- [ ] VPC and subnet created (delegate to `qcloud-vpc-ops` if needed)

### Verify Setup

```bash
# Check CLI and credentials
tccli tke DescribeClusters --Region {{env.TENCENTCLOUD_REGION}} --Offset 0 --Limit 1
```

### Your First Command

```bash
# List all TKE clusters
tccli tke DescribeClusters --Region {{env.TENCENTCLOUD_REGION}} --Offset 0 --Limit 100
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — Understand TKE architecture
- [Execution Flows](#execution-flows-agent-readable) — Create, manage, and delete clusters
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateCluster | Create a managed or independent Kubernetes cluster | Medium | Low |
| DescribeClusters | View cluster details, status, endpoints | Low | None |
| CreateClusterAsGroup | Create a node pool with auto-scaling | Medium | Low |
| ModifyClusterAsGroup | Scale or modify node pool configuration | Medium | Medium |
| InstallComponents | Install cluster addons (metrics-server, coredns, etc.) | Low | Low |
| DeleteCluster | Terminate a cluster and its resources | Low | **High** — irreversible |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2026-06-04 | Added 4 missing execution flows: UpdateClusterVersion, DeleteNode/DrainNode, AddNodeToPool (batch scale), ModifyClusterAttribute/CreateClusterEndpoint — with full pre-flight safety gates per rubric §4; Fixed DeleteCluster pre-flight check to use API path; Fixed container runtime inconsistency; Added 18 eval_queries test cases |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 TKE-specific safety rules incl. cluster-delete cascade, node-drain PDB guard, version-upgrade addon compat, public-endpoint security), `references/prompt-templates.md` (Generator + Critic + Orchestrator). `max_iter=2` per AGENTS.md §8 |
| 1.0.1 | 2026-05-28 | Update K8s version to 1.30.0; Fix polling script timeout handling; Change container runtime to containerd; Add TCR integration guide; Clarify NodePoolId extraction |
| 1.0.0 | 2026-05-21 | Initial release — cluster lifecycle, node pools, addons, dual-path |

---

## Execution Flows (Agent-Readable)

### Operation: CreateCluster

**Pre-flight**: 检查 CLI/SDK、Credentials、VPC/Subnet/SG 是否存在、Quota — 完整检查表见 [references/cli-usage.md](references/cli-usage.md) §Pre-flight。
**CLI**: `tccli tke CreateCluster ...` — 完整命令见 [references/cli-usage.md](references/cli-usage.md) §CreateCluster。
**SDK**: 示例见 [references/api-sdk-usage.md](references/api-sdk-usage.md) §CreateCluster。
**验证**: 轮询 DescribeClusters 直到 ClusterStatus = Running (max 600s)。
**错误处理**: 见 [通用错误表](#error-code-reference-tke-specific) + `ResourceInsufficient.Vpc` → HALT。

> TCR 集成（可选）：见 [references/advanced/tcr-integration.md](references/advanced/tcr-integration.md)。

### Operation: DescribeClusters

**CLI**: `tccli tke DescribeClusters --Region {{env.TENCENTCLOUD_REGION}} [--ClusterId {{user.cluster_id}}]`
**SDK**: 等价命令见 [references/api-sdk-usage.md](references/api-sdk-usage.md) §DescribeClusters。
**输出字段**: 见 [Response Field Table](#response-field-table)。

### Operation: CreateClusterAsGroup (Node Pool)

**Pre-flight**: Cluster 是否 Running、Instance type 是否可用 — 检查表见 [references/cli-usage.md](references/cli-usage.md) §Pre-flight。
**CLI**: `tccli tke CreateClusterAsGroup ...` — 完整命令见 [references/cli-usage.md](references/cli-usage.md) §CreateClusterAsGroup。
**SDK**: 示例见 [references/api-sdk-usage.md](references/api-sdk-usage.md) §CreateClusterAsGroup。
**验证**: 轮询 DescribeClusterAsGroups 直到 NodePoolStatus = Running (max 300s)。
**错误处理**: 见 [通用错误表](#error-code-reference-tke-specific)。

### Operation: DeleteCluster

**Pre-flight (Safety Gate)**:
- **MUST** 显式确认：删除集群 `{{user.cluster_name}}` (`{{user.cluster_id}}`)
- **MUST** 警示：删除所有节点、Pod 和数据；提示用户先导出 YAML
- **MUST** 检查：节点健康（DescribeClusterInstances）；用户手动确认 workload（kubectl 不在本 Skill 范围内）
- **MUST** 检查：节点池已缩容到 0 或先删除

**CLI**: `tccli tke DeleteCluster --ClusterId "{{user.cluster_id}}" --InstanceDeleteMode "TerminateAndDestroy"`
**SDK**: 示例见 [references/api-sdk-usage.md](references/api-sdk-usage.md) §DeleteCluster。
**验证**: 轮询 DescribeClusters 直到 NotFound (max 600s)。
**错误处理**: 见 [通用错误表](#error-code-reference-tke-specific)。

### Operation: InstallComponents (Addon Management)

**CLI**: `tccli tke InstallComponents --ClusterId "{{user.cluster_id}}" --Components '[{"ComponentName":"metrics-server","ComponentVersion":"3.8.4"}]'`
**验证**: Addon 状态应为 Running（DescribeClusterAttribute）。
**错误处理**: 见 [通用错误表](#error-code-reference-tke-specific) + `AddonConflict`（HALT）、`AddonNotSupport`（升级集群）。

### Operation: UpdateClusterVersion (K8s Upgrade)

> **GCL 安全规则（Rubric §4 rule 4）**: 必须检查 addon 兼容性；拒绝跳版本升级（eg 1.28→1.30）；必须显式确认。

**Pre-flight (Safety Gate)**:

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster exists | `tccli tke DescribeClusters --ClusterId {{user.cluster_id}}` | Running | HALT |
| Current → target version | DescribeClusters + user input | ≥ current, no minor-skip | HALT; warn one-directional |
| Addon compatibility | `DescribeClusterAttribute --Attribute "ClusterLevel/Addons"` | Compatible | Surface incompatible addons; require confirm |
| User confirm | Cluster ID + name + version change | User approves | HALT |

**CLI**: `tccli tke ModifyCluster --ClusterId "{{user.cluster_id}}" --ClusterVersion "{{user.k8s_version}}"`
**SDK**: 示例见 [references/api-sdk-usage.md](references/api-sdk-usage.md) §ModifyCluster。
**验证**: 轮询 DescribeClusters 直到 ClusterStatus = Running 且 ClusterVersion = target (max 1200s)。
**错误处理**: 见 [通用错误表](#error-code-reference-tke-specific) + `InvalidParameterValue`（不支持目标版本 → HALT）。

### Operation: DeleteNode / DrainNode

> **GCL 安全规则（Rubric §4 rule 2）**: 节点 ID 回声；>50% 节点拒绝；PDB 检查；Desired/Ready 节点数显示。

**Pre-flight (Safety Gate)**:

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster exists | `tccli tke DescribeClusters --ClusterId {{user.cluster_id}}` | Running | HALT |
| Node instances | `DescribeClusterInstances` | Nodes exist; capture InstanceId(s) | HALT |
| Node count check | Parse `$.Response.TotalCount` | Drain < 50% of total | **REFUSE** if >50% |
| Instance IDs | User-supplied `{{user.instance_ids}}` | At least one ID | HALT |
| PDB warning | Warn of PDB constraints | User acknowledges | Surface warning |

**CLI**: `tccli tke DeleteClusterInstances --ClusterId "{{user.cluster_id}}" --InstanceIds '[{{user.instance_ids}}]' --DeleteMode "TERMINATE"`
**SDK**: 示例见 [references/api-sdk-usage.md](references/api-sdk-usage.md) §DeleteClusterInstances。
**验证**: 轮询 DescribeClusterInstances 直到 removed instances 消失 (max 300s)。
**错误处理**: 见 [通用错误表](#error-code-reference-tke-specific)。

### Operation: AddNodeToPool (Batch Scale)

> **GCL 安全规则（Rubric §4 rule 3）**: 配额检查；当前+提议节点数显示；>10% 增加需确认；不超过 MaxNum。

**Pre-flight (Safety Gate)**:

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster + NodePool exists | DescribeClusters + DescribeClusterAsGroups | Running | HALT |
| Current node count | `$.Response.NodePoolSet[].DesiredNodeCount` | Known | Compare |
| Proposed count | User-supplied `{{user.desired_nodes}}` | ≤ MaxNum, ≥ MinNum | Adjust bounds |
| Scale risk | Proposed > current × 1.1 | Require confirm | HALT |
| Account quota | `tccli tke DescribeUserQuota` | Sufficient | HALT |

**CLI**: `tccli tke ModifyClusterAsGroup --ClusterId "{{user.cluster_id}}" --NodePoolId "{{user.node_pool_id}}" --DesiredNodeCount {{user.desired_nodes}}`
**SDK**: 示例见 [references/api-sdk-usage.md](references/api-sdk-usage.md) §ModifyClusterAsGroup。
**验证**: 轮询 DescribeClusterAsGroups 直到 DesiredNodeCount 匹配 (max 300s)。
**错误处理**: 见 [通用错误表](#error-code-reference-tke-specific) + `InvalidParameterValue`（超出 [MinNum,MaxNum] → HALT）、`ResourceInsufficient`（更换类型/子网）。

### Operation: ModifyClusterAttribute / CreateClusterEndpoint

> **GCL 安全规则（Rubric §4 rule 5）**: 公网端点须有 IP 白名单确认；端点删除须警示 kubectl 中断；当前状态须显示。

**Pre-flight (Safety Gate)**: Cluster 是否 Running（DescribeClusters）；当前端点状态（DescribeClusterEndpoints）；属性变更（用户指定名称/描述/端点）。

**CLI**: `tccli tke ModifyCluster --ClusterId "{{user.cluster_id}}" --ClusterName "{{user.cluster_name}}"`（端点为 SDK-only 操作）
**SDK**: 示例见 [references/api-sdk-usage.md](references/api-sdk-usage.md) §ModifyCluster + 附录 Endpoint 操作。
**验证**: 属性修改 → DescribeClusters；端点变更 → DescribeClusterEndpoints。
**错误处理**: 见 [通用错误表](#error-code-reference-tke-specific)。

---

## Error Code Reference (TKE-Specific)

| Code | Agent Action |
|------|-------------|
| `InvalidParameter` | Fix param — check API spec |
| `InvalidParameterValue` | Adjust value per spec |
| `MissingParameter` | Add missing param |
| `ResourceNotFound` | Verify ID; suggest Describe |
| `ResourceNotFound.ClusterNotFound` | Verify ClusterId; list clusters |
| `ResourceInsufficient` | HALT — request quota increase |
| `ResourceInUse` | Use unique name/CIDR |
| `ResourcePreRunning` | RETRY (3×, 30s) — poll status; wait |
| `OperationConflict` | RETRY (3×, 30s) — wait for completion |
| `InvalidSecretKey` / `InvalidSecretId` | HALT — fix credentials |
| `RequestLimitExceeded` | RETRY (3×, exponential) — backoff |
| `InternalError` | RETRY (3×, exponential) — escalate with RequestId |
| `AddonConflict` | Check existing addons; resolve conflict |
| `QuotaExceeded` | HALT — request quota increase |

> **After use:** Verify each code exists in the official TKE API error documentation.

## Safety Gates (Destructive Operations)

Every **DeleteCluster** or irreversible operation MUST have:

1. **Explicit user confirmation** with cluster ID and name displayed
2. **Pre-backup reminder** — export namespace YAML, PVC data, CRDs before deletion
3. **Dependency check** — warn if cluster has running pods/services
4. **Post-delete verification** — poll until absent or NotFound (max 600s)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 TKE-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? |
|---|---|
| Destructive: `DeleteCluster`, `DeleteNode`, `DrainNode` | **yes** |
| Sensitive mutating: `UpdateClusterVersion`, `ModifyClusterAttribute`, `CreateClusterEndpoint` | **yes** |
| Mutating: `CreateCluster`, `AddNodeToPool`, `InstallAddon`, `DeleteAddon` | **yes** |
| Read-only: `DescribeClusters`, `DescribeClusterInstances`, `DescribeAddon` | optional |

### TKE-specific safety rules (rubric §4)

1. `DeleteCluster` — ID + Name echo; workload cascade warning (PVCs, CRDs, all namespaces); YAML export prompt
2. `DeleteNode` / `DrainNode` — node count check (>50% refuse); PDB check for critical namespaces
3. `AddNodeToPool` (batch) — capacity check; confirmation when >10% scale-up
4. `UpdateClusterVersion` — show current → target; warn one-directional; surface addon compatibility; reject minor-version skip
5. `ModifyClusterAttribute` / `CreateClusterEndpoint` — public endpoint security warning; current status display

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "abc123",
    "ClusterId": "cls-xxxxx",
    "NodePoolId": "np-xxxxx"
  }
}
```

Error responses:

```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidParameter",
      "Message": "Parameter validation failed"
    }
  }
}
```

---

## Reference Directory

- [Core Concepts](references/core-concepts.md) — TKE architecture, cluster types, networking
- [API & SDK Usage](references/api-sdk-usage.md) — TKE API operation map and SDK patterns
- [CLI Usage](references/cli-usage.md) — `tccli tke` command map and coverage gaps
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, multi-round diagnosis
- [Monitoring & Alerts](references/monitoring.md) — TKE metrics, health checks, alerting patterns
- [Integration](references/integration.md) — SDK setup, cross-skill delegation, CI/CD patterns
- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar TKE assessment
- [Enhanced Self-Healing Framework](references/enhanced-self-healing-framework.md) — Installation recovery patterns
- [Execution Environment Setup](../qcloud-skill-generator/references/execution-environment.md)

## Operational Best Practices

- **Cluster version:** Pin to a stable LTS version; test upgrades in a staging cluster first
- **Node pools:** Use separate node pools for different workload types (stateful vs stateless)
- **Networking:** Use VPC-CNI for large clusters (>500 pods per node)
- **Cost:** Use prepaid nodes for baseline capacity, pay-as-you-go for burst in autoscaling pools
- **Security:** Rotate kubeconfig credentials regularly; use CAM roles instead of static keys