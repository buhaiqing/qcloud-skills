# TKE Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-tke-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-tke-ops` → **required**, `max_iterations = 2`).
>
> This rubric is **self-contained** — it does NOT delegate to sibling rubrics for the
> 5-dimension backbone. Each dimension checklist is written with TKE-specific API names,
> parameter paths, and state transitions.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| TKE mutation operations: `CreateCluster`, `DeleteCluster`, `ModifyClusterAttribute`, `CreateClusterEndpoint`, `DeleteClusterEndpoint`, `AddNodeToPool`, `DeleteNode`, `DrainNode`, `ModifyNodePoolAttribute`, `UpdateClusterVersion`, `InstallAddon`, `DeleteAddon`, `CreateClusterRouteTable` | Pure read operations (`DescribeClusters`, `DescribeClusterEndpoints`, `DescribeClusterInstances`, `DescribeClusterRouteTables`, `DescribeAddon`) — scored at Orchestrator's discretion; recommend max_iter=1 |
| Application-level K8s YAML apply (`kubectl apply -f`) — this is Kubernetes API, not TKE API | In-cluster operations (`kubectl`, `helm`, `kustomize`) — these are Kubernetes data-plane, not Tencent Cloud TKE API; not covered by this GCL pilot |

---

## 2. Five rubric dimensions (mandatory)
> **TE-6:** 5-dimension skeleton → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md).


Each dimension is scored `0`, `0.5`, or `1`. Thresholds are taken from
[AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill) and are **not negotiable** —
the only exception is `correctness = 1.0` **required** for the destructive
operations listed in the per-operation table below.

