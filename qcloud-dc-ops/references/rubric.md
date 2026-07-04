# DC Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-dc-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-dc-ops` → **required**, `max_iterations = 2`).
>
> This rubric is the **runtime** counterpart to the **build-time** 2-round self-review
> in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update) and to the **Safety Gates** chapter
> in `SKILL.md`. A clean self-review does not exempt runtime scoring, and a perfect
> rubric score does not exempt a sloppy skill update.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every DC mutation operation invoked by this skill: `CreateDirectConnect`, `DeleteDirectConnect`, `CreateDirectConnectTunnel`, `DeleteDirectConnectTunnel`, `CreateDirectConnectGateway`, `DeleteDirectConnectGateway` | Pure read operations (`DescribeDirectConnects`, `DescribeDirectConnectTunnels`, `DescribeDirectConnectGateways`) — scored at the Orchestrator's discretion; recommend max_iter=1, no hard abort |
| Dual-path execution (tccli primary, SDK fallback) | — |
| Physical DC deletion (requires offline coordination) | — |

---

## 2. Five rubric dimensions (mandatory)

Each dimension is scored `0`, `0.5`, or `1`. Thresholds are taken from
[AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill) and are **not negotiable** in
this skill — the only exception is `correctness = 1.0` **required** for destructive
operations listed in the per-operation table below.

| # | Dimension | Threshold | Why this threshold for DC |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for `DeleteDirectConnect`, `DeleteDirectConnectTunnel`, `DeleteDirectConnectGateway` in production) | Half-correct DC delete leaves orphaned tunnels; half-correct gateway delete may break routing |
| 2 | **Safety** | **= 1** (strict) | DC destructive ops require physical coordination and affect live connections; any missing safety step must abort |
| 3 | **Idempotency** | ≥ 0.5 | DC has async provisioning; tunnel/gateway dependencies require careful retry handling |
| 4 | **Traceability** | ≥ 0.5 | Every DC call has a `RequestId`; DC/tunnel/gateway IDs are audit-trail anchors |
| 5 | **Spec Compliance** | ≥ 0.5 | Refers to `references/cli-usage.md` / `references/core-concepts.md` constraints (bandwidth, region, network type) |

**Safety = 0 → ABORT immediately**, regardless of total score. See
[AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins) → `SAFETY_FAIL`.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Returned `{{output.dc_id}}` / `{{output.tunnel_id}}` / `{{output.gateway_id}}` parses; `Describe*` confirms target exists (or is absent for delete) | ✓ | returned ID parses but final state not yet confirmed (poll still in progress) | ID / task_id missing, wrong shape, or state contradicts request |
| For `DeleteDirectConnect`: post-state confirmed via `DescribeDirectConnects` returning absent | ✓ | — | DC "deleted" but still listed |
| For `DeleteDirectConnectTunnel`: tunnel absent in `DescribeDirectConnectTunnels` | ✓ | — | tunnel still listed after delete |
| For `DeleteDirectConnectGateway`: gateway absent in `DescribeDirectConnectGateways` | ✓ | — | gateway still listed after delete |

### 3.2 Safety (weight: highest; threshold = 1)

This dimension audits the **Safety Gates** chapter of `SKILL.md` and the per-operation
"DC-Specific safety rules" table in §4 below. A single missing gate ⇒ Safety = 0.

| Check | Score 1 | Score 0 |
|---|---|
| Destructive op has **explicit user confirmation** captured in trace (e.g. user said "yes, delete DC `dc-xxx`") | ✓ | missing or only implicit |
| Pre-impact-warning fired: for `DeleteDirectConnect` — "physical disconnection required, all tunnels will be removed"; for `DeleteDirectConnectTunnel` — "tunnel connection will be cut immediately" | ✓ | not surfaced |
| Dependency check fired: for `DeleteDirectConnect` — list tunnels, verify all deleted first; for `DeleteDirectConnectGateway` — list associated CCN/VPN connections | ✓ | skipped |
| For `DeleteDirectConnectTunnel`: confirm DC is in AVAILABLE state | ✓ | attempted on non-available DC |
| For `DeleteDirectConnectGateway`: confirm no CCN attachments or VPN gateway dependencies | ✓ | attempted with active dependencies |
| Region, bandwidth, and network type validated against `references/core-concepts.md` | ✓ | any param failed validation but was still submitted |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| For `DeleteDirectConnect` retries: the same DC ID is used; already-deleted DC recognized as no-op | ✓ | retry used fresh ID | second delete attempted on deleted DC |
| `DeleteDirectConnectTunnel` on already-deleted tunnel is recognized as a no-op | ✓ | re-attempted with error | doubled error flood |
| `DeleteDirectConnectGateway` on already-deleted gateway is a no-op | ✓ | error raised as real failure | retry loop created |
| `CreateDirectConnect` retry after `OperationDenied.DCInUse`: handle appropriately; partial success captured | ✓ | — | second create created duplicate DC |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Full CLI/SDK call captured (with all params, masking `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_SECRET_ID` as `<masked>`) | ✓ | only param values captured, call missing | call reconstructed after the fact |
| Raw response JSON captured (or at minimum: `RequestId`, `TaskId`, DC/tunnel/gateway IDs) | ✓ | only IDs captured | response reconstructed |
| Polling tail captured: for state-transition ops, at least the **final** `Describe*` call and its result are in the trace | ✓ | only initial state captured | polling happened but trace is empty |
| Exit code captured | ✓ | — | missing |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| `Bandwidth` within allowed range per account quota and DC type | ✓ | — | invalid bandwidth submitted |
| `Region` is valid and supports DC | ✓ | — | invalid region submitted |
| `NetworkType` ∈ {`VPC`, `BM`} per DC spec | ✓ | — | invalid network type submitted |
| Access point ID is valid and available | ✓ | — | invalid access point accepted |

