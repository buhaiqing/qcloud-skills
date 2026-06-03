# TKE GCL Prompt Templates

> Prompt skeletons for the **Generator (G)**, **Critic (C)**, and **Orchestrator (O)**
> of the `qcloud-tke-ops` skill, instantiated from
> [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill).
>
> The G/C/O backbone is identical across all Phase 1 pilots (see
> [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full template).
> This file documents only the **CLB → TKE delta**: namespace, per-operation
> augmentation in §4, and TKE-specific anti-patterns.

---

## 1. Generator prompt template — TKE delta

Replace the CLB template's header block with:

```text
You are the Generator for the qcloud-tke-ops skill (Tencent Cloud TKE operations).
- PRIMARY: tccli tke <subcommand> ...  (verify with `tccli tke help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-tke; namespace:
  from tencentcloud.tke.v20180525 import tke_client, models
```

Variables: `user.cluster_id`, `user.node_pool_id`, `user.node_id`, `user.k8s_version`,
`user.addon_name`, `user.desired_nodes`; outputs: `$.Response.ClusterId`, `TaskId`.

Pre-flight for `UpdateClusterVersion`: call `DescribeAddon` first and surface
addon-compatibility list. Pre-flight for `DeleteCluster`: export YAML via
`kubectl get all -A -o yaml`.

---

## 2. Critic prompt template — TKE delta

Same as CLB template, with scoring rule replaced:

- TKE-specific rule checks (rubric §4): rules 1 (`DeleteCluster`), 2 (`DeleteNode`/`DrainNode`),
  3 (`AddNodeToPool` batch), 4 (`UpdateClusterVersion`), 5 (`ModifyClusterAttribute` /
  `CreateClusterEndpoint` public endpoint).

---

## 3. Orchestrator prompt template — TKE delta

Same as CLB template. TKE-specific abort conditions:

- (a) `UpdateClusterVersion` version jump (1.xx → 1.xx+2) without addon-compat check ⇒ ABORT
- (b) `DeleteCluster` without YAML export ⇒ ABORT

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteCluster` | rule 1: Cluster ID + Name echo; workload cascade warning; YAML export prompt; dependency check (LoadBalancer Services, CRDs, PVCs) |
| `DeleteNode` / `DrainNode` | rule 2: Node ID echo; node count check (>50% refuse); PDB check for critical namespaces; surface Desired/Ready count |
| `AddNodeToPool` (batch) | rule 3: account capacity check; surface current + proposed count; confirmation when >10% of current |
| `UpdateClusterVersion` | rule 4: show current → target version; warn one-directional; surface addon compatibility list; reject minor-version skip |
| `ModifyClusterAttribute` / `CreateClusterEndpoint` | rule 5: warn public endpoint security; require explicit confirmation; surface current endpoint status |

---

## 5. TKE-specific anti-patterns

- ❌ **Version jump without addon compat check** — TKE-specific: `UpdateClusterVersion`
  from 1.28 to 1.30 (skipping 1.29) is allowed by the API but breaks addons
- ❌ **DeleteCluster without YAML export** — TKE-specific: cluster deletion is
  irreversible; YAML export is the only recovery path
- ❌ **Drain >50% nodes without PDB check** — TKE-specific: draining too many nodes
  at once can crash scheduling

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 TKE rollout: templates (5 rules, version-upgrade addon-compat guard, node-drain PDB guard, public-endpoint security) |