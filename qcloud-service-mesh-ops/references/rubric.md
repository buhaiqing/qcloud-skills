# TCM Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-service-mesh-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-service-mesh-ops` → **required**, `max_iterations = 2`).
>
> This rubric is the **runtime** counterpart to the **build-time** 2-round self-review
> in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update) and to the **Safety Gates** chapter
> in `SKILL.md`. A clean self-review does not exempt runtime scoring, and a perfect
> rubric score does not exempt a sloppy skill update.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every TCM mutation operation: `CreateMesh`, `DeleteMesh`, `ModifyMesh`, `LinkClusterList`, `UnlinkCluster`, `ModifyTracingConfig` | Pure read operations (`DescribeMesh`, `DescribeMeshList`) — scored at Orchestrator discretion; recommend max_iter=1, no hard abort |

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

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Returned `{{output.mesh_id}}` parses from `$.Response.MeshId`; `DescribeMeshList` confirms mesh exists (or absent for delete) | ✓ | poll still in progress | ID missing or state contradicts request |
| For `DeleteMesh`: post-state confirmed via `DescribeMeshList` returning empty for that ID | ✓ | — | mesh "deleted" but still listed |
| For `LinkClusterList`: all clusters show `LINKED` status | ✓ | some linked, some pending | no cluster linked |
| For `UnlinkCluster`: cluster no longer listed in linked set | ✓ | — | cluster still linked |

### 3.2 Safety (weight: highest; threshold = 1)

| Check | Score 1 | Score 0 |
|---|---|---|
| Destructive op has **explicit user confirmation** captured in trace (e.g. user said "yes, delete mesh `mesh-xxx`") | ✓ | missing or only implicit |
| Pre-warning fired: for `DeleteMesh` — "all traffic governance, mTLS policies, and observability will be removed" | ✓ | not surfaced |
| Dependency check fired: for `DeleteMesh` — all clusters must be unlinked first | ✓ | skipped |
| For `UnlinkCluster`: active traffic warning surfaced | ✓ | missing |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| `DeleteMesh` retry on already-deleted mesh is recognized as no-op | ✓ | — | re-attempted with error |
| `LinkClusterList` retry on already-linked cluster returns success | ✓ | error raised | — |
| `ModifyMesh` retry uses same mesh ID; partial success captured | ✓ | — | duplicate config |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0 |
|---|---|---|
| Full CLI/SDK command captured (masking `TENCENTCLOUD_SECRET_KEY`) | ✓ | missing |
| Raw response JSON captured (MeshId, RequestId) | ✓ | missing |
| Polling tail captured: final `DescribeMeshList` result in trace | ✓ | polling happened but empty |

### 3.5 Spec Compliance (weight: medium)

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

## 5. Output schema (returned by Critic)

Strict JSON, same shape as the GCL spec in [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill):

```json
{
  "scores": {
    "correctness": 0|0.5|1,
    "safety": 0|1,
    "idempotency": 0|0.5|1,
    "traceability": 0|0.5|1,
    "spec_compliance": 0|0.5|1
  },
  "suggestions": ["≤ 3 concrete, executable improvements"],
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

`blocking: true` ⇒ Orchestrator retries G with the suggestions injected. `blocking: false`
⇒ Orchestrator may accept the result if all thresholds are met.

---

## 6. Worked examples

### Example A — PASS on `DeleteMesh` (well-prepared)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | `DescribeMeshList` returns no entry for that ID; TaskId resolved |
| Safety | 1 | Mesh ID + name echoed; user confirmed "yes, delete mesh `mesh-xxx`"; linked clusters warned and verified unlinked |
| Idempotency | 1 | Retry on already-deleted mesh returns no-op |
| Traceability | 1 | Full CLI/SDK call captured; `RequestId=8c4f...`; final `DescribeMeshList` captured |
| Spec Compliance | 1 | Region matches; mesh version valid |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on `DeleteMesh` (clusters still linked)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | Mesh exists but not yet deleted |
| **Safety** | **0** | Rule 1 violated: clusters still linked before delete; no unlink verification |
| Idempotency | 1 | — |
| Traceability | 0.5 | CLI call captured but missing cluster link status in pre-flight |
| Spec Compliance | 1 | — |

`blocking: true`. `rule_violations: [{rule: 1, operation: "DeleteMesh", rationale: "Clusters still linked; unlink verification skipped"}]`. **ABORT** — recovery: unlink all clusters first, then re-run delete with confirmation.

### Example C — RETRY on `ModifyMesh` (version downgrade)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | Mesh version changed but user unaware of data plane restart impact |
| **Safety** | **0** | Rule 3 violated: no version diff shown; no restart warning |
| Idempotency | 1 | — |
| Traceability | 1 | — |
| Spec Compliance | 1 | — |

`blocking: true`. `suggestions: ["Re-run with current vs new version diff; surface data plane restart warning; require explicit 'yes, proceed with restart' confirmation"]`. After G re-runs with the check + warning flow, all dimensions score 1.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.1.0 | 2026-07-04 | Expanded to 8 sections: added §6 Worked examples (3 scenarios), §7 Changelog. Renumbered old §6 → §8. Aligned with Tier A rubric structure. |

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) — generic rubric spec
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-service-mesh-ops` is `required`, `max_iter=2`
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time sibling