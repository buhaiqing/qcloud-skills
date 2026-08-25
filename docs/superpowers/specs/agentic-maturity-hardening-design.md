# SPEC: Agentic Maturity Hardening (Fail-safe Defaults → KB Automation → Memory Efficacy → Closed Loop)

> Status: DONE · Owner: ox-alpha session · Created: 2026-08-26
> Source: maturity-gap review (P0 #2/#3/#1, P1 #4). Follow-up iterations of this subsystem must append here, not create a new file.

## Background

Four gaps identified from an agentic-AI-maturity audit of this repo:

1. **#2 Fail-safe defaults violated (P0)** — two silent-failure defaults:
   - `scripts/autonomy_policy.py::AutonomyPolicy.evaluate` falls through to `auto_confirm` when no rule matches → an unclassified operation auto-executes. Deny-by-default required.
   - `scripts/agent_slo.py::SLOMonitor.compliance` returns `1.0` for empty samples → missing telemetry looks like a perfect SLO (violates lesson L8 "green but vacuous").
2. **#3 Layer-1/2 KB manual & partial (P0)** — `cli_param_validator.py` / `schema_validator.py` ship hand-written KBs covering ~13/34 skills. Coverage drifts silently.
3. **#1 Reflexion memory has no efficacy attribution (P0/P1)** — patterns are injected into Generator context (`gcl_runner.py` pre-flight) but nothing records *which* patterns were injected nor measures whether injection reduced recurrence.
4. **#4 Self-evolution loop last mile open (P1)** — `skill_quality_score.py` emits `upgrade_signal` but no orchestrator consumes it end-to-end (root cause → FixProposal → golden regression gate → PR via `self_heal_pr_workflow.py`).

## Architecture

```
[W1] fail-safe defaults          [W3] memory efficacy
 autonomy_policy.py               gcl_runner.py preflight_reflexion
   └─ fallback → human_approval     ├─ + injection_id, matched_failure_keys[]
 agent_slo.py                       └─ reflexion_efficacy.py (new)
   └─ empty → N/A + breach             └─ hit-rate / prevention-rate report

[W2] KB automation               [W4] closed loop
 kb_sync_openapi.py (new)          self_evolution_loop.py (new)
   └─ tccli metadata → shared KB     ├─ skill_quality_score --json
      assets/shared/*.json           ├─ root-cause pick from traces+patterns
      cli_param_validator merge      ├─ golden regression gate (scoped validators)
      schema_validator merge         └─ SelfHealPRWorkflow.run_workflow
```

## Schema / Contracts

### W1
- `compliance(agent) -> dict[str, float | None]`; `None` = no data (N/A).
- `breaches(agent)` treats `None` as breach (missing telemetry must alert).
- `evaluate()` no-match fallback action: `human_approval`, `matched_rule=None`.
- Explicit `"else"` catch-all rules remain honored (documented escape hatch); LEVEL_0 semantics unchanged.

### W2
- `scripts/kb_sync_openapi.py --metadata <dir-or-file> [--out-dir assets/shared] [--check]`
  - Input: tccli product metadata JSON (`{product: {version: {actions: {Action: {metadata: {method}, request: {members}}}}}}` shape; tolerant to missing products).
  - Outputs:
    - `assets/shared/tcloud_cli_flags.json`: `{skill: {action: [flags...]}}`
    - `assets/shared/tcloud_response_schemas.json`: `{skill: {action: {required, data_field?, request_id}}}`
    - `assets/shared/tcloud_kb_coverage.json`: per-skill covered-action counts.
  - Product→skill mapping: `cvm → qcloud-cvm-ops` etc.; unmapped products skipped with warning.
  - Validators merge external KB over built-in `_KNOWN_FLAGS` / `_SCHEMA_KB` (external wins); load path overridable via `TCLOUD_KB_DIR` env var; graceful skip when files absent (L10).

### W3
- `preflight_reflexion` trace block gains:
  - `injection_id`: `<utc-timestamp>-<sha1(skill+command)[:8]>`
  - `matched_failure_keys`: `[ "<skill>|<command>|<error>" ... ]`
- `scripts/reflexion_efficacy.py [--trace-dir audit-results] [--json] [--out PATH]`
  - Metrics: `runs_total`, `runs_with_injection`, `hint_coverage`, per-pattern `injected_runs`, `recurred_runs`, `prevention_rate = 1 - recurred/injected`.
  - Recurrence match: later trace same skill, final.status != PASS, failure text fuzzy-contains stored pattern error keyword (normalized lowercase substring on first 40 chars).
  - Self-check: report generation raises/asserts non-vacuous when ≥1 injected run exists (L5/L8).

### W4
- `scripts/self_evolution_loop.py [--dry-run] [--max-skills N] [--root .]`
  1. Run `skill_quality_score.py --json` in-process import; collect `upgrade_signal`.
  2. Per signal skill: pick top recurring failure pattern (traces + `failure_pattern_extract`) as root cause.
  3. Build golden regression gate: run scoped validators (`validate_skills_frontmatter` target, `cli_param_validator --dry-run`, `schema_validator --dry-run`). Gate must pass BEFORE PR creation.
  4. Construct `FixProposal(level="L2", ...)` patching the owning SKILL.md rubric threshold note / references fix note — content change is deliberately conservative (documentation-level remediation), full auto-codegen out of scope for this phase.
  5. Delegate to `SelfHealPRWorkflow.run_workflow` unless `--dry-run` (then print proposal only).
  - Exit codes: 0 nothing-to-do or all succeeded; 1 any workflow failure.

## File Manifest

| File | Change |
|---|---|
| `scripts/autonomy_policy.py` | fallback `auto_confirm` → `human_approval` |
| `scripts/test_autonomy_policy.py` | new no-match fail-safe tests |
| `scripts/agent_slo.py` | N/A compliance + breach-on-missing |
| `scripts/agent_slo_test.py` | update contract (L12) |
| `scripts/kb_sync_openapi.py` (+test) | NEW generator + coverage |
| `scripts/cli_param_validator.py` | external KB merge layer |
| `scripts/schema_validator.py` | external KB merge layer |
| `scripts/gcl_runner.py` | injection_id + matched_failure_keys in trace |
| `scripts/reflexion_efficacy.py` (+test) | NEW efficacy attribution report |
| `scripts/self_evolution_loop.py` (+test) | NEW closed-loop orchestrator |
| `docs/gcl-spec.md` §12 | changelog entry |

## Plan (checkboxes = live progress)

### Phase A — Fail-safe defaults (#2)
- [x] A1 autonomy_policy no-match fallback → human_approval + tests
- [x] A2 agent_slo empty-sample N/A + breach-on-missing + dashboard N/A + tests

### Phase B — KB automation (#3)
- [x] B1 kb_sync_openapi.py generator + coverage report + unit test w/ fixture
- [x] B2 validators merge external KB (TCLOUD_KB_DIR), coverage surfaced in --dry-run

### Phase C — Memory efficacy (#1)
- [x] C1 injection_id + matched_failure_keys recorded in gcl_runner trace
- [x] C2 reflexion_efficacy.py metrics report + unit test

### Phase D — Closed loop (#4)
- [x] D1 self_evolution_loop.py orchestration + dry-run mode + unit test

### Phase E — Verification & sedimentation
- [x] E1 full script test suite green (changed-file suites + validate_local python gates)
- [x] E2 changelog + CADL review

## Self-Check (DoD)

- `python3 -m unittest scripts.test_autonomy_policy scripts.agent_slo_test` (and each new *_test) exit 0.
- No-match evaluation NEVER returns `auto_confirm` without an explicit `else` rule (asserted by test).
- Empty-sample SLO never reports compliance 1.0 (asserted by test).
- `kb_sync_openapi.py` on bundled fixture produces non-empty KBs and coverage file (asserted by test).
- `reflexion_efficacy.py` asserts non-vacuous metrics given injected-run fixtures (asserted by test).
- `self_evolution_loop.py --dry-run` produces proposal without network/PR side effects (asserted by test).
