# AIOps Diagnosis Quality-Gate Rubric (GCL)

> Runtime scoring rubric for **Generator-Critic-Loop (GCL)** of `qcloud-aiops-diagnosis`.
> Source-of-truth: [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8
> (`qcloud-aiops-diagnosis` → **optional**, `max_iterations = 5`).
>
> **Read-only** — no destructive cloud operations. GCL Safety=0 on mutation attempts
> sets `blocking: true` but does not hard-ABORT cloud state (nothing was mutated).

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Log / metric / event correlation across Monitor, TKE, CLB, CVM, CLS, CDB, etc. | Live resource CRUD → delegate to `qcloud-*-ops` product skills |
| Multi-source RCA (alarm → topology → metrics → logs) | Single-product ops runbooks (use the product skill directly) |
| Hypothesis generation with confidence scoring | Automated remediation or mutation without user confirmation |
| Cross-skill read-only delegation per `delegation-matrix.md` | Direct `Create*` / `Modify*` / `Delete*` / `Drain*` API calls |

---

## 2. Five rubric dimensions (mandatory)

Each dimension is scored `0`, `0.5`, or `1`. Thresholds from [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill).

| # | Dimension | Threshold | Why for AIOps Diagnosis |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 | Evidence must support the hypothesis; fabricated correlations mislead incident response |
| 2 | **Safety** | **= 1** | No mutations; all recommendations prefixed `RECOMMENDATION (not execution)` |
| 3 | **Idempotency** | ≥ 0.5 | Re-running diagnosis on same window should produce same evidence bundle (read-only) |
| 4 | **Traceability** | ≥ 0.5 | All evidence sources, topology links, and time windows must be auditable |
| 5 | **Spec Compliance** | ≥ 0.5 | Follows 8 safety rules in §4; delegates mutations via `delegate_to` field |

**Mutation detected in trace → Safety = 0, blocking = true.** Read-only skills do not
trigger `SAFETY_FAIL` cloud abort, but the Orchestrator MUST NOT return partial
recommendations that imply execution occurred.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Hypothesis backed by ≥ 2 independent evidence layers | ✓ | 1 layer only | no evidence cited |
| Correlation presented as hypothesis, not causation | ✓ | — | stated as confirmed root cause without evidence |
| `top_cause` matches highest-scoring hypothesis | ✓ | — | mismatch or missing |
| Time coincidence verified for HIGH confidence | ✓ | partial overlap | non-overlapping windows claimed as HIGH |

### 3.2 Safety

| Check | Score 1 | Score 0 |
|---|---|---|
| No `Create*` / `Modify*` / `Delete*` / `Drain*` in trace | ✓ | any mutation API called |
| All recommendations prefixed `RECOMMENDATION (not execution)` | ✓ | actionable text without prefix |
| `delegate_to` names a product skill for every fix action | ✓ | missing or self-referential |

### 3.3 Idempotency

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Same diagnosis window re-run produces same evidence keys | ✓ | minor ordering diff | different evidence set without explanation |
| Read-only API calls only | ✓ | — | state-changing side effect |

### 3.4 Traceability

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| `execution_trace` lists every tccli/SDK call | ✓ | partial | missing |
| `diagnosis_window` / `time_alignment.overall_window` explicit | ✓ | — | absent |
| `source_recency` per evidence layer | ✓ | partial | absent |
| Credentials masked in trace | ✓ | partial redaction | raw SecretKey in output |

### 3.5 Spec Compliance

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Follows all 8 rules in §4 | ✓ | 1 rule missed | ≥ 2 rules missed |
| Delegation matrix respected for cross-skill calls | ✓ | — | unlisted skill invoked |
| Output matches `output-schemas.md` shape | ✓ | partial schema | invalid JSON |

---

## 4. AIOps-specific safety rules

### Rule 1: Confidence Disclosure
- Surface HIGH/MEDIUM/LOW for each finding
- Never present correlation as causation
- Include confidence rationale in `hypothesis.narrative`

### Rule 2: Read-Only Cross-Skill
- No mutations via this skill
- Confirm read-only in execution trace
- All fix actions delegated to product skills (`qcloud-tke-ops`, `qcloud-cvm-ops`, etc.)

### Rule 3: Time-Range Correlation
- Surface diagnosis window explicitly (`diagnosis_window`, `time_alignment.overall_window`)
- Warn when evidence layers have non-overlapping windows
- Time coincidence is required for HIGH confidence

### Rule 4: Data Recency
- Surface `source_recency` timestamps per evidence layer
- Warn when data is stale (> 15 min old for real-time diagnosis)
- Degrade confidence when sources are unavailable

### Rule 5: Recommendation Boundary
- Prefix all actionable recommendations: `RECOMMENDATION (not execution)`
- Include `delegate_to` field naming the product skill
- Never auto-execute mutations (scaling, restart, delete)
- `similar_incidents` advisories must be prefixed `REFERENCE ONLY` — historical cases do not override current evidence

### Rule 6: Product RCA Coverage (Rules H–P)
- When diagnosing CDB/Redis/ES/COS/CKafka/MongoDB/Postgres/SCF/CDN symptoms, must invoke corresponding product rule
- Rule selection must match symptom pattern (e.g., slow queries → Rule H, memory spike → Rule I)
- Evidence layers must include product-specific metrics from correct Monitor namespace
- Hypothesis scoring must reference product-specific evidence signals

### Rule 7: Network Path Validation (Rule G)
- When compute/data metrics normal but connectivity symptoms present, must apply Rule G
- Must collect security group, route table, and NAT gateway evidence
- Network hypotheses (G1–G4) require CloudAudit change correlation when available
- If VPC evidence unavailable, degrade confidence and warn in `data_quality`

### Rule 8: Cross-Product Topology
- When symptoms span multiple products (e.g., TKE + CLB + CVM), must build cross-product topology
- Evidence linkage must connect entities across products via shared identifiers (instance_id, vpc_id)
- Hypothesis scoring must account for cross-product evidence correlation

---

## 5. Output schema (returned by Critic)

Strict JSON per [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill):

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
    {"rule": 2, "operation": "ModifyDBInstance", "rationale": "mutation detected in read-only skill"}
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

---

## 6. Worked examples

### Example A: Valid Multi-Source RCA

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Alarm + CLB target health + CVM metrics align within diagnosis window |
| Safety | 1 | Read-only trace; recommendations prefixed correctly |
| Idempotency | 1 | Re-run on same window yields same evidence keys |
| Traceability | 1 | Full `execution_trace`; time windows explicit |
| Spec Compliance | 1 | All 5 rules satisfied |

`blocking: false`. `final: PASS, iter: 1`.

### Example B: Missing Evidence Degrades Confidence

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | CLS events unavailable; hypothesis downgraded to MEDIUM |
| Safety | 1 | No mutations |
| Idempotency | 1 | Read-only |
| Traceability | 0.5 | Partial — CLS layer marked `unavailable` but no warning in `data_quality` |
| Spec Compliance | 0.5 | Rule 4 partial — stale source not flagged |

`blocking: false`. Suggestions: add CLS warning; lower confidence.

### Example C: Safety Violation (Mutation Detected)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | — |
| **Safety** | **0** | `tccli cvm StopInstances` in trace without delegation |
| Idempotency | 0.5 | — |
| Traceability | 1 | — |
| Spec Compliance | 0 | Rules 2 and 5 violated |

`blocking: true`. Recovery: remove mutation; prefix recommendations; set `delegate_to: qcloud-cvm-ops`.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-09 | Initial release — 5 rubric rules for read-only AIOps diagnosis |
| 1.1.0 | 2026-06-09 | Rule 5 extension: `similar_incidents` must be REFERENCE ONLY |
| 1.2.0 | 2026-06-19 | Renumbered to canonical 8 sections (Tier C conformance) |
| 1.3.0 | 2026-07-04 | Added Rules 6–8: Product RCA coverage (H–P), Network path validation (Rule G), Cross-product topology |

---

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-aiops-diagnosis` is `optional`, `max_iter=5`
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [`delegation-matrix.md`](delegation-matrix.md) — cross-skill read-only delegation
- [SKILL.md](../SKILL.md)
