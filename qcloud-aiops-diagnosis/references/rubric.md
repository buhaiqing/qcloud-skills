# AIOps Diagnosis Rubric — GCL Scoring

> This skill is **read-only** (no destructive operations). GCL is optional per [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud). Safety=0 does not trigger ABORT; instead, it degrades confidence and adds warnings.

## Rubric Dimensions

| Dimension | Scale | Threshold | Notes |
|-----------|-------|-----------|-------|
| **Correctness** | 0 / 0.5 / 1 | ≥ 0.5 | Evidence actually supports the hypothesis; no fabricated correlations |
| **Safety** | 0 / 1 | = 1 | No mutations performed; all recommendations prefixed `RECOMMENDATION (not execution)` |
| **Idempotency** | 0 / 0.5 / 1 | ≥ 0.5 | Re-running diagnosis produces same evidence bundle (read-only) |
| **Traceability** | 0 / 0.5 / 1 | ≥ 0.5 | All evidence sources recorded; topology links auditable; time windows explicit |
| **Spec Compliance** | 0 / 0.5 / 1 | ≥ 0.5 | Follows 5 rubric rules below; delegates mutations to product skills |

## Safety Rules (Rubric §4)

### Rule 1: Confidence Disclosure
- Surface HIGH/MEDIUM/LOW for each finding
- Never present correlation as causation
- Include confidence rationale in `hypothesis.narrative`

### Rule 2: Read-Only Cross-Skill
- No mutations via this skill
- Confirm read-only in execution trace
- All fix actions delegated to product skills (qcloud-tke-ops, qcloud-cvm-ops, etc.)

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

## Scoring Examples

### Example A: Valid Multi-Source RCA
```json
{
  "scores": {
    "correctness": 1,
    "safety": 1,
    "idempotency": 1,
    "traceability": 1,
    "spec_compliance": 1
  },
  "suggestions": [],
  "blocking": false
}
```

### Example B: Missing Evidence Degrades Confidence
```json
{
  "scores": {
    "correctness": 0.5,
    "safety": 1,
    "idempotency": 1,
    "traceability": 0.5,
    "spec_compliance": 0.5
  },
  "suggestions": [
    "CLS events unavailable: add warning to data_quality.warnings",
    "Lower hypothesis confidence from HIGH to MEDIUM due to evidence gap"
  ],
  "blocking": false
}
```

### Example C: Safety Violation (Hypothetical)
```json
{
  "scores": {
    "correctness": 1,
    "safety": 0,
    "idempotency": 0.5,
    "traceability": 1,
    "spec_compliance": 0
  },
  "suggestions": [
    "CRITICAL: Mutation detected without delegation prefix",
    "Add RECOMMENDATION (not execution) prefix to all actionable outputs",
    "Remove any direct tccli Modify*/Delete*/Create* calls from this skill"
  ],
  "blocking": true
}
```

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-09 | Initial release — 5 rubric rules for read-only AIOps diagnosis skill, scoring examples, Safety=0 handling for read-only skills |
| 1.1.0 | 2026-06-09 | Rule 5 extension: `similar_incidents` must be REFERENCE ONLY |