| # | Dimension | Threshold | Why this threshold for TKE |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for `DeleteCluster`, `DeleteNode`/`DrainNode`, `UpdateClusterVersion`, `CreateClusterEndpoint` without IP whitelist) | Half-correct cluster state leaves orphaned CVM instances; half-correct version upgrade breaks addons |
| 2 | **Safety** | **= 1** (strict) | TKE destructive ops are irreversible (no recycle bin like CDB's IsolateDBInstance). Any missing safety step must abort |
| 3 | **Idempotency** | ≥ 0.5 | TKE has async operations (cluster creation, node pool scaling); retry with same params should not duplicate resources |
| 4 | **Traceability** | ≥ 0.5 | Every TKE call has a `RequestId`; cluster/nodepool IDs are audit-trail anchors |
| 5 | **Spec Compliance** | ≥ 0.5 | Refers to `references/cli-usage.md` / `references/core-concepts.md` constraints (K8s version matrix, node OS compatibility, networking mode × subnet CIDR) |

**Safety = 0 → ABORT immediately**, regardless of total score. See
[AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins) → `SAFETY_FAIL`.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Returned `{{output.cluster_id}}` / `{{output.node_pool_id}}` / `{{output.request_id}}` parses; `DescribeClusters` / `DescribeClusterAsGroups` confirms target exists (or is absent for delete) | ✓ | returned ID parses but final state not yet confirmed (poll still in progress) | ID / request_id missing, wrong shape, or state contradicts request |
| For `DeleteCluster`: post-state confirmed via `DescribeClusters` returning empty for that ClusterId | ✓ | — | cluster "deleted" but still listed |
| For `CreateClusterAsGroup` (node pool): returned `NodePoolId` is valid; `DescribeClusterAsGroups` shows status = `Running` | ✓ | node pool created but still in `Creating` state (poll in progress) | NodePoolId missing or creation failed |
| For `UpdateClusterVersion`: `DescribeClusters` shows `ClusterVersion` = target version after upgrade; addon status remains `Running` | ✓ | version updated but addons show non-Running state | version unchanged or addons broken |
| For `DeleteClusterInstances` (DeleteNode): removed instance IDs no longer appear in `DescribeClusterInstances` | ✓ | — | instances still listed |
| For `CreateClusterEndpoint`: `DescribeClusterEndpoints` shows new endpoint with expected type | ✓ | endpoint created but not yet accessible | endpoint missing |

### 3.2 Safety (weight: highest; threshold = 1)

This dimension audits the **Safety Gates** chapter of `SKILL.md` and the **TKE-specific safety rules** in §4 below. A single missing gate ⇒ Safety = 0.

| Check | Score 1 | Score 0 |
|---|---|---|
| Destructive op has **explicit user confirmation** captured in trace (e.g. user said "yes, delete cluster `cls-xxx`") | ✓ | missing or only implicit |
| Pre-impact-warning fired: for `DeleteCluster` — "all workloads, PVCs, CRDs, Service LoadBalancers will be destroyed"; for `DeleteNode` — "pods on these nodes will be evicted"; for `UpdateClusterVersion` — "one-directional upgrade, addon compatibility risk" | ✓ | not surfaced |
| Dependency check fired: for `DeleteCluster` — list node pools, list cluster instances; for `AddNodeToPool` — check account quota; for `DeleteNode` — check node count / PDB constraints | ✓ | skipped for batch |
| For `UpdateClusterVersion`: addon compatibility list surfaced via `DescribeClusterAttribute` before upgrade | ✓ | addon compat not checked |
| For `CreateClusterEndpoint`: public endpoint security warning surfaced; IP whitelist/ACL confirmed | ✓ | public endpoint enabled without warning |
| For `DeleteNode` / `DrainNode`: node count check (>50% of total = refuse without recurse-confirm) | ✓ | >50% drain accepted silently |
| Cluster state, node pool state, and addon state were sanity-checked against `references/core-concepts.md` (K8s version matrix, node OS compatibility) | ✓ | any param failed validation but was still submitted |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| `CreateCluster` retry after `InternalError`: same `ClusterName` + `VpcId` + `SubnetId` re-issued; `ResourceInUse` is handled as a no-op (cluster already exists) | ✓ | retry created a duplicate cluster (different ClusterId but same name) | second create returned a new cluster without checking |
| `DeleteCluster` retry: the same `ClusterId` is used; already-deleted cluster returns `ResourceNotFound` which is handled as a no-op | ✓ | second delete attempted on a deleted cluster (floods audit log) | error raised and surfaced as a real failure |
| `AddNodeToPool` (batch scale): retry after `InternalError` uses the same `DesiredNodeCount`; partial success is captured in trace | ✓ | — | second scale call doubled the node count |
| `DeleteClusterInstances` (DeleteNode): retry on already-removed instances returns `ResourceNotFound` which is handled as a no-op | ✓ | re-attempted with new error | error flood |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Full CLI command line captured (with all params, masking `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_SECRET_ID` as `<masked>`) | ✓ | only param values captured, command line missing | command reconstructed after the fact |
| Raw response JSON captured (or at minimum: `RequestId`, `ClusterId`, `NodePoolId`) | ✓ | only IDs captured | response reconstructed |
| Polling tail captured: for state-transition ops, at least the **final** `DescribeClusters` / `DescribeClusterAsGroups` call and its result are in the trace | ✓ | only initial state captured | polling happened but trace is empty |
| For batch operations (DeleteNode, AddNodeToPool): list of affected instances/nodes echoed in captured response | ✓ | — | partial success invisible |
| `tccli` exit code captured | ✓ | — | missing |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0 |
|---|---|---|
| `ClusterType` ∈ {`MANAGED_TKE`, `INDEPENDENT`} per Tencent Cloud TKE docs | ✓ | invalid type submitted |
| `ClusterVersion` ∈ supported K8s versions per `references/core-concepts.md`; no minor-version skip (e.g., 1.28 → 1.30) | ✓ | unsupported or skipped version submitted |
| `InstanceType` valid per TKE node pool spec and available in target zone | ✓ | invalid or unavailable instance type accepted |
| `ContainerRuntime` ∈ {`containerd`} (docker is deprecated for TKE) | ✓ | docker (deprecated) accepted |
| For `DeleteClusterInstances`: `DeleteMode` ∈ {`TERMINATE`, `RETAIN`} per API spec | ✓ | invalid delete mode |
| For `CreateClusterEndpoint`: endpoint type matches cluster type (VPC-CNI vs GR networking) | ✓ | incompatible endpoint type |

---

## 4. TKE-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteCluster` (any) | **Cluster ID + Name echo + explicit confirmation + workload cascade warning (PVCs, CRDs, all namespaces, Service-type LoadBalancer cleanup); confirm with the user that they have exported critical YAML/PVC data/CRDs before deletion; batch not applicable (single cluster delete)** | TKE cluster deletion is irreversible: the API server, etcd, all nodes, all PVCs, and all workloads are destroyed. There is no "recycle bin" like CDB's IsolateDBInstance. Exporting YAML is the only recovery path |
| 2 | `DeleteNode` / `DrainNode` (any) | **Node ID + instance ID echoed; check node count in the cluster before drain (if draining >50% of nodes, refuse without recurse-confirm); check PodDisruptionBudget for critical namespaces; surface `Desired/Ready node count` from `DescribeClusterInstances`** | Draining too many nodes at once can crash the cluster's pod scheduling. Without PDB, pods are evicted without guarantee of re-scheduling. The most common TKE incident: "I drained the nodes for maintenance but the API pods never came back because the PDB was `maxUnavailable: 0`" |
| 3 | `AddNodeToPool` (batch) | **Check account capacity quota (`DescribeUserQuota` or `DescribeClusterRouteTable`); surface current node count + proposed new count; require explicit confirmation when proposed count would exceed 10% of current (scale-up risk guard)** | Node pool scale-up surprises happen when the user specifies `DesiredNodes` too large and hits the quota silently — the API returns a partial success with some nodes created and others stuck in `CREATING`. The user sees "nodes pending" and blames the cluster |
| 4 | `UpdateClusterVersion` (K8s upgrade) | **Show current K8s version → target version; warn that K8s upgrades are one-directional (downgrading requires cluster re-creation); surface any addons that may be incompatible (via `DescribeClusterAttribute --Attribute ClusterLevel/Addons`); require explicit confirmation; do NOT proceed from 1.xx → 1.xx+2 in one jump (minor version skip is blocked by API but the rule catches the intent)** | K8s version upgrades are the highest-incident TKE operation. Users skip minor versions ("jump from 1.28 to 1.30"), causing etcd data format incompatibility. Addons break silently. The skill must surface the addon compatibility list BEFORE the upgrade |
| 5 | `ModifyClusterAttribute` / `CreateClusterEndpoint` (public endpoint / ACL) | **For public-endpoint enable: warn that the cluster API server becomes publicly accessible; require explicit confirmation that node-level network ACL / IP whitelist is in place; for delete-endpoint: warn that all kubectl connections will drop; surface current `ClusterExternalEndpoint` status before any change** | Exposing a K8s API server to the public internet without IP whitelist is a security incident waiting to happen. TKE's `CreateClusterEndpoint` does not enforce IP restrictions by default — they must be set separately |

**Anti-patterns (for Critic awareness):**
- ❌ **Version jump without addon compat check** — TKE-specific: `UpdateClusterVersion` from 1.28 to 1.30 (skipping 1.29) is allowed by the API but breaks addons
- ❌ **DeleteCluster without YAML export** — TKE-specific: cluster deletion is irreversible; YAML export is the only recovery path
- ❌ **Drain >50% nodes without PDB check** — TKE-specific: draining too many nodes at once can crash scheduling
- ❌ **CreateClusterEndpoint with no IP whitelist** — public K8s API server without ACL is a security incident
- ❌ **ContainerRuntime=docker** — docker is deprecated on TKE; must use containerd

---

## 5. Output schema (for Critic trace parsing)

All TKE API responses follow the standard Tencent Cloud structure:

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

For batch operations (DeleteNode, AddNodeToPool), capture the list of affected IDs.

---

## 6. Worked examples (for Critic calibration)

### Example 1: DeleteCluster (score: 1, 1, 1, 0.5, 1)

Generator performed:
- Confirmed `cls-abc123` (`prod-cluster`) with user → user said "yes"
- Warned: deletes nodes, PVCs, CRDs, all namespaces; asked user to export YAML
- Executed: `tccli tke DeleteCluster --ClusterId "cls-abc123" --InstanceDeleteMode "TerminateAndDestroy"`
- Polled: DescribeClusters returned NotFound after 300s
- Captured: full CLI command (masked creds), raw JSON response, polling tail, exit code

**Critic scoring:**
| Dimension | Score | Reason |
|---|---|---|
| Correctness | 1 | Cluster confirmed absent via DescribeClusters |
| Safety | 1 | User confirmed, cascade warning fired, YAML export prompted |
| Idempotency | 1 | Second call handled ResourceNotFound as no-op |
| Traceability | 0.5 | Full trace captured but missing pre-delete DescribeClusters baseline |
| Spec Compliance | 1 | InstanceDeleteMode = "TerminateAndDestroy" is correct |

### Example 2: UpdateClusterVersion without addon check (SAFETY_FAIL)

Generator performed:
- Confirmed: current 1.28 → target 1.30 with user approval
- Executed: `tccli tke ModifyCluster --ClusterId "cls-abc" --ClusterVersion "1.30.0"`
- **Did NOT call DescribeClusterAttribute to surface addon compatibility**
- Polled: cluster upgraded successfully but coredns addon broken

**Critic scoring:**
| Dimension | Score | Reason |
|---|---|---|
| Safety | **0** | §4 rule 4 violated: addon compatibility list NOT surfaced before upgrade ⇒ **ABORT** |
| Correctness | 0.5 | Version updated but addon broken = partial success |
| Idempotency | 1 | Single call, no retry |
| Traceability | 0.5 | Command captured, but no addon list in trace |
| Spec Compliance | 0.5 | Acceptable K8s version but skipped 1.29 |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.1.0 | 2026-06-04 | Phase 1 TKE rollout: rubric (5 dimensions, 5 TKE-specific safety rules). Initial version delegated 5-dimension checklists to `qcloud-clb-ops` |
| 1.2.0 | 2026-06-04 | Made rubric self-contained: inlined 5-dimension checklists (scoring tables, output schema, worked examples, anti-patterns) with TKE-specific API names and parameters. Removed CLB cross-reference dependency |
| 1.2.1 | 2026-06-18 | Tier A conformance: merged Anti-patterns into §4 safety rules; renumbered to canonical 8 sections (was 9) |

## 8. See also

- [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill), [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud)
- [`prompt-templates.md`](prompt-templates.md)
- [SKILL.md §Quality Gate (GCL)](../SKILL.md#quality-gate-gcl)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations)