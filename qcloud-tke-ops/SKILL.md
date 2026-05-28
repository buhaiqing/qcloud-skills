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
  version: "1.0.0"
  last_updated: "2026-05-21"
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
| 1.0.1 | 2026-05-28 | Update K8s version to 1.30.0; Fix polling script timeout handling; Change container runtime to containerd; Add TCR integration guide; Clarify NodePoolId extraction |
| 1.0.0 | 2026-05-21 | Initial release — cluster lifecycle, node pools, addons, dual-path |

---

## Execution Flows (Agent-Readable)

### Operation: CreateCluster

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI installed | `tccli tke help CreateCluster` | Exit code 0 | Document CLI install |
| SDK available | `python3 -c "from tencentcloud.tke import tke_client"` | No ImportError | `pip install tencentcloud-sdk-python-tke` |
| Credentials | Check env vars | Non-empty values | HALT; user configures |
| VPC exists | `tccli vpc DescribeVpcs --VpcId {{user.vpc_id}}` | VPC in Available state | Delegate to `qcloud-vpc-ops` |
| Subnet exists | `tccli vpc DescribeSubnets --SubnetIds {{user.subnet_id}}` | Subnet exists | Delegate to `qcloud-vpc-ops` |
| SecurityGroup | `tccli vpc DescribeSecurityGroups --SecurityGroupIds {{user.security_group_id}}` | Security group exists | Delegate to `qcloud-vpc-ops` |
| Quota | `tccli tke DescribeUserQuota` | Sufficient cluster quota | HALT; user raises quota |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli tke CreateCluster \
  --ClusterType "MANAGED_TKE" \
  --ClusterName "{{user.cluster_name}}" \
  --ClusterDescription "Managed TKE cluster" \
  --ClusterVersion "1.30.0" \
  --ClusterOs "tlinux3.1x86_64" \
  --ClusterOsType "CUSTOM" \
  --VpcId "{{user.vpc_id}}" \
  --SubnetId "{{user.subnet_id}}" \
  --SecurityGroup "{{user.security_group_id}}" \
  --ContainerRuntime "containerd" \
  --NodeNameMode "{{user.cluster_name}}-%i" \
  --ClusterLevel "L5" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: TKE CreateCluster"""
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tke import tke_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = tke_client.TkeClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.CreateClusterRequest()
        req.ClusterType = "MANAGED_TKE"
        req.ClusterName = os.environ.get("CLUSTER_NAME")
        req.ClusterOs = "tlinux3.1x86_64"
        req.ClusterVersion = "1.30.0"
        req.VpcId = os.environ.get("VPC_ID")
        req.SubnetId = os.environ.get("SUBNET_ID")
        resp = client.CreateCluster(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Read `{{output.cluster_id}}` from `$.Response.ClusterId`
2. Poll DescribeClusters until ClusterStatus = `Running` or timeout (600s):

```bash
for i in $(seq 1 60); do
  STATUS=$(tccli tke DescribeClusters --Region {{env.TENCENTCLOUD_REGION}} --ClusterId "{{output.cluster_id}}" | jq -r '.Response.Clusters[0].ClusterStatus')
  [ "$STATUS" = "Running" ] && break
  sleep 10
done
# Check timeout
if [ "$STATUS" != "Running" ]; then
  echo "[ERROR] Timeout waiting for cluster Running status (current: $STATUS)"
  exit 1
fi
```

3. Report cluster ID and endpoints to user
4. On failure, go to **Failure Recovery**

#### TCR Integration (Optional)

If using **Tencent Container Registry (TCR)** for container images:

```bash
# Associate TCR instance with cluster
tccli tke EnableClusterAudit \
  --ClusterId "{{output.cluster_id}}" \
  --Region {{env.TENCENTCLOUD_REGION}}

# Configure image pull secrets for TCR private registry
tccli tke DescribeClusterSecurity \
  --ClusterId "{{output.cluster_id}}" \
  --Region {{env.TENCENTCLOUD_REGION}} > /tmp/kubeconfig.yaml

# Set image pull secret in kubeconfig (manual step shown)
kubectl --kubeconfig=/tmp/kubeconfig.yaml create secret docker-registry tcr-secret \
  --docker-server={{user.tcr_registry}} \
  --docker-username={{user.tcr_username}} \
  --docker-password={{user.tcr_password}} \
  --docker-email={{user.email}}
```

**Note:** For full TCR operations, use `qcloud-tcr-ops` skill.

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|---------------|-------------|---------|--------------|-------------|
| `InvalidParameter` | 0–1 | — | Fix args per API spec; retry once | `[ERROR] InvalidParameter: Request parameter invalid → Check CreateCluster API spec → Retry` |
| `ResourceInUse` | 0 | — | HALT | `[ERROR] ResourceInUse: Name or CIDR already in use → Use unique name/CIDR → Retry` |
| `ResourceInsufficient.Vpc` | 0 | — | HALT | `[ERROR] VPC resource insufficient → Verify VPC/Subnet available → Check IP pool` |
| `QuotaExceeded` | 0 | — | HALT | `[ERROR] Cluster quota exceeded → Request quota increase` |
| `InvalidSecretKey` / `InvalidSecretId` | 0 | — | HALT | `[ERROR] Credential invalid → Verify env vars → Retry` |
| `OperationConflict` | 3 | 30s | Wait for conflicting op; retry | `⚠️ Another operation in progress → Retrying after completion...` |
| `RequestLimitExceeded` / 429 | 3 | exponential | Back off; respect rate limit | `⚠️ Rate limit reached → Retrying in {backoff}s` |
| `InternalError` / 5xx | 3 | 2s, 4s, 8s | Retry; HALT with RequestId if persists | `[ERROR] InternalError → Retry → Escalate with RequestId: {{output.request_id}}` |

### Operation: DescribeClusters

#### Execution

```bash
# List all clusters (JSON output)
tccli tke DescribeClusters --Region {{env.TENCENTCLOUD_REGION}} --Offset 0 --Limit 100

# Filter by cluster ID
tccli tke DescribeClusters --Region {{env.TENCENTCLOUD_REGION}} --ClusterId "{{user.cluster_id}}"
```

```python
# SDK equivalent
req = models.DescribeClustersRequest()
req.ClusterId = os.environ.get("CLUSTER_ID")
req.Offset, req.Limit = 0, 100
resp = client.DescribeClusters(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Present to User

| Field | JSON Path | Notes |
|-------|-----------|-------|
| ClusterId | `$.Response.Clusters[0].ClusterId` | Plain text (cls-xxx) |
| ClusterName | `$.Response.Clusters[0].ClusterName` | Human-readable |
| ClusterStatus | `$.Response.Clusters[0].ClusterStatus` | Running/Creating/Abnormal/Deleting |
| ClusterVersion | `$.Response.Clusters[0].ClusterVersion` | K8s version (e.g., 1.28.3) |
| ClusterType | `$.Response.Clusters[0].ClusterType` | MANAGED_TKE / INDEPENDENT |
| TotalNodeNum | `$.Response.Clusters[0].TotalNodeNum` | Node count |
| CreatedTime | `$.Response.Clusters[0].CreatedTime` | ISO 8601 timestamp |

### Operation: CreateClusterAsGroup (Node Pool)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster exists | `tccli tke DescribeClusters --ClusterId {{user.cluster_id}}` | Cluster in Running state | HALT |
| Instance type valid | `tccli tke DescribeClusterAsGroupOption` or CVM catalog | Instance type available | Suggest alternative type |

#### Execution — CLI

```bash
tccli tke CreateClusterAsGroup \
  --ClusterId "{{user.cluster_id}}" \
  --NodePoolName "{{user.node_pool_name}}" \
  --InstanceType "{{user.instance_type}}" \
  --SubnetId "{{user.subnet_id}}" \
  --VpcId "{{user.vpc_id}}" \
  --LaunchRemotePort 22 \
  --DesiredPodNum 0 \
  --MaxPodNum 256 \
  --NodeOs "tlinux3.1x86_64" \
  --NodeOsType "CUSTOM" \
  --AutoscalingStatus "DISABLED" \
  --MaxNum 10 \
  --MinNum 1 \
  --DeleteOption "RELEASE_INVOKE" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK

```python
req = models.CreateClusterAsGroupRequest()
req.ClusterId = os.environ.get("CLUSTER_ID")
req.NodePoolName = os.environ.get("NODE_POOL_NAME")
req.InstanceType = os.environ.get("INSTANCE_TYPE", "S5.MEDIUM8")
req.SubnetId = os.environ.get("SUBNET_ID")
req.VpcId = os.environ.get("VPC_ID")
req.MaxNum = 10
req.MinNum = 1
req.AutoscalingStatus = "DISABLED"
req.NodeOs = "tlinux3.1x86_64"
resp = client.CreateClusterAsGroup(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Read `{{output.node_pool_id}}` from CreateClusterAsGroup response:
   ```bash
   NODE_POOL_ID=$(tccli tke CreateClusterAsGroup ... | jq -r '.Response.NodePoolId')
   ```
   Or from Python SDK:
   ```python
   output.node_pool_id = resp.NodePoolId  # e.g., "np-xxxxxxxx"
   ```
2. Poll DescribeClusterAsGroups until NodePoolStatus = `Running` (max 300s)
3. Verify node count matches MinNum

#### Failure Recovery

| Error | Max retries | Agent Action | UX Feedback |
|-------|-------------|--------------|-------------|
| `ResourceNotFound.ClusterNotFound` | 0 | HALT | `[ERROR] Cluster not found → Verify ClusterId` |
| `ResourceInCreation` | 3 | Backoff 10s; retry | `⚠️ Cluster still initializing → Retrying...` |
| `InvalidInstanceType` | 0 | HALT | `[ERROR] Instance type invalid → Check available types` |

### Operation: DeleteCluster

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of cluster `{{user.cluster_name}}` (`{{user.cluster_id}}`)
- **MUST** warn: deletes all nodes, pods, and cluster data; remind user to backup important namespaces
- **MUST** check: no active applications running; pods in Running or Succeeded state
- **MUST** check: node pools are scaled down to 0 or delete first

#### Execution — CLI

```bash
tccli tke DeleteCluster \
  --ClusterId "{{user.cluster_id}}" \
  --InstanceDeleteMode "TerminateAndDestroy" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK

```python
req = models.DeleteClusterRequest()
req.ClusterId = os.environ.get("CLUSTER_ID")
req.InstanceDeleteMode = "TerminateAndDestroy"
resp = client.DeleteCluster(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Poll DescribeClusters until cluster returns NotFound or ClusterStatus = `Deleting` → absent (max 600s)
2. Verify CVM instances are terminated
3. Verify VPC/Subnet resources released (or remain for reuse)

#### Failure Recovery

| Error | Max retries | Agent Action | UX Feedback |
|-------|-------------|--------------|-------------|
| `ResourcePreRunning` | 3, 30s | Wait; retry | `⚠️ Cluster has active operations → Waiting for completion...` |
| `OperationConflict` | 3, 30s | Wait; retry | `⚠️ Another operation in progress → Retrying...` |
| `InternalError` | 3, exponential | Retry; HALT with RequestId | `[ERROR] InternalError → Escalate with RequestId: {{output.request_id}}` |

### Operation: InstallComponents (Addon Management)

#### Execution — CLI

```bash
# List available addons
tccli tke DescribeClusterAttribute \
  --ClusterId "{{user.cluster_id}}" \
  --Attribute "ClusterLevel/Addons"

# Install an addon
tccli tke InstallComponents \
  --ClusterId "{{user.cluster_id}}" \
  --Components '[{"ComponentName":"metrics-server", "ComponentVersion":"3.8.4"}]'
```

#### Post-execution Validation

1. Verify addon status is `Running` via DescribeClusterAttribute
2. Confirm addon pods are Ready in the cluster

#### Failure Recovery

| Error | Max retries | Agent Action | UX Feedback |
|-------|-------------|--------------|-------------|
| `AddonConflict` | 0 | HALT | `[ERROR] Addon already installed or conflicting → Check existing addons` |
| `AddonNotSupport` | 0 | HALT | `[ERROR] Addon not supported in this cluster version → Upgrade cluster` |
| `InternalError` | 3 | Retry | `[ERROR] InternalError → Retry or escalate with RequestId` |

---

## Error Code Reference (TKE-Specific)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter; retry with correct value |
| `InvalidParameterValue` | Parameter value out of range | No | Adjust value per API spec |
| `MissingParameter` | Required parameter missing | No | Add missing parameter |
| `ResourceNotFound` | Target cluster/resource not found | No | Verify ID; suggest Describe |
| `ResourceNotFound.ClusterNotFound` | TKE cluster does not exist | No | Verify ClusterId; list clusters |
| `ResourceInsufficient` | Quota exceeded | No | HALT; suggest quota increase |
| `ResourceInUse` | Resource name/CIDR already used | No | Use unique name/CIDR |
| `ResourcePreRunning` | Resource not yet ready | Yes (3x, 30s) | Wait; poll status; retry |
| `OperationConflict` | Concurrent operation conflict | Yes (3x, 30s) | Wait; retry after completion |
| `InvalidSecretKey` / `InvalidSecretId` | Credential invalid | No | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit exceeded | Yes (3x) | Exponential backoff |
| `InternalError` | Server-side error | Yes (3x) | Retry; escalate with RequestId |
| `AddonConflict` | Addon already installed or conflict | No | Check existing addons |
| `QuotaExceeded` | Cluster quota exceeded | No | HALT; request quota increase |

> **After use:** Verify each code exists in the official TKE API error documentation.

## Safety Gates (Destructive Operations)

Every **DeleteCluster** or irreversible operation MUST have:

1. **Explicit user confirmation** with cluster ID and name displayed
2. **Pre-backup reminder** — export namespace YAML, PVC data, CRDs before deletion
3. **Dependency check** — warn if cluster has running pods/services
4. **Post-delete verification** — poll until absent or NotFound (max 600s)

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