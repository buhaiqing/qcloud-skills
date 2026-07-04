# CI/CD Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-cicd-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-cicd-ops` → **required**, `max_iterations = 2`).
>
> This rubric is the **runtime** counterpart to the **build-time** 2-round self-review
> in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update) and to the **Safety Gates** chapter
> in `SKILL.md`. A clean self-review does not exempt runtime scoring, and a perfect
> rubric score does not exempt a sloppy skill update.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every CI/CD mutation operation invoked by this skill: `CreatePipeline`, `DeletePipeline`, `StartPipeline`, `StopPipeline` | Pure read operations (`DescribePipelines`, `DescribeBuildLogs`) — scored at the Orchestrator's discretion; recommend max_iter=1, no hard abort |
| Pipeline trigger operations (`StartPipeline`) | Build log retrieval when pipeline is not running |
| SDK-only execution path (no tccli available) | — |

---

## 2. Five rubric dimensions (mandatory)

Each dimension is scored `0`, `0.5`, or `1`. Thresholds are taken from
[AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill) and are **not negotiable** in
this skill — the only exception is `correctness = 1.0` **required** for destructive
operations listed in the per-operation table below.

| # | Dimension | Threshold | Why this threshold for CI/CD |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for `DeletePipeline`, `StopPipeline` in production) | Half-correct pipeline delete leaves orphaned webhooks; half-correct stop may leave build in inconsistent state |
| 2 | **Safety** | **= 1** (strict) | CI/CD destructive ops cancel active builds and remove automation; no soft-delete window. Any missing safety step must abort |
| 3 | **Idempotency** | ≥ 0.5 | CI/CD has `TaskId` for async ops; retry safety depends on operation type |
| 4 | **Traceability** | ≥ 0.5 | Every CI/CD call has a `RequestId`; pipeline/build IDs are audit-trail anchors |
| 5 | **Spec Compliance** | ≥ 0.5 | Refers to `references/sdk-code-examples.md` constraints (pipeline name, region, build trigger conditions) |

**Safety = 0 → ABORT immediately**, regardless of total score. See
[AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins) → `SAFETY_FAIL`.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Returned `{{output.pipeline_id}}` / `{{output.build_id}}` parses; `DescribePipelines` confirms target exists (or is absent for delete) | ✓ | returned ID parses but final state not yet confirmed (poll still in progress) | ID / task_id missing, wrong shape, or state contradicts request |
| For `DeletePipeline`: post-state confirmed via `DescribePipelines` returning empty for that ID | ✓ | — | pipeline "deleted" but still listed |
| For `StartPipeline`: build ID returned and poll confirms build started | ✓ | build started but status unclear | no build_id returned |
| For `StopPipeline`: pipeline status confirmed as STOPPED or build cancelled | ✓ | partial (some stages stopped, some not) | build still running after stop |

### 3.2 Safety (weight: highest; threshold = 1)

This dimension audits the **Safety Gates** chapter of `SKILL.md` and the per-operation
"CI/CD-Specific safety rules" table in §4 below. A single missing gate ⇒ Safety = 0.

| Check | Score 1 | Score 0 |
|---|---|
| Destructive op has **explicit user confirmation** captured in trace (e.g. user said "yes, delete pipeline `pl-xxx`") | ✓ | missing or only implicit |
| Pre-impact-warning fired: for `DeletePipeline` — "automation will be removed, running builds cancelled"; for `StopPipeline` — "running build will be aborted, partial artifacts discarded" | ✓ | not surfaced |
| Dependency check fired: for `DeletePipeline` — list running builds, dependent webhooks/triggers; for `StopPipeline` — confirm build is actually running | ✓ | skipped |
| For `StartPipeline`: confirm pipeline exists and is in a startable state | ✓ | attempted to start non-startable pipeline |
| Region and pipeline name validated against `references/sdk-code-examples.md` | ✓ | any param failed validation but was still submitted |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| For `DeletePipeline` retries: the same `TaskId` is used (or the Orchestrator recognizes a duplicate from a previous successful run) | ✓ | retry used fresh task_id | second delete attempted on a deleted pipeline |
| `DeletePipeline` on an already-deleted pipeline is recognized as a no-op | ✓ | re-attempted with new error | doubled error flood |
| `StopPipeline` on an already-stopped build is a no-op | ✓ | error raised as real failure | retry loop created |
| `StartPipeline` retry after `OperationDenied.PipelineRunning`: wait for completion then retry; partial success captured | ✓ | — | second trigger call created duplicate build |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Full SDK call captured (with all params, masking `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_SECRET_ID` as `<masked>`) | ✓ | only param values captured, call missing | call reconstructed after the fact |
| Raw response JSON captured (or at minimum: `RequestId`, `TaskId`, pipeline/build IDs) | ✓ | only IDs captured | response reconstructed |
| Polling tail captured: for state-transition ops, at least the **final** `DescribePipelines` / `DescribeBuildLogs` call and its result are in the trace | ✓ | only initial state captured | polling happened but trace is empty |
| `tccli` exit code captured | ✓ | — | missing |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Pipeline name length and character constraints respected per `references/sdk-code-examples.md` | ✓ | — | invalid name submitted |
| Region is valid for the account | ✓ | — | invalid region submitted |
| For `StartPipeline`: source branch/repo exists and is accessible | ✓ | — | invalid branch/repo accepted |
| Build trigger conditions met (e.g. source commit exists, credentials valid) | ✓ | — | trigger accepted for non-existent commit |

