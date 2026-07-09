# Spec: Reflexion + Skill Quality Score 基础设施

> Status: draft | Owner: qcloud-skills | Related: `docs/reflexion-memory.md`, `docs/gcl-spec.md`
> Source commits: `feature/reflexion-quality-score` (a4e1d5a, gcl_runner wiring, 2fbd180)

## 1. Purpose

Two cross-cutting, reusable infrastructure scripts that close the self-evolution loop for this repo's GCL (Generator-Critic-Loop) quality system:

- **`reflexion_retrieve.py`** — read side: load ranked failure patterns from `docs/failure-patterns.md` and format them for injection into a GCL Generator run.
- **`skill_quality_score.py`** — aggregate GCL trace history into per-skill quality scores and emit an "upgrade signal" for skills below threshold.

Both are **read-only against cloud resources** and operate purely on local artifacts (`docs/`, `audit-results/`).

## 2. Interfaces (contract)

### reflexion_retrieve.py
- `load_failure_patterns(skill, command=None, top_n=3, path=None) -> list[dict]`
  - Ranking: skill-exact-match = 3pts; command substring match (in command or error) = 2pts; otherwise filtered out.
  - Tie-break by `count` desc. Returns original dicts (no mutation of store).
  - Import dependency: `from failure_pattern_extract import parse_existing` (existing module in `scripts/`).
- `format_for_injection(patterns) -> str`
  - Returns markdown block `- [skill] error=`...` -> fix=`...` (count=N)`.
  - **Credentials masked** via `_mask_credentials` (SecretKey/secret_key, password, AKID*, long base64). Returns `""` (not `None`) when empty.
- CLI: `retrieve --skill <s> [--command <c>] [--top-n N] [--json] [--path P]`

### skill_quality_score.py
- `read_traces(root, since_hours=168) -> list[dict]` — reads `audit-results/gcl-trace-*.json`, windowed by mtime.
- `aggregate_skill_scores(root, since_hours=168, threshold_pass=0.9, threshold_dim=0.8) -> dict`
  - Per skill: `total`, `pass`, `safety_fail`, `pass_rate`, per-dimension avg over `RUBRIC_DIMS = (correctness, safety, idempotency, traceability, spec_compliance)`.
  - `upgrade_signal`: skills where `pass_rate < threshold_pass` OR any dim avg `< threshold_dim`.
- `persist_report(root, report) -> Path` — writes `audit-results/skill-quality-<ts>.json`.
- CLI: `score [--since-hours N] [--threshold-pass F] [--threshold-dim F] [--json]`

## 3. Integration points (already wired)
- `gcl_runner.py:cmd_run` calls `load_failure_patterns(skill, command)` → builds `REFLEXION_PATTERNS` env → injects into Generator; persists `preflight_reflexion` block to trace. Graceful `except` fallback to `[]`.
- `qcloud-skill-generator/SKILL.md` Step 2.5 "Consult Reflexion Memory" documents the read step.
- `AGENTS.md` build-time table registers both scripts.

## 4. Gaps (must-fix, see plan)
1. **Write side missing**: nothing in the repo writes `docs/failure-patterns.md`. The self-evolution loop is read-only today. Need a `reflexion_write` / GCL-trace→pattern extractor that dedups by `skill+command+error` and enforces ≤200 lines.
2. **quality score not in CI**: `skill_quality_score.py` is not registered in `.github/workflows/validate-skills.yml`; no trace fixtures exist, so it cannot run meaningfully in CI.
3. **No unit test for gcl_runner wiring**: the env-injection + `preflight_reflexion` block has no test.
4. **Masking double-count risk**: `_mask_credentials` runs base64 regex over already-masked text in tests — acceptable, but `format_for_injection` should be the single masking boundary.

## 5. Non-goals
- Not a runtime cloud-operation path.
- Not a replacement for GCL Critic scoring; it is a historical aggregate.
- Does not modify `docs/failure-patterns.md` content policy (owned by `docs/reflexion-memory.md`).
