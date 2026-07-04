# TCM Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-service-mesh-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-service-mesh-ops` → **required**, `max_iterations = 2`).

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every TCM mutation operation: `CreateMesh`, `DeleteMesh`, `ModifyMesh`, `LinkClusterList`, `UnlinkCluster`, `ModifyTracingConfig` | Pure read operations (`DescribeMesh`, `DescribeMeshList`) — scored at Orchestrator discretion |

---

## 2. Five rubric dimensions (mandatory)

Each dimension is scored `0`, `0.5`, or `1`. Thresholds are from [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill).

| # | Dimension | Threshold | Why this threshold for TCM |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for `DeleteMesh`) | Mesh deletion without full cluster unlink leaves orphaned config |
| 2 | **Safety** | **= 1** (strict) | TCM destructive ops sever cluster connectivity; missing safety gates must abort |
| 3 | **Idempotency** | ≥ 0.5 | TCM async ops have TaskId; idempotent retry avoids orphan resources |
| 4 | **Traceability** | ≥ 0.5 | MeshId + ClusterId + RequestId are audit anchors |
| 5 | **Spec Compliance** | ≥ 0.5 | TCM version compatibility, cluster state requirements |

**Safety = 0 → ABORT immediately**. See [AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins).

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| `{{output.mesh_id}}` parses from `$.Response.MeshId`; `DescribeMeshList` confirms mesh exists (or absent for delete) | ✓ | poll still in progress | ID missing or state contradicts request |
| For `DeleteMesh`: post-state confirmed via `DescribeMeshList` returning absent | ✓ | — | mesh still listed after delete |
| For `LinkClusterList`: cluster shows in `LinkedClusterSet` with status `RUNNING` | ✓ | partial | cluster not linked |

### 3.2 Safety (threshold = 1)

| Check | Score 1 | Score 0 |
|---|---|---|
| Destructive op has **explicit user confirmation** with mesh ID and name | ✓ | missing |
| Pre-warning fired: for `DeleteMesh` — "all traffic governance, mTLS policies, and observability will be removed" | ✓ | not surfaced |
| Dependency check fired: for `DeleteMesh` — all clusters must be unlinked first | ✓ | skipped |
| For `UnlinkCluster`: active traffic warning surfaced | ✓ | missing |

### 3.3 Idempotency

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| `DeleteMesh` retry on already-deleted mesh is recognized as no-op | ✓ | — | re-attempted with error |
| `LinkClusterList` retry on already-linked cluster returns success | ✓ | error raised | — |
| `ModifyMesh` retry uses same mesh ID; partial success captured | ✓ | — | duplicate config |

### 3.4 Traceability

| Check | Score 1 | Score 0 |
|---|---|---|
| Full CLI/SDK command captured (masking `TENCENTCLOUD_SECRET_KEY`) | ✓ | missing |
| Raw response JSON captured (MeshId, RequestId) | ✓ | missing |
| Polling tail captured: final `DescribeMeshList` result in trace | ✓ | polling happened but empty |

### 3.5 Spec Compliance

| Check | Score 1 | Score 0 |
|---|---|---|
| `MeshVersion` ∈ supported versions (check `DescribeMeshList` available versions) | ✓ | unsupported version |
| Cluster state `RUNNING` before linking | ✓ | non-running cluster accepted |
| `ModifyTracingConfig`: valid tracing config format | ✓ | invalid config submitted |

---

## 4. TCM-specific safety rules

Each rule enforced by Safety dimension. Missing any rule → Safety = 0 → ABORT.

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteMesh` | **MUST** confirm mesh ID + name; **MUST** warn all clusters unlinked, mTLS/authz removed; **MUST** verify all clusters are unlinked before commit | Deleting a mesh with linked clusters orphans traffic governance; there is no soft-delete |
| 2 | `UnlinkCluster` | **MUST** warn that cluster loses mesh-side traffic management; **MUST** confirm cluster ID | Unlinking without warning can break production traffic abruptly |
| 3 | `ModifyMesh` (version) | **MUST** show current vs new MeshVersion; **MUST** warn that data plane restart may cause brief disruption | Version downgrade or config change can disrupt running services |

---

## 5. Output schema

```json
{
  "scores": {
    "correctness": 0|0.5|1,
    "safety": 0|1,
    "idempotency": 0|0.5|1,
    "traceability": 0|0.5|1,
    "spec_compliance": 0|0.5|1
  },
  "suggestions": ["≤ 3 concrete improvements"],
  "blocking": true|false,
  "rule_violations": [
    {"rule": 1, "operation": "DeleteMesh", "rationale": "Clusters still linked before delete"}
  ],
  "thresholds": {
    "correctness": 1.0,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5
  }
}
```

---

## 6. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud)
- [`prompt-templates.md`](prompt-templates.md) — G/C/O skeletons
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations)