---

## 4. CI/CD-specific safety rules (Pilot scope)

These three rules are the **must-cover** subset for the Phase 1 CI/CD rollout. Each rule is
enforced by the Safety dimension; missing any of them → Safety = 0 → ABORT.

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeletePipeline` (any) | **Pipeline ID + Name echo + explicit confirmation + running-build dependency check + webhook/trigger orphan warning; warn that ALL automation is removed atomically** | A pipeline delete cancels all running builds and removes all webhooks and triggers. There is no "soft delete" — once the pipeline is gone, the automation is irrecoverable unless backed up |
| 2 | `StopPipeline` (any) | **Build ID echoed; explicit confirmation with "running build will be aborted, partial artifacts discarded"; verify build is actually in progress** | Stopping a pipeline mid-build discards all intermediate artifacts. If the user did not intend to stop (e.g. confused with "pause for debugging"), the abort is disruptive and may require re-running the entire build |
| 3 | `StartPipeline` (any) | **Pipeline ID + Name echoed; confirm pipeline exists and is in a startable state (not SUSPENDED or DELETED); warn about potential duplicate builds if previous build is still running** | Starting an already-running pipeline creates duplicate builds; the user should confirm they want to run concurrent builds |

Rules 1 and 2 mirror the existing **Safety Gates** chapter in `SKILL.md` (which already
names `DeletePipeline`, `StopPipeline`). Rule 3 is new — the existing Safety Gates chapter
does not yet cover `StartPipeline` duplicate-build protection; this rubric surfaces that gap.

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
    {"rule": 1, "operation": "DeletePipeline", "rationale": "No explicit confirmation captured in trace"}
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

### Example A — PASS on `DeletePipeline` (well-prepared)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | `DescribePipelines` returns no entry for that ID; TaskId resolved |
| Safety | 1 | Pipeline ID + name echoed; user confirmed "yes, delete pipeline `pl-xxx`"; running builds listed and warned; webhook orphan warning surfaced |
| Idempotency | 1 | Retry on already-deleted pipeline returns no-op |
| Traceability | 1 | Full SDK call captured; `RequestId=8c4f...`; final `DescribePipelines` captured |
| Spec Compliance | 1 | Region matches; pipeline name valid |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on `StopPipeline` (no confirmation)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Build stopped |
| **Safety** | **0** | Rule 2 violated: no explicit confirmation; build ID not echoed; no warning about partial artifacts |
| Idempotency | 1 | — |
| Traceability | 1 | Everything logged |
| Spec Compliance | 1 | — |

`blocking: true`. `rule_violations: [{rule: 2, operation: "StopPipeline", rationale: "No explicit confirmation captured; no artifact discard warning"}]`. **ABORT** — recovery: re-run with explicit confirmation + artifact warning.

### Example C — RETRY on `StartPipeline` (duplicate build)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | Build started but user did not realize previous build was still running |
| **Safety** | **0** | Rule 3 violated: no check for already-running build; no warning about duplicate builds |
| Idempotency | 0.5 | Duplicate build created; partial success visible |
| Traceability | 1 | — |
| Spec Compliance | 1 | — |

`blocking: true`. `suggestions: ["Re-run with running-build check; surface duplicate-build warning; require literal 'yes, run concurrent builds' confirmation if previous build is active"]`. After G re-runs with the check + warning flow, all dimensions score 1.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-04 | Initial CI/CD rubric: 3 rules (DeletePipeline automation removal, StopPipeline abort, StartPipeline duplicate-build guard). SDK-only skill (no tccli available). Adapted from `qcloud-clb-ops` rubric structure. |

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) — generic rubric spec
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-cicd-ops` is `required`, `max_iter=2`
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time sibling
