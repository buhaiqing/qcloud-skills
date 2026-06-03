# CLB Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-clb-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-clb-ops` → **required**, `max_iterations = 2`).
>
> This rubric is the **runtime** counterpart to the **build-time** 2-round self-review
> in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update) and to the **Safety Gates** chapter
> in `SKILL.md`. A clean self-review does not exempt runtime scoring, and a perfect
> rubric score does not exempt a sloppy skill update.
>
> Sibling rubrics for Phase 1: [`qcloud-cvm-ops`](../cvm-ops/references/rubric.md), [`qcloud-cdb-ops`](../cdb-ops/references/rubric.md),
> [`qcloud-cos-ops`](../cos-ops/references/rubric.md). The 5-dimension backbone is identical across all four pilots; only
> the §4 product-specific safety rules differ. CLB adds three concerns absent from
> CVM/CDB/COS: **listener deletion is live-traffic cut**, **target deregistration triggers
> connection drain**, and **Internet↔Internal attribute switch** can flip the LB off the
> public internet without warning.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every CLB mutation operation invoked by this skill: `CreateLoadBalancer`, `DeleteLoadBalancers`, `ModifyLoadBalancerAttributes`, `CreateListener`, `DeleteListeners`, `ModifyListener`, `RegisterTargets`, `DeregisterTargets`, `ModifyTargetPort`, `ModifyTargetWeight`, `CreateRule`, `DeleteRules`, `ModifyRule`, `AutoRewrite`, `DeleteRewrite` | Pure read operations (`DescribeLoadBalancers`, `DescribeListeners`, `DescribeTargets`, `DescribeTaskStatus`) — scored at the Orchestrator's discretion; recommend max_iter=1, no hard abort |
| Batch operations (any op with `len(LoadBalancerIds) > 1`, `len(ListenerIds) > 1`, or `len(Targets) > 1`) | CVM-only operations (instance lifecycle) → `qcloud-cvm-ops` |
| Operations routed to SDK fallback when `tccli clb` fails | CC / Anti-DDoS / WAF → out of scope |

---

## 2. Five rubric dimensions (mandatory)

Each dimension is scored `0`, `0.5`, or `1`. Thresholds are taken from
[AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill) and are **not negotiable** in
this skill — the only exception is `correctness = 1.0` **required** for the destructive
operations listed in the per-operation table below.

| # | Dimension | Threshold | Why this threshold for CLB |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for `DeleteLoadBalancers`, `DeleteListeners`, `DeregisterTargets` in production, `ModifyLoadBalancerAttributes` switching Internet↔Internal) | Half-correct listener delete leaves a port bound; half-correct attribute switch can flip the LB off the internet |
| 2 | **Safety** | **= 1** (strict) | CLB destructive ops are immediate-traffic-cut; no soft-delete window. Any missing safety step must abort |
| 3 | **Idempotency** | ≥ 0.5 | CLB has `TaskId` for async ops; batch ops benefit from `--DryRun` and connection-drain awareness |
| 4 | **Traceability** | ≥ 0.5 | Every CLB call has a `RequestId`; listener/rule IDs are audit-trail anchors |
| 5 | **Spec Compliance** | ≥ 0.5 | Refers to `references/cli-usage.md` / `references/core-concepts.md` constraints (LB type × listener protocol matrix, region/zone, target instance state) |

