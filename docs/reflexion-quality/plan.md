# Plan: Close the Reflexion + Quality-Score Loop

> Depends on: `docs/reflexion-quality/spec.md`
> Branch: `feature/reflexion-quality-score` (or follow-up `feature/reflexion-write-ci`)
> Harness note: large/independent items run in **git worktree + subagent** per AGENTS.md.

## Item 1 — Reflexion write side (close self-evolution loop)
**Why:** `reflexion_retrieve` reads `docs/failure-patterns.md`, but nothing writes it. Loop is half-open.
**What:**
- Add `reflexion_retrieve.py` subcommand `upsert` (or new `reflexion_write.py`) that takes a pattern `{skill, command, error, fix}` and:
  - dedups by `skill+command+error` (increment `count`), per `docs/reflexion-memory.md`;
  - enforces ≤200 lines (drop lowest-count when over);
  - is idempotent (re-running same pattern only bumps count).
- Wire GCL `failure_pattern` (from trace) → upsert at end of `gcl_runner.py:cmd_run` (or in Critic finalize).
**Verify:** unit test for upsert idempotency + dedup; manual run against a sample trace produces a new line in `docs/failure-patterns.md`.
**Worktree:** yes (independent of task 1 commits).

## Item 2 — Register quality score in CI
**Why:** `skill_quality_score.py` exists but is not exercised by CI; no signal without execution.
**What:**
- Add a `scripts/fixtures/gcl-quality-summary-*.json` trace fixture (healthy + at-least-one-upgrade) so the score step is deterministic in CI.
- Register `python3 scripts/skill_quality_score.py score --json` in `.github/workflows/validate-skills.yml` (non-blocking informational step, like `gcl_alarm_wire`).
**Verify:** `validate_local.py` includes the step; CI green on PR.
**Worktree:** yes.

## Item 3 — Unit test gcl_runner reflexion wiring
**Why:** env injection + `preflight_reflexion` block is the riskiest new path and untested.
**What:**
- Add `scripts/gcl_runner_test.py` (or extend existing) covering: (a) empty store → `gen_env=None`, `preflight_reflexion.matched=0`; (b) populated store → `REFLEXION_PATTERNS` set; (c) `load_failure_patterns` raises → fallback `[]`.
- Keep using `--structural-critic-only` so no real tccli call.
**Verify:** `cd scripts && python3 -m unittest discover -p "*_test.py"` green.

## Item 4 — Single masking boundary ✅ DONE
**What:** ensure `format_for_injection` is the only place credentials get masked for injection output; remove redundant masking if any.
**Finding:** No redundant masking exists. Two separate functions serve distinct paths:
- `_mask_credentials()` in `reflexion_retrieve.py` → masks pattern error/fix fields **before** injection into Generator prompt (via `format_for_injection` → `REFLEXION_PATTERNS` env var).
- `mask_secrets()` in `gcl_runner.py` → masks Generator **stdout/stderr** for trace/logging output only. Neither function touches the other's data path.
**Verify:** `reflexion_retrieve_test` 6/6 pass; `test_mask_credentials_function` covers the boundary.

## Execution order
1. Item 3 (cheap, unblocks confidence in task-1 wiring) — ✅ landed on current branch.
2. Items 1 & 2 in parallel worktrees — ✅ merged.
3. Item 4 audit — ✅ no action needed, documented above.
4. Final: re-run full `validate_local.py` → confirm only the 3 pre-existing failures remain.

## Evidence gate
- Each item: `ruff check` clean + relevant unittest green before merge.
- Final: `git diff main..HEAD --stat` excludes `qcloud-cos-ops/`; no secret literals.
