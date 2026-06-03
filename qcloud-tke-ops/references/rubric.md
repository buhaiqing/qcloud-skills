# TKE Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-tke-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-tke-ops` → **required**, `max_iterations = 2`).
>
> Sibling rubrics: [`qcloud-cvm-ops`](../cvm-ops/references/rubric.md), [`qcloud-cdb-ops`](../cdb-ops/references/rubric.md),
> [`qcloud-cos-ops`](../cos-ops/references/rubric.md), [`qcloud-clb-ops`](../clb-ops/references/rubric.md).
> The 5-dimension backbone is identical; only §4 product-specific safety rules differ.
> TKE adds three concerns: **K8s version upgrades are one-directional**, **cluster deletion
> cascades to all workloads**, **node drain can disrupt pod scheduling without PDB**.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| TKE mutation operations: `CreateCluster`, `DeleteCluster`, `ModifyClusterAttribute`, `CreateClusterEndpoint`, `DeleteClusterEndpoint`, `AddNodeToPool`, `DeleteNode`, `DrainNode`, `ModifyNodePoolAttribute`, `UpdateClusterVersion`, `InstallAddon`, `DeleteAddon`, `CreateClusterRouteTable` | Pure read operations (`DescribeClusters`, `DescribeClusterEndpoints`, `DescribeClusterInstances`, `DescribeClusterRouteTables`, `DescribeAddon`) — scored at Orchestrator's discretion; recommend max_iter=1 |
| Application-level K8s YAML apply (`kubectl apply -f`) — this is Kubernetes API, not TKE API | In-cluster operations (`kubectl`, `helm`, `kustomize`) — these are Kubernetes data-plane, not Tencent Cloud TKE API; not covered by this GCL pilot |

---

## Dimensions, scoring checklists, output schema, anti-patterns

The 5-dimension backbone, per-dimension checklists (§3), output schema (§5), worked examples (§6), and anti-patterns follow the exact same structure as the sibling rubrics
([`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) §2, §3, §5, §6 — verbatim identical except product-specific
API names and parameter paths). This file documents only the §4 product-specific safety
rules. The full rubric content can be assembled by merging §2–§3–§5–§6 from the CLB rubric
with §1–§4–§7–§8 below.

---

## 4. TKE-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteCluster` (any) | **Cluster ID + Name echo + explicit confirmation + workload cascade warning (PVCs, CRDs, all namespaces, Service-type LoadBalancer cleanup); confirm with the user that they have exported critical YAML/PVC data/CRDs before deletion; batch not applicable (single cluster delete)** | TKE cluster deletion is irreversible: the API server, etcd, all nodes, all PVCs, and all workloads are destroyed. There is no "recycle bin" like CDB's IsolateDBInstance. Exporting YAML is the only recovery path |
| 2 | `DeleteNode` / `DrainNode` (any) | **Node ID + instance ID echoed; check node count in the cluster before drain (if draining >50% of nodes, refuse without recurse-confirm); check PodDisruptionBudget for critical namespaces; surface `Desired/Ready node count` from `DescribeClusterInstances`** | Draining too many nodes at once can crash the cluster's pod scheduling. Without PDB, pods are evicted without guarantee of re-scheduling. The most common TKE incident: "I drained the nodes for maintenance but the API pods never came back because the PDB was `maxUnavailable: 0`" |
| 3 | `AddNodeToPool` (batch) | **Check account capacity quota (`DescribeClusterRouteTable` or `DescribeAccountQuota`); surface current node count + proposed new count; require explicit confirmation when proposed count would exceed 10% of current (scale-up risk guard)** | Node pool scale-up surprises happen when the user specifies `DesiredNodes` too large and hits the quota silently — the API returns a partial success with some nodes created and others stuck in `CREATING`. The user sees "nodes pending" and blames the cluster |
| 4 | `UpdateClusterVersion` (K8s upgrade) | **Show current K8s version → target version; warn that K8s upgrades are one-directional (downgrading requires cluster re-creation); surface any addons that may be incompatible (via `DescribeAddon`); require explicit confirmation; do NOT proceed from 1.xx → 1.xx+2 in one jump (minor version skip is blocked by API but the rule catches the intent)** | K8s version upgrades are the highest-incident TKE operation. Users skip minor versions ("jump from 1.28 to 1.30"), causing etcd data format incompatibility. Addons break silently. The skill must surface the addon compatibility list BEFORE the upgrade |
| 5 | `ModifyClusterAttribute` / `CreateClusterEndpoint` (public endpoint / ACL) | **For public-endpoint enable: warn that the cluster API server becomes publicly accessible; require explicit confirmation that node-level network ACL / IP whitelist is in place; for delete-endpoint: warn that all kubectl connections will drop; surface current `ClusterExternalEndpoint` status before any change** | Exposing a K8s API server to the public internet without IP whitelist is a security incident waiting to happen. TKE's `CreateClusterEndpoint` does not enforce IP restrictions by default — they must be set separately |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 TKE rollout: rubric (5 dimensions, 5 TKE-specific safety rules incl. cluster-delete cascade, node-drain PDB guard, version-upgrade addon compat, public-endpoint security). Adapted from `qcloud-clb-ops` rubric v1.0.0; rules 1, 2 mirror the existing TKE Safety Gates chapter, rules 3, 4, 5 are new |

## 8. See also

- [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill), [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud)
- [`prompt-templates.md`](prompt-templates.md)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations)
- Sibling rubrics: [`cvm`](../cvm-ops/references/rubric.md), [`cdb`](../cdb-ops/references/rubric.md), [`cos`](../cos-ops/references/rubric.md), [`clb`](../clb-ops/references/rubric.md)