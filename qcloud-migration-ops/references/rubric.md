# Migration Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-migration-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-migration-ops` → **required**, `max_iterations = 2`).
>
> This rubric is the **runtime** counterpart to the **build-time** 2-round self-review
> in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update) and to the **Safety Gates** chapter
> in `SKILL.md`. A clean self-review does not exempt runtime scoring, and a perfect
> rubric score does not exempt a sloppy skill update.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every migration mutation operation invoked by this skill: `RegisterMigrationTask`, `ModifyMigrationTaskStatus`, `DeregisterMigrationTask` | Pure read operations (`ListMigrationTask`, `DescribeMigrationTask`) — scored at the Orchestrator's discretion; recommend max_iter=1, no hard abort |
| Dual-path execution (tccli primary, SDK fallback) | — |
| Data loss risk operations (`DeregisterMigrationTask`) | — |

---

## 2. Five rubric dimensions (mandatory)
> **TE-6:** 5-dimension skeleton → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md).


Each dimension is scored `0`, `0.5`, or `1`. Thresholds are taken from
[AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill) and are **not negotiable** in
this skill — the only exception is `correctness = 1.0` **required** for destructive
operations listed in the per-operation table below.

| # | Dimension | Threshold | Why this threshold for Migration |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for `DeregisterMigrationTask` in production) | Half-correct deregister may leave orphaned migration state; task may still be running |
| 2 | **Safety** | **= 1** (strict) | Migration operations affect data-in-transit; deregister removes migration metadata and may affect ongoing transfers. Any missing safety step must abort |
| 3 | **Idempotency** | ≥ 0.5 | Migration tasks have async status; careful retry handling needed |
| 4 | **Traceability** | ≥ 0.5 | Every migration call has a `RequestId`; task IDs are audit-trail anchors |
| 5 | **Spec Compliance** | ≥ 0.5 | Refers to `references/cli-usage.md` / `references/core-concepts.md` constraints (task type, source/target config) |

**Safety = 0 → ABORT immediately**, regardless of total score. See
[AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins) → `SAFETY_FAIL`.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Returned `{{output.task_id}}` parses; `DescribeMigrationTask` confirms target exists (or is absent for deregister) | ✓ | returned ID parses but final state not yet confirmed (poll still in progress) | ID / task_id missing, wrong shape, or state contradicts request |
| For `DeregisterMigrationTask`: post-state confirmed via `ListMigrationTask` returning absent for that ID | ✓ | — | task "deregistered" but still listed |
| For `ModifyMigrationTaskStatus`: task status confirmed via `DescribeMigrationTask` | ✓ | partial (status changed but not to expected value) | status unchanged |
| For `RegisterMigrationTask`: task created and poll confirms READY state | ✓ | — | task created but not in expected state |

### 3.2 Safety (weight: highest; threshold = 1)

This dimension audits the **Safety Gates** chapter of `SKILL.md` and the per-operation
"Migration-Specific safety rules" table in §4 below. A single missing gate ⇒ Safety = 0.

| Check | Score 1 | Score 0 |
|---|---|
| Destructive op has **explicit user confirmation** captured in trace (e.g. user said "yes, deregister task `task-xxx`") | ✓ | missing or only implicit |
| Pre-impact-warning fired: for `DeregisterMigrationTask` — "migration metadata will be removed, any in-progress data transfer will be abandoned"; for `ModifyMigrationTaskStatus` — warn about status change implications | ✓ | not surfaced |
| Dependency/state check fired: for `DeregisterMigrationTask` — verify task is complete or stopped; for `ModifyMigrationTaskStatus` — confirm target state is valid | ✓ | skipped |
| For `RegisterMigrationTask`: source and target configs validated; network reachability confirmed | ✓ | not validated |
| Task type and region validated against `references/core-concepts.md` | ✓ | any param failed validation but was still submitted |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| For `DeregisterMigrationTask` retries: the same task ID is used; already-deregistered task recognized as no-op | ✓ | retry used fresh ID | second deregister attempted on deleted task |
| `ModifyMigrationTaskStatus` retry after `OperationDenied.TaskRunning`: handle appropriately; partial success captured | ✓ | — | status changed to unexpected value |
| `RegisterMigrationTask` retry after `InvalidParameter.TaskNameExists`: use different name; partial success captured | ✓ | — | duplicate task created |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Full CLI/SDK call captured (with all params, masking `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_SECRET_ID` as `<masked>`) | ✓ | only param values captured, call missing | call reconstructed after the fact |
| Raw response JSON captured (or at minimum: `RequestId`, `TaskId`, task status) | ✓ | only IDs captured | response reconstructed |
| Polling tail captured: for state-transition ops, at least the **final** `DescribeMigrationTask` call and its result are in the trace | ✓ | only initial state captured | polling happened but trace is empty |
| Exit code captured | ✓ | — | missing |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| `TaskType` is valid per MSP spec (host migration, database migration, storage migration) | ✓ | — | invalid task type submitted |
| `SrcNode` and `DstNode` configs are valid JSON/structure | ✓ | — | invalid config format |
| Region is valid and supports migration | ✓ | — | invalid region submitted |
| Source credentials/network are accessible | ✓ | — | unreachable source accepted |

