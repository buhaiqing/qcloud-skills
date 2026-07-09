# API Gateway GCL Rubric

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-apigw-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-apigw-ops` → **required**, `max_iterations = 2`).

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every API Gateway mutation operation invoked by this skill: `CreateService`, `CreateApi`, `ModifyApi`, `DeleteApi`, `DeleteService`, `ReleaseService` (to `release`), `BindSubDomain`, `CreateUsagePlan`, `BindSecretIds`, `BindEnvironment` | Pure read operations (`DescribeServicesStatus`, `DescribeApisStatus`, `DescribeServiceReleaseVersion`) — scored at the Orchestrator's discretion; recommend max_iter=1, no hard abort |
| Dual-path execution (tccli primary, SDK fallback) | — |
| Live-traffic risk operations (`ReleaseService` to `release`, `DeleteService`, `DeleteApi`) | — |

---

## 2. Five rubric dimensions (mandatory)

Each dimension is scored `0`, `0.5`, or `1`. Thresholds are taken from
[AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill). Correctness = 1.0 is **required**
for destructive operations (DeleteService, DeleteApi).

| # | Dimension | Threshold | Why this threshold for API Gateway |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for destructive ops) | Half-correct delete may leave orphaned APIs / live bindings |
| 2 | **Safety** | **= 1** (strict) | Deletes break clients; release routes production traffic |
| 3 | **Idempotency** | ≥ 0.5 | API Gateway resources have async status; retry carefully |
| 4 | **Traceability** | ≥ 0.5 | Every call has `RequestId`; resource IDs are audit anchors |
| 5 | **Spec Compliance** | ≥ 0.5 | Refers to `references/cli-usage.md` / `references/core-concepts.md` |

**Safety = 0 → ABORT immediately**, regardless of total score.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Returned `{{output.service_id}}` / `{{output.api_id}}` parses; describe confirms exists | ✓ | ID parses but state not yet confirmed | ID missing, wrong shape |
| For `DeleteApi`: post-state confirmed via `DescribeApisStatus` absent | ✓ | — | API "deleted" but still listed |
| For `DeleteService`: all child APIs verified absent | ✓ | partial | service still present |
| For `ReleaseService`: release version confirmed via `DescribeServiceReleaseVersion` | ✓ | partial | release not reflected |

### 3.2 Safety (weight: highest; threshold = 1)

| Check | Score 1 | Score 0 |
|---|---|---|
| Destructive op has **explicit user confirmation** captured (service/api ID + name echoed) | ✓ | missing or implicit |
| For `DeleteService` — warning that ALL child APIs destroyed; `SkipVerification=0` kept | ✓ | skipped verification |
| For `DeleteApi` — warning about client breakage; verify not serving live traffic | ✓ | not surfaced |
| For `ReleaseService` (release) — environment + change note confirmed with user | ✓ | not confirmed |
| Credentials masked in trace | ✓ | credential leaked |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| For `DeleteApi` retries: same API ID; already-deleted recognized as no-op | ✓ | retry fresh ID | second delete on deleted API |
| `CreateApi` retry after `InvalidParameterValue`: reuse existing | ✓ | — | duplicate created |
| `BindSecretIds` retry: idempotent bind | ✓ | — | duplicate bind error |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Full CLI/SDK call captured (masking credentials) | ✓ | only params | reconstructed |
| Raw response JSON captured (RequestId, resource ID) | ✓ | only IDs | reconstructed |
| Polling tail captured for state-transition ops | ✓ | only initial | empty |
| Exit code captured | ✓ | — | missing |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| ServiceName / ApiName valid per API Gateway spec | ✓ | — | invalid submitted |
| Region valid and supports API Gateway | ✓ | — | invalid region |
| RequestConfig / ServiceConfig well-formed JSON | ✓ | — | malformed struct |

---

## 4. API Gateway-specific safety rules

These rules are the **must-cover** subset. Each is enforced by the Safety dimension; missing any → Safety = 0 → ABORT.

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteService` | **Service ID + Name echoed + explicit confirmation + `SkipVerification=0` (verification ON) + total-destruction warning** | Deletes all APIs and release history irreversibly |
| 2 | `DeleteApi` | **API ID + service echoed + explicit confirmation + live-traffic check + client-breakage warning** | All clients calling the API get 404/5xx |
| 3 | `ReleaseService` (to `release`) | **Environment + change note echoed + explicit confirmation + production-impact warning** | Routes live production traffic |

---

## 5. Output schema (returned by Critic)

Strict JSON, same shape as [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill):

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
    {"rule": 1, "operation": "DeleteService", "rationale": "SkipVerification not kept at 0"}
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

## 6. Worked examples

### Example A — PASS on `DeleteApi`

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | API deleted; `DescribeApisStatus` confirms absent |
| Safety | 1 | API ID + service echoed; user confirmed; not serving live traffic; breakage warned |
| Idempotency | 1 | Retry on deleted API returns no-op |
| Traceability | 1 | Full CLI call + RequestId captured |
| Spec Compliance | 1 | Region valid |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on `DeleteService`

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Service deleted |
| **Safety** | **0** | Rule 1 violated: `SkipVerification` set to 1 without user ack; child APIs destroyed silently |
| Idempotency | 1 | — |
| Traceability | 1 | Everything logged |
| Spec Compliance | 1 | — |

`blocking: true`. `rule_violations: [{rule: 1, operation: "DeleteService", rationale: "SkipVerification=1 bypassed safety check"}]`. **ABORT** — recovery: keep `SkipVerification=0` and re-confirm with user.

### Example C — RETRY on `CreateApi` (service missing)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | API creation failed — service not found |
| Safety | 1 | Pre-flight validation performed |
| Idempotency | 1 | — |
| Traceability | 1 | Everything logged |
| **Spec Compliance** | **0** | Rule 3 violated: service not validated before submission |

`blocking: true`. `suggestions: ["Create service first or verify existing service ID"]`. After G creates service and retries, all dimensions score 1.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-09 | Initial API Gateway rubric: 3 rules (service delete guard, API delete guard, release-to-release confirmation). Dual-path execution. Covers service/API lifecycle + usage plan + custom domain. |

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-apigw-ops` is `required`, `max_iter=2`
- [`prompt-templates.md`](prompt-templates.md)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations)
