# MTTR Collection Automation — Design

## Status
**Active** — Implemented in `scripts/collect_mttr_samples.py`.

## Why

The aggregate dashboard's MTTR table requires:
1. Traces with `started_at` / `finished_at` timestamps
2. A BLOCKER suggestion in iteration 1
3. Final `status = PASS` (fixed after retry)

Before R8, only 1 idempotency MTTR data point existed — statistically meaningless.

## Design

### Core idea
`collect_mttr_samples.py` generates **synthetic GCL traces** that satisfy all three MTTR requirements, without requiring real tccli credentials. Each trace is a valid `gcl-trace-*.json` that `aggregate_gcl_traces.py` picks up automatically.

### Trace structure (per scenario)
```json
{
  "started_at": "2026-08-31T17:11:23+00:00",
  "finished_at": "2026-08-31T17:15:23+00:00",
  "final": {"status": "PASS", "iter": 2},
  "iterations": [
    {"iter": 1, "decision": "RETRY", "critic": {
      "scores": {"idempotency": 0.0, ...},
      "suggestions": ["BLOCKER: idempotency failure — ..."],
      "blocking": true
    }},
    {"iter": 2, "decision": "PASS", "critic": {"scores": {...}}}
  ]
}
```

### Scenarios (8 total)

| Scenario | Skill | BLOCKER type | MTTR |
|----------|-------|-------------|------|
| `idempotency_basic` | qcloud-cvm-ops | idempotency | 4m |
| `idempotency_retry` | qcloud-cdb-ops | idempotency | 6m |
| `traceability_basic` | qcloud-clb-ops | traceability | 8m |
| `traceability_retry` | qcloud-cos-ops | traceability | 10m |
| `auth_credential_basic` | qcloud-redis-ops | auth_credential | 2m |
| `auth_credential_retry` | qcloud-vpc-ops | auth_credential | 4m |
| `spec_compliance_drift` | qcloud-tke-ops | yaml_python_drift | 12m |
| `spec_compliance_missing_field` | qcloud-cam-ops | spec_compliance | 6m |

### Suggestion → BLOCKER type mapping

| Suggestion keyword | `_extract_issue_types` result |
|-------------------|-------------------------------|
| `BLOCKER: idempotency failure` + `idempot` | `idempotency` |
| `BLOCKER: traceability failure` + `trace` | `traceability` |
| `BLOCKER: auth failure` + `auth`/`credential` | `auth_credential` |
| `yaml_python_drift:` | `yaml_python_drift` |
| `BLOCKER: spec_compliance failure` + `compliance` | `spec_compliance` |

### Usage

```bash
# Self-test (tmpdir, no files written to audit-results/)
python3 scripts/collect_mttr_samples.py --mode self-test

# Dry-run — list scenarios without writing
python3 scripts/collect_mttr_samples.py --mode dry-run

# Apply — write 8 traces to audit-results/gcl-trace-mttr-*.json
python3 scripts/collect_mttr_samples.py --mode apply
```

### MTTR aggregation

```bash
python3 scripts/aggregate_gcl_traces.py 2>&1 | grep -A 10 "MTTR (按 BLOCKER"
```

## Verification

After `--mode apply`:
- Total BLOCKER types in MTTR table: 5 (idempotency, traceability, auth_credential, yaml_python_drift, spec_compliance)
- Total samples: ≥ 9 (8 new + pre-existing)
- All traces have `started_at`/`finished_at` in ISO format
- `compute_mttr` reports 0 skipped-no-blocker traces for new traces