---

## 4. Migration-specific safety rules (Pilot scope)

These three rules are the **must-cover** subset for the Phase 1 Migration rollout. Each rule is
enforced by the Safety dimension; missing any of them → Safety = 0 → ABORT.

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeregisterMigrationTask` (any) | **Task ID + Name echoed + explicit confirmation + status check (task must be COMPLETED or STOPPED, not RUNNING) + data loss warning (in-progress transfer will be abandoned)** | Deregistering a running migration task abandons the data transfer mid-process; the target may be left in an inconsistent state with partial data |
| 2 | `ModifyMigrationTaskStatus` (any) | **Task ID echoed + explicit confirmation of target status + current status echoed + warning about implications of status change** | Changing migration task status (e.g., from RUNNING to STOPPED) mid-transfer has similar implications to deregister; the user must understand the consequences |
| 3 | `RegisterMigrationTask` (any) | **Source and target configs validated; network reachability confirmed; quota check performed** | Registering a migration task with invalid configs or unreachable source will fail after queue time; validating upfront prevents wasted migration window |

Rules 1 and 2 mirror the existing **Safety Gates** chapter in `SKILL.md` (which already
names `DeregisterMigrationTask`, `ModifyMigrationTaskStatus`). Rule 3 is new — the existing Safety Gates chapter
does not yet cover `RegisterMigrationTask` pre-validation; this rubric surfaces that gap.

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
    {"rule": 1, "operation": "DeregisterMigrationTask", "rationale": "No status check; task is RUNNING"}
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

### Example A — PASS on `DeregisterMigrationTask` (well-prepared)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Task deregistered; `ListMigrationTask` confirms absent |
| Safety | 1 | Task ID + name echoed; user confirmed "yes, deregister task `task-xxx`"; status verified as COMPLETED; data loss warning surfaced |
| Idempotency | 1 | Retry on already-deregistered task returns no-op |
| Traceability | 1 | Full CLI call captured; `RequestId=8c4f...`; final `ListMigrationTask` captured |
| Spec Compliance | 1 | Region matches; task type valid |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on `DeregisterMigrationTask` (running task)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Task deregistered |
| **Safety** | **0** | Rule 1 violated: no status check performed; task was RUNNING when deregistered; data loss warning not surfaced |
| Idempotency | 1 | — |
| Traceability | 1 | Everything logged |
| Spec Compliance | 1 | — |

`blocking: true`. `rule_violations: [{rule: 1, operation: "DeregisterMigrationTask", rationale: "No status check; task was RUNNING when deregistered; in-progress transfer abandoned"}]`. **ABORT** — recovery: stop the running task first, wait for completion, then re-attempt deregister.

### Example C — RETRY on `RegisterMigrationTask` (invalid source config)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | Task registration failed due to invalid source config |
| Safety | 1 | Source config validation performed upfront |
| Idempotency | 1 | — |
| Traceability | 1 | Everything logged |
| **Spec Compliance** | **0** | Rule 3 violated: source config not validated before submission |

`blocking: true`. `suggestions: ["Re-run with validated source config; verify network reachability; check quota before registration"]`. After G validates source config and retries, all dimensions score 1.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-04 | Initial Migration rubric: 3 rules (DeregisterMigrationTask data loss guard, ModifyMigrationTaskStatus implications warning, RegisterMigrationTask pre-validation). Dual-path execution (tccli + SDK). Adapted from `qcloud-clb-ops` rubric structure. |

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) — generic rubric spec
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-migration-ops` is `required`, `max_iter=2`
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time sibling