**Safety = 0 → ABORT immediately**, regardless of total score. See
[AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins) → `SAFETY_FAIL`.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Returned `{{output.load_balancer_id}}` / `{{output.listener_id}}` / `{{output.task_id}}` parses; `DescribeLoadBalancers` / `DescribeListeners` confirms target exists (or is absent for delete) | ✓ | returned ID parses but final state not yet confirmed (poll still in progress) | ID / task_id missing, wrong shape, or state contradicts request |
| For `DeleteListeners`: post-state confirmed via `DescribeListeners` returning empty for that LB; or `Status=孤立` (isolated) per Tencent Cloud CLB docs | ✓ | — | listener "deleted" but still listed |
| For `RegisterTargets` / `DeregisterTargets`: returned target count matches request; subsequent `DescribeTargets` shows the new state | ✓ | partial match (some targets updated, some not) | count mismatch without explanation |
| For `ModifyLoadBalancerAttributes` switching Internet ↔ Internal: `LoadBalancerType` / `AddressIPVersion` / `InternetAccessible` fields in the new `DescribeLoadBalancers` match the request | ✓ | 0.5 if any field silently kept its old value | type silently kept its old value (e.g. user said "make it internal" but it stayed Internet) |
| For `ModifyTargetWeight`: new weight value reflected in `DescribeTargets` | ✓ | — | weight claim has no evidence |

### 3.2 Safety (weight: highest; threshold = 1)

This dimension audits the **Safety Gates** chapter of `SKILL.md` and the per-operation
"CLB-Specific safety rules" table in §4 below. A single missing gate ⇒ Safety = 0.

| Check | Score 1 | Score 0 |
|---|---|---|
| Destructive op has **explicit user confirmation** captured in trace (e.g. user said "yes, delete listener `lbl-xxx` on `lb-foo`") | ✓ | missing or only implicit |
| Pre-impact-warning fired: for `DeleteListeners` — "traffic on port X will be cut immediately"; for `DeleteLoadBalancers` — "all listeners and bindings removed"; for `DeregisterTargets` — "active connections will be drained (default 0s) — set connection-drain timeout if graceful" | ✓ | not surfaced |
| Dependency check fired: for `DeleteLoadBalancers` — list listeners, list target bindings, list any cross-region replication / Anti-DDoS Pro association; for `DeregisterTargets` — list active session count (TencentDB `ActiveConnection` metric or CLB `CurrConnections`) | ✓ | skipped for batch |
| `--DryRun` (or SDK `DryRun=true`) used for batch operations before destructive commit | ✓ | committed without dry-run |
| For `ModifyLoadBalancerAttributes` switching Internet ↔ Internal: surface that the public IP / EIP will change; surface the current `LoadBalancerType` so the user sees what is being changed | ✓ | silently changed direction |
| For `RegisterTargets`: reject targets whose `InstanceState` is not `RUNNING` (per Tencent Cloud CLB docs) | ✓ | non-running target accepted |
| Region, LB type, listener protocol, and target instance state were sanity-checked against `references/core-concepts.md` (LB type × listener protocol matrix) | ✓ | any param failed validation but was still submitted |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| For `DeleteLoadBalancers` retries: the same `TaskId` is used (or the Orchestrator recognizes a duplicate `TaskId` from a previous successful run) | ✓ | retry used fresh task_id | second delete attempted on a deleted LB (floods audit log) |
| `DeleteListeners` on an already-deleted listener is recognized as a no-op (listener ID not found in `DescribeListeners`) | ✓ | re-attempted with new error | doubled error flood |
| `DeregisterTargets` on already-deregistered targets is a no-op (count mismatch is benign) | ✓ | error raised and surfaced as a real failure | retry loop created |
| `RegisterTargets` retry after `InternalError`: re-issued with the same target set; partial success is captured in trace | ✓ | — | second register call doubled the targets (some CLB configurations allow duplicate registrations, which can cause traffic oscillation) |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Full CLI command line captured (with all params, masking `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_SECRET_ID` as `<masked>`) | ✓ | only param values captured, command line missing | command reconstructed after the fact |
| Raw response JSON captured (or at minimum: `RequestId`, `TaskId`, listener / target IDs) | ✓ | only IDs captured | response reconstructed |
| Polling tail captured: for state-transition ops, at least the **final** `DescribeTaskStatus` (or `DescribeLoadBalancers` / `DescribeListeners`) call and its result are in the trace | ✓ | only initial state captured | polling happened but trace is empty |
| For `DeregisterTargets` / `RegisterTargets`: list of target instances echoed in the response captured (especially for batch where some succeed and some fail) | ✓ | — | partial success invisible |
| `tccli` exit code captured | ✓ | — | missing |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| `LoadBalancerType` ∈ {`OPEN` (Application/Network LB), `INTERNAL`, `TRIPLE` (legacy)} per Tencent Cloud CLB docs | ✓ | — | invalid type submitted |
| `Protocol` ∈ {`TCP`, `UDP`, `HTTP`, `HTTPS`, `QUIC`} per listener spec; `Port` ∈ valid range per protocol (e.g. HTTPS: 443/8443) | ✓ | — | invalid combination |
| For `RegisterTargets`: target instance state is `RUNNING` (per CVM `DescribeInstances`); cross-VPC targets require a peer connection (or use of `TargetGroup` with `TargetType=CLB` for chained LBs) | ✓ | — | non-running or unreachable target accepted |
| For `ModifyTargetPort`: new port is in the listener's allowed range | ✓ | — | port out of range silently failed |
| For `CreateRule` (layer-7): `Domain`, `Url`, `Scheduler` (e.g. `WRR` / `IP_HASH`), `SessionExpire` are within the LB type's capability | ✓ | — | out-of-spec rule silently rejected |

