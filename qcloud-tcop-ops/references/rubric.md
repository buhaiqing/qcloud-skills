# TCOP GCL Rubric

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-tcop-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-tcop-ops` → **optional**, `max_iterations = 1`).
>
> TCOP is a **read-only advisory** skill (`sdk-only`, no `tccli` support). GCL validates
> SDK correctness and recommendation accuracy; no destructive operations are invoked
> by this skill.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every TCOP analysis operation invoked by this skill: `DescribeCostAnalysis`, `DescribeRightSizingRecommendations`, `DescribeIdleResources`, `DescribeWasteAnalysis`, `DescribeSavingsPlanCoverage`, `DescribeArchitectureAssessment`, `GenerateOptimizationReport`, `DescribeOptimizationReport` | Direct resource mutations (resize, stop, release) — delegate to `qcloud-cvm-ops`, `qcloud-cdb-ops`, `qcloud-clb-ops`, etc. |
| Read-only optimization recommendations presented as **proposals** | Any execution of a recommendation without explicit delegation to the owning product skill |
| Well-Architected read-only assessment invoked by `qcloud-well-architected-review` | Well-Architected write remediation — owned by the relevant product skill |
| Cost/waste data rendered with credential masking | Sharing cost data with unauthorized contexts or exposing credential values |

If the operation is not in the left column, the Orchestrator should skip the GCL loop and return directly.

---

## 2. Five rubric dimensions (mandatory)

Each dimension is scored `0`, `0.5`, or `1`. Thresholds are taken from
[AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 (`qcloud-tcop-ops` →
`optional`, `max_iterations = 1`).

| # | Dimension | Weight | Threshold | Why this threshold for TCOP |
|---|---|---|---|---|
| 1 | **Correctness** | 0.25 | ≥ 0.5 | SDK call must succeed; response parsed correctly; recommendations must map to real resources |
| 2 | **Safety** | 0.25 | = 1 | All recommendations are proposals; no automatic resource mutation; credential masking enforced |
| 3 | **Idempotency** | 0.15 | ≥ 0.5 | Analysis operations are naturally idempotent; report generation must handle duplicate `ReportId` gracefully |
| 4 | **Traceability** | 0.15 | ≥ 0.5 | `RequestId` captured for every SDK call; recommendation rationale documented |
| 5 | **Spec Compliance** | 0.20 | ≥ 0.5 | Output matches documented schema; `{{output.*}}` placeholders resolved; delegation warnings present |

**Safety = 0 → ABORT immediately**, regardless of total score. See
[AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins) → `SAFETY_FAIL`.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high; threshold ≥ 0.5)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| SDK import path and client version match `references/api-sdk-usage.md` | ✓ | minor version drift documented | wrong module / client class |
| `DescribeCostAnalysis` returns `TotalCost` and `ProductCostSet[]` | ✓ all expected fields present | one field missing but documented | response not parsed or fields absent |
| `DescribeRightSizingRecommendations` returns `RecommendationSet[]` with `CurrentSpec`, `RecommendedSpec`, `EstimatedMonthlySavings` | ✓ | one field missing | array empty without explanation or wrong shape |
| `DescribeIdleResources` returns `IdleResourceSet[]` with `ResourceId`, `ResourceType`, `RecommendedAction` | ✓ | one field missing | wrong shape |
| `GenerateOptimizationReport` returns `ReportId`; subsequent `DescribeOptimizationReport` resolves status to `COMPLETED` | ✓ report completes | report ID captured but no polling | report generation failed silently |

### 3.2 Safety (weight: highest; threshold = 1)

| Check | Score 1 | Score 0 |
|---|---|---|
| Every recommendation is presented as a **proposal** with explicit "requires confirmation / delegation" wording | ✓ | recommendation phrased as imperative execution |
| Right-sizing / idle-resource recommendations include explicit delegation warning to owning product skill (`qcloud-cvm-ops`, `qcloud-cdb-ops`, etc.) | ✓ | missing delegation warning |
| `GenerateOptimizationReport` does not trigger automatic resource changes; warnings about action-taking side effects are surfaced | ✓ | report implies auto-execution |
| Cost/waste data is not shared with unauthorized contexts; credential masking enforced | ✓ | credential or raw cost data exposed |
| `sdk-only` path respected — no `tccli` invocation attempted | ✓ | `tccli` used despite unsupported product |

### 3.3 Idempotency (weight: medium; threshold ≥ 0.5)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| `Describe*` calls are naturally idempotent; retry returns same result | ✓ | — | — |
| `GenerateOptimizationReport` retry detects duplicate report request and returns existing `ReportId` | ✓ | retry creates duplicate report | blind retry loop |
| `DescribeOptimizationReport` polling has bounded loop (interval 5s, max 120s) | ✓ | — | unbounded polling |

### 3.4 Traceability (weight: medium; threshold ≥ 0.5)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Full SDK call captured (module, client, method, masked credentials) | ✓ | only response captured | nothing captured |
| `RequestId` from every response captured in trace | ✓ | one missing | none captured |
| Recommendation rationale (confidence, reason) documented | ✓ | partially documented | rationale absent |
| `tccli` not used — if any fallback attempted, trace notes `sdk-only` reason | ✓ | — | `tccli` used without justification |

### 3.5 Spec Compliance (weight: medium; threshold ≥ 0.5)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Output uses documented JSON paths from `SKILL.md` Response Field Table | ✓ | one path off but documented | wrong paths |
| `{{output.*}}` placeholders resolved consistently | ✓ | one placeholder unresolved | placeholders missing |
| Delegation-to-product-skill markers present for actionable recommendations | ✓ | marker present but vague | no delegation marker |
| `{{env.*}}` placeholders used for credentials; never collected from user | ✓ | — | credentials prompted or echoed |

---

## 4. TCOP-specific safety rules

These rules are the **must-cover** subset for the TCOP rollout. Each rule is
enforced by the Safety dimension; missing any of them → Safety = 0 → ABORT.

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DescribeRightSizingRecommendations` / `DescribeIdleResources` | **Recommendations MUST be presented as proposals** (not direct execution). Delegation to the owning product skill MUST be explicit. | TCOP suggests changes but does not own the resource lifecycle. Executing a resize directly bypasses the product skill's safety gates. |
| 2 | `GenerateOptimizationReport` | **Report MUST NOT trigger automatic resource changes.** Warnings about action-taking side effects MUST be surfaced. | A consolidated report could be misread as an execution plan. The Generator must clearly separate analysis from action. |
| 3 | `DescribeCostAnalysis` / `DescribeWasteAnalysis` | **Cost/waste data MUST NOT be shared with unauthorized contexts.** Credential masking required. | Cost data is sensitive; credentials must never appear in command line, trace, or response capture. |
| 4 | `DescribeArchitectureAssessment` | **Assessment is read-only; recommendations MUST NOT be applied automatically.** | Architecture findings delegate to product skills for remediation. |
| 5 | All operations | **SDK is the only execution path (`sdk-only`).** No `tccli` fallback exists. | `tccli` does not ship a `tcop` subcommand. Attempting CLI fallback will fail with "Invalid choice". |

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
    {"rule": 1, "operation": "DescribeRightSizingRecommendations", "rationale": "delegation warning missing"}
  ],
  "thresholds": {
    "correctness": 0.5,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5
  }
}
```

`blocking: true` ⇒ Orchestrator retries G with the suggestions injected. `blocking: false`
⇒ Orchestrator may accept the result if all thresholds are met.

`rule_violations` is **TCOP-specific** (rules 1–5 in §4) and is the audit trail the
Security / Compliance team reads to track which safety rules fire most often.

---

## 6. Worked examples

### Example A — PASS on `DescribeCostAnalysis`

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | SDK call returned `TotalCost` and `ProductCostSet[]`; all expected fields parsed |
| Safety | 1 | Read-only analysis; no recommendations imply execution; credentials masked |
| Idempotency | 1 | `DescribeCostAnalysis` is naturally idempotent |
| Traceability | 1 | `RequestId` captured; SDK call documented |
| Spec Compliance | 1 | Output paths match `SKILL.md` Response Field Table |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on `DescribeRightSizingRecommendations` (delegation warning missing)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Recommendations returned with valid `CurrentSpec` / `RecommendedSpec` |
| **Safety** | **0** | Rule 1 violated: recommendations presented as "resize these instances" without explicit delegation warning to `qcloud-cvm-ops` or user confirmation |
| Idempotency | 1 | — |
| Traceability | 0.75 | `RequestId` captured; recommendation rationale missing confidence level |
| Spec Compliance | 0.75 | Output matches schema but delegation marker absent |

`blocking: true`. `rule_violations: [{rule: 1, operation: DescribeRightSizingRecommendations, rationale: "delegation warning missing"}]`. **ABORT** — recovery suggestion: add explicit "proposed action — delegate to qcloud-cvm-ops for execution" wording before presenting recommendations.

### Example C — RETRY on `GenerateOptimizationReport` (missing side-effect warning)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | `ReportId` returned; `DescribeOptimizationReport` status reached `COMPLETED` |
| Safety | 0.5 → **1** after retry | First iteration report summary phrased as "optimization actions taken" instead of "proposed actions". Retry corrected wording to "proposed actions with side-effect warnings" |
| Idempotency | 1 | Duplicate report request returned existing `ReportId` |
| Traceability | 1 | Full chain captured |
| Spec Compliance | 1 | Output paths match schema |

`blocking: true` on the first iteration. `suggestions: ["Rephrase all recommendation language as proposals; add explicit delegation warnings and side-effect notes"]`. After G re-runs, all dimensions score 1 on the second iteration. `final: PASS, iter: 2`.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-08 | Initial TCOP rubric: 5 dimensions, 5 TCOP-specific safety rules, scoring scale, worked examples |
| 1.1.0 | 2026-07-09 | Tier A conformance: restructure to 8 sections (Scope, Dimensions, Per-dim checklist, Product-specific rules, Output schema, Worked examples, Changelog, See also). Added per-dimension scoring checklist and three worked examples (PASS, SAFETY_FAIL, RETRY) |

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) — generic rubric spec
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-tcop-ops` is `optional`, `max_iter=1`
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time sibling
- [SKILL.md §Quality Gate (GCL)](../SKILL.md#quality-gate-gcl) — GCL applicability, max_iter, trace path
- [SKILL.md §API and Response Conventions](../SKILL.md#api-and-response-conventions) — documented response paths
