# P0-1 Incident Replay Harness — Design

## Background

L4 metrics are dead:

| metric | current | target | root cause |
|--------|---------|--------|------------|
| failure_pattern_hit_rate | 0.0 | 0.6 | no traces with preflight_reflexion.matched > 0 |
| success_path_reuse_rate | 0.0 | 0.9 | no PASS traces with preflight injection |
| emerging_pattern_latency | null | <7d | pattern_anomaly never produced output |

All share one cause: **zero production GCL traces**. GCL→Reflexion→Pattern→Preflight loop has never run at scale. Components exist, flywheel speed = 0.

Goal: synthesize a cold-start corpus → replay through `gcl_runner run --structural-critic-only` → bulk-emit `audit-results/gcl-trace-*.json` → make L4 dashboards non-vacuous → gate them in CI.

## Architecture

```
[synthesize_incident_corpus.py]
  reads  qcloud-*-ops/assets/eval_queries.json  (should_trigger=true lanes)
  reads  references/cli-usage.md read-only templates (Describe*/List* only)
  writes scripts/fixtures/incidents/corpus.jsonl  (≥20 entries JSONL)

[incident_replay.py]  (single owner for all replay modes)
  --mode dry-run : validate corpus schema + destructive-verb safety gate, no subprocess
  --mode replay  : preflight safety gate → subprocess gcl_runner per entry
                   python3 scripts/gcl_runner.py run --skill S --request R --command C
                     --structural-critic-only --trace-id <incident_id> --max-iter 1
  --limit N      : smoke cap
  emits audit-results/replay-summary-<ts>.json

[l4_metrics_tracker.py --gate]
  reuses get_*() helpers; --min-traces guard; writes audit-results/l4-gate.json
  exit 1 when any enabled metric below/above target, exit 0 otherwise
  data-insufficient (traces < min-traces or None metrics) → exit 0 skip (L10)

[Makefile]
  replay-smoke : dry-run corpus + one-shot replay limit=2
  l4-gate      : python3 scripts/l4_metrics_tracker.py --gate
```

## Corpus Schema (JSONL, one object per line)

```json
{"incident_id":"inc-cvm-001","skill":"qcloud-cvm-ops","request":"List CVM instances in Guangzhou","command":"tccli cvm DescribeInstances --limit 5 --output json","severity":"info","source":"eval_queries"}
```

Constraints:
- `incident_id` `^inc-[a-z0-9-]+$` unique
- `skill` must exist as `qcloud-*-ops/SKILL.md`
- `command` must start `tccli ` and Action must match `^(Describe|List|Get|Inquiry)` (read-only whitelist)
- `severity` in `info|warning|critical`
- `source` freeform provenance tag
- Coverage: ≥20 entries, ≥5 distinct skills, all severity buckets present

## Safety Gate

Single source: `scripts/harness_safety.py::VERBS` + `assets/shared/destructive_verbs.json`.
`incident_replay.py` normalizes each command token via `t.lower()` and rejects if `t == v or t.startswith(v)` for any destructive verb `v`. Also enforces read-only Action whitelist above. Rejected entry counted as `rejected`, not retried, reflected in summary.

No credentials are printed. Replay uses `--structural-critic-only`, so no real cloud mutation; still, only read-only Actions are allowed.

## Files

| path | owner | purpose |
|------|-------|---------|
| `scripts/incident_replay.py` | Agent A | replay harness (dry-run + replay) |
| `scripts/incident_replay_test.py` | Agent A | harness tests (L1/L2/L6) |
| `scripts/synthesize_incident_corpus.py` | Agent B | corpus synthesizer |
| `scripts/synthesize_incident_corpus_test.py` | Agent B | synthesizer tests |
| `scripts/fixtures/incidents/corpus.jsonl` | Agent B | generated corpus (≥20) |
| `scripts/l4_metrics_tracker.py` (modify) | Agent C | add --gate / --min-traces / --gate-report |
| `scripts/l4_metrics_gate_test.py` | Agent C | gate two-state tests (L6/L10) |
| `Makefile` (modify) | Agent C | replay-smoke + l4-gate targets |

No overlapping writes across agents.

## Phases (checkbox — single source of truth)

- [ ] Phase A (Agent A): `incident_replay.py` + tests — load/validate/replay, dry-run vs replay, limit, summary emit
- [ ] Phase B (Agent B): `synthesize_incident_corpus.py` + corpus.jsonl ≥20, ≥5 skills, ≥3 severities, 100% read-only
- [ ] Phase C (Agent C): `--gate` mode + Makefile targets + gate tests
- [ ] Phase D (integration): end-to-end `make replay-smoke && make l4-gate` + `ruff check` + `pytest` full suite

## Self-check (must all pass before merge)

- `assert not errors` on both SPECs (this file + e2e-eval-design.md)
- dry-run rejects a destructive-verb fixture (`delete`/`remove`/`stop`) with exit != 0
- clean dry-run exit 0
- corpus ≥20, ≥5 skills, 100% whitelist pass
- gate two-state: insufficient traces → exit 0 skip; healthy traces → exit 0 pass; missing: gate must also prove exit != 0 when data-sufficient but metrics fail (L6) — do not fake with skip
- `ruff check` 0 errors; `pytest` 0 failures
- replay summary `traced == len(corpus) - rejected` (zero loss besides intentional rejects)