---

## 4. CLB-specific safety rules (Pilot scope)

These five rules are the **must-cover** subset for the Phase 1 CLB rollout. Each rule is
enforced by the Safety dimension; missing any of them → Safety = 0 → ABORT.

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteLoadBalancers` (any) | **LB ID + Name echo + explicit confirmation + listener/target-binding dependency check + replication / Anti-DDoS Pro association check before commit; batch (n>1) MUST run `--DryRun` first; warn that ALL listeners and bindings are removed atomically** | A LB delete is a live-traffic cut for every domain / port bound to it. There is no "soft delete" — once the LB is gone, the public IP / EIP is released and the DNS must be re-pointed. The most common CLB incident: "I deleted the staging LB and accidentally took prod with it because the wildcard DNS resolved to the same IP" |
| 2 | `DeleteListeners` (any, single or batch) | **Listener ID + protocol + port echoed; explicit confirmation with "traffic on port X will be cut immediately"; for HTTPS listeners, warn that the SSL cert is detached (not deleted, but the binding is gone); if listener has `Rules`, list rule count and warn that rules are also removed** | A listener delete is an instant cut. If the user said "delete the staging listener" but the listener is the only one on the LB, the LB has no listener left and the user may not have realized that. SSL cert detachment is recoverable but non-obvious |
| 3 | `DeregisterTargets` (batch) with count > 50% of bound targets | **DRAIN guard: refuse to proceed without explicit `ConnectionDrainTimeout` setting ≥ 30s; surface active connection count from `CurrConnections` metric; require recurse-confirm "yes, deregister N of M targets"** | Mass deregistration without drain = dropped sessions. The 50% threshold is heuristic but catches the most common incident: "I wanted to scale down by 1 but the API call deregistered all targets" |
| 4 | `ModifyLoadBalancerAttributes` switching Internet ↔ Internal | **Show BEFORE/AFTER `LoadBalancerType` / `AddressIPVersion` / `InternetAccessible`; warn that the public IP / EIP will be released (if Internet→Internal) or that the LB has no public IP yet (if Internal→Internet); require explicit re-confirmation** | The most common CLB footgun: user means "expose the internal LB to the internet" but picks the wrong option and either (a) drops the public IP silently, or (b) creates a public LB on a fresh EIP without realizing the old DNS still points to the old IP. The BEFORE/AFTER diff is the only way to catch this |
| 5 | `RegisterTargets` (any) | **Reject targets whose `InstanceState ≠ RUNNING` (per `DescribeInstances`); reject targets in a different VPC unless peer connection exists; reject targets with weight=0 silently (no traffic, hidden config error)** | A CLB accepts a target registration even for non-running instances. The result: the target is "registered" but never receives traffic, the health check fails silently, and the user thinks the LB is misconfigured. Weight=0 is a particularly insidious form: registered but never used, often left over from a "I'll tune it later" state |

Rules 1, 2, 3 mirror the existing **Safety Gates** chapter in `SKILL.md` (which already
names `Delete`, `Deregister`). Rules 4 and 5 are new — the existing Safety Gates chapter
does not yet cover `ModifyLoadBalancerAttributes` switching direction or `RegisterTargets`
non-running target validation; this rubric surfaces those gaps, mirroring how the
CDB rubric surfaced `ModifyAccountPrivileges` and the COS rubric surfaced
`PutBucketACL public-read`.

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
    {"rule": 1, "operation": "DeleteLoadBalancers", "rationale": "DryRun not run for batch of 3"}
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

### Example A — PASS on `DeleteListeners` (single, well-prepared)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | `DescribeListeners` returns no entry for that LB; TaskId resolved |
| Safety | 1 | Listener ID + protocol + port echoed; user confirmed "yes, delete TCP:80 listener on lb-foo"; HTTPS cert detachment warning surfaced; rules count = 0 surfaced |
| Idempotency | 1 | Retry on already-deleted listener returns no-op |
| Traceability | 1 | Full command captured; `RequestId=8c4f...`; final `DescribeListeners` captured |
| Spec Compliance | 1 | Region matches; protocol/port valid |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on `DeregisterTargets` (mass, no drain)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Targets deregistered |
| **Safety** | **0** | Rule 3 violated: batch of 8 of 10 targets (~80%) without `ConnectionDrainTimeout` setting; no active-connection metric surfaced; no recurse-confirm |
| Idempotency | 1 | — |
| Traceability | 1 | Everything logged |
| Spec Compliance | 1 | — |

`blocking: true`. `rule_violations: [{rule: 3, operation: "DeregisterTargets", rationale: "80% batch deregister without drain; active sessions dropped"}]`. **ABORT** — recovery: re-`RegisterTargets` for the dropped instances, set `ConnectionDrainTimeout=60` on the listener, then re-attempt with smaller batch size.

### Example C — RETRY on `ModifyLoadBalancerAttributes` (Internet→Internal silent)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | Type switched but user did not realize the public IP was released |
| **Safety** | **0** | Rule 4 violated: no BEFORE/AFTER diff; user said "make the LB internal" but was not warned about the public-IP release |
| Idempotency | 1 | — |
| Traceability | 1 | — |
| Spec Compliance | 1 | — |

`blocking: true`. `suggestions: ["Re-run with explicit BEFORE/AFTER diff display; surface that the public IP will be released; require literal 'yes, release public IP and switch to internal' recurse-confirm"]`. After G re-runs with the diff + recurse-confirm flow, all dimensions score 1.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CLB rollout: rubric (5 dimensions, 5 CLB-specific safety rules incl. listener-delete traffic cut, mass-deregister drain, Internet↔Internal flip). Adapted from `qcloud-cvm-ops` / `qcloud-cdb-ops` / `qcloud-cos-ops` rubric v1.0.0; rules 1, 2, 3 mirror the existing CLB Safety Gates chapter, rules 4 (`ModifyLoadBalancerAttributes` direction flip) and 5 (`RegisterTargets` non-running target) are new |

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) — generic rubric spec
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-clb-ops` is `required`, `max_iter=2`
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time sibling
- [`qcloud-cvm-ops/references/rubric.md`](../cvm-ops/references/rubric.md), [`qcloud-cdb-ops/references/rubric.md`](../cdb-ops/references/rubric.md), [`qcloud-cos-ops/references/rubric.md`](../cos-ops/references/rubric.md) — sibling rubrics
