# P0-2 E2E Evaluation Suite — Design

## Background

P0-1 makes L4 dashboards non-vacuous by bulk-emitting traces. P0-2 proves **task success**, not just trace volume, and proves **learning works**.

Current `assets/eval_queries.json` only tests `should_trigger` (intent classification). No score for: task completion, plan quality, or whether Reflexion injection actually helps.

## Goals

1. Deterministic task-level graders that judge end-to-end success per incident (not just trigger).
2. Track plan quality (copilot `engine.ask(dry_run=True)` path, no cloud calls).
3. Prove learning efficacy via A/B: with-reflexion vs without-reflexion on the same corpus.

P0-2 starts after P0-1 lands (reuses `corpus.jsonl` + `gcl-trace-*.json` data contracts). Spec + Plan are prepared now so sizing is explicit; no code is written until P0-1 is merged.

## Architecture

```
corpus.jsonl (P0-1, extended — backward compatible)
  + expected_intent?  string   e.g. "DescribeInstances"
  + expected_status?  "PASS"|"RETRY"|"ABORT"  (optional oracle)
  + expected_readonly? bool

[eval_graders.py]  deterministic, side-effect-free
  grade_intent(entry, trace)        → 0/1  (trace.intent vs expected_intent)
  grade_traceability(entry, trace)  → 0/1  (trace has command/params/request)
  grade_safety(entry, trace)        → 0/1  (safety dimension pass)
  grade_plan(plan, entry)           → {step_count, redundancy_ratio}
  grade_readonly(entry)             → 0/1  (command whitelist pass)

[eval_e2e.py]
  mode=e2e   corpus + trace-dir → runs all graders per incident → audit-results/e2e-report-<ts>.json
  mode=ab    --ab  (requires gcl_runner --no-reflexion, see §4)

[copilot dry_run track]  (no credentials, no cloud calls)
  for each incident: engine = CopilotEngine(...); plan = engine.ask(request, dry_run=True)
  graders consume plan for plan-quality metrics

Outputs: audit-results/e2e-report-<ts>.json, audit-results/e2e-ab-report-<ts>.json, audit-results/e2e-baseline.json
```

## Corpus Extension (backward compatible — new fields are optional)

Existing P0-1 corpus entries remain valid graders handle `None` as "skip this dimension".

```
{"incident_id":"...","skill":"...","request":"...","command":"...","severity":"...",
 "expected_intent":"DescribeInstances","expected_status":"PASS","expected_readonly":true}
```

If a field is absent, that grader is skipped for that entry (no score, no failure).

## New Flag for A/B (§4)

`scripts/gcl_runner.py` needs one addition: `--no-reflexion` to skip preflight `reflexion_retrieve` injection. A/B then is:

```
# A (with reflexion) : python3 scripts/gcl_runner.py run --skill ... --request ... --command ... --structural-critic-only --trace-id inc-xxx
# B (without)        : python3 scripts/gcl_runner.py run --skill ... --request ... --command ... --structural-critic-only --no-reflexion --trace-id inc-xxx-ctrl
compare avg_iterations / pass_rate across same corpus
```

Guardrails for the flag: default off (existing behavior unchanged), isolated to preflight retrieval only, zero impact on rubric or safety gates.

## Files (P0-2 owns; P0-1 blocked)

| path | purpose |
|------|---------|
| `scripts/eval_graders.py` | deterministic graders (pure functions, no I/O) |
| `scripts/eval_graders_test.py` | golden tests per grader |
| `scripts/eval_e2e.py` | runner (e2e + ab modes), baseline compare |
| `scripts/eval_e2e_test.py` | runner tests |
| `scripts/gcl_runner.py` (small modify) | add --no-reflexion flag |
| `scripts/fixtures/incidents/corpus.jsonl` (extend) | add expected_* to a subset of entries |
| `Makefile` (extend) | eval-e2e, eval-ab targets (non-blocking CI) |

Overlap with P0-1: `gcl_runner.py` and `corpus.jsonl` are shared. Rule: P0-2 does not modify them until P0-1 is merged. If both branches need to touch them, rebase P0-2 on P0-1 merge commit.

## Phases (checkbox — single source of truth, sized for review)

- [ ] Phase A — `gcl_runner.py --no-reflexion` + test (2 pts, isolated, no P0-1 data needed)
- [ ] Phase B — `eval_graders.py` + `eval_graders_test.py` (pure, no subprocess; golden-tested; most reviewable)
- [ ] Phase C — `eval_e2e.py` (e2e mode: corpus + trace-dir → report; dry_run plan track; baseline compare)
- [ ] Phase D — `eval_e2e.py` ab mode + `corpus.jsonl` expected_* enrichment (depends on Phase A+C)
- [ ] Phase E — Makefile/CI wiring (non-blocking) + two-state verification
- [ ] Phase F — GCL review (≥2 Critics) → merge → delete worktree

First branch for P0-2 should be `feature/e2e-eval` cut from P0-1 merge commit. Do not fan out P0-2 code agents until P0-1 GCL review passes.

## Self-check (must all pass before merge)

- `pytest scripts/eval_graders_test.py` — golden cases per grader, 0 failures
- `pytest scripts/eval_e2e_test.py` — runner on 2-fixture smoke corpus, deterministic report
- `ruff check` 0 errors
- `make eval-e2e` on current `audit-results/` produces valid JSON with non-vacuous metrics (`completion_rate`, `intent_accuracy`, `plan_redundancy` are present and typed per L8)
- `make eval-ab --limit 4` demonstrates flag isolation: B traces contain `preflight_reflexion.matched==0` or absent, A traces unchanged — config snapshot diff asserts single-variable isolation
- no overlapping writes with P0-1 branch