---

## 4. DC-specific safety rules (Pilot scope)

These three rules are the **must-cover** subset for the Phase 1 DC rollout. Each rule is
enforced by the Safety dimension; missing any of them → Safety = 0 → ABORT.

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteDirectConnect` (any) | **DC ID + Name echoed + explicit confirmation + tunnel dependency check (all tunnels must be deleted first) + physical disconnection warning; require online coordination if DC state is AVAILABLE** | A Direct Connect delete requires physical disconnection coordination. If the user deletes the DC while it's still active, they may be billed for unused connections and need on-site intervention to restore service |
| 2 | `DeleteDirectConnectTunnel` (any) | **Tunnel ID echoed + explicit confirmation with "connection will be cut immediately"; verify DC is in AVAILABLE state before deletion** | Deleting a tunnel while the DC is in a transitional state can leave the tunnel in an inconsistent state; the tunnel must be fully provisioned before deletion |
| 3 | `DeleteDirectConnectGateway` (any) | **Gateway ID echoed + explicit confirmation + dependency check (no CCN attachments, no VPN gateway associations)** | Deleting a gateway with active CCN attachments or VPN associations will break routing for all connected networks; the dependencies must be cleaned up first |

Rules 1, 2, 3 mirror the existing **Safety Gates** chapter in `SKILL.md` (which already
names `DeleteDirectConnect`, `DeleteDirectConnectTunnel`, `DeleteDirectConnectGateway`).

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
    {"rule": 1, "operation": "DeleteDirectConnect", "rationale": "Tunnel dependency check not performed"}
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

### Example A — PASS on `DeleteDirectConnectTunnel` (well-prepared)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Tunnel deleted; `DescribeDirectConnectTunnels` confirms absent |
| Safety | 1 | Tunnel ID echoed; user confirmed "yes, delete tunnel `dtunnel-xxx`"; DC state verified as AVAILABLE |
| Idempotency | 1 | Retry on already-deleted tunnel returns no-op |
| Traceability | 1 | Full CLI call captured; `RequestId=8c4f...`; final `DescribeTunnels` captured |
| Spec Compliance | 1 | Region matches; bandwidth valid |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on `DeleteDirectConnect` (no tunnel check)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | DC deleted |
| **Safety** | **0** | Rule 1 violated: tunnel dependency check not performed; tunnels still exist when DC deleted |
| Idempotency | 1 | — |
| Traceability | 1 | Everything logged |
| Spec Compliance | 1 | — |

`blocking: true`. `rule_violations: [{rule: 1, operation: "DeleteDirectConnect", rationale: "Tunnel dependency check not performed; tunnels still exist"}]`. **ABORT** — recovery: delete all tunnels first, then re-attempt DC deletion.

### Example C — RETRY on `DeleteDirectConnectGateway` (active CCN)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | Gateway deletion attempted but failed due to active CCN attachment |
| **Safety** | **0** | Rule 3 violated: no dependency check for CCN attachments; attempted delete with active dependencies |
| Idempotency | 1 | — |
| Traceability | 1 | — |
| Spec Compliance | 1 | — |

`blocking: true`. `suggestions: ["Re-run after detaching CCN from gateway; verify no VPN associations exist; confirm gateway is not serving as next-hop for any route tables"]`. After G detaches CCN and retries, all dimensions score 1.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-04 | Initial DC rubric: 3 rules (DeleteDirectConnect physical coordination, DeleteTunnel state check, DeleteGateway dependency check). Dual-path execution (tccli + SDK). Adapted from `qcloud-clb-ops` rubric structure. |

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) — generic rubric spec
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-dc-ops` is `required`, `max_iter=2`
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time sibling
