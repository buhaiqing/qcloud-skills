# auto-fix-gcl-blockers — Spec

## Problem Statement

GCL traces accumulate BLOCKER suggestions. Two categories dominate the historical
record (from evidence-local.jsonl, 265 runs, 204 iterations with suggestions):

| Category | Occurrences | Root Cause |
|---|---|---|
| **traceability** | 39 | Generator response missing `RequestId` — cannot correlate with API logs |
| **idempotency** | 129 | Generator response missing `ClientToken` — cannot verify idempotency |
| **auth_credential** | 18 | `exit_code=-2` — command rejected or credentials missing |
| other | 18 | Misc suggestions ("fix") |

The first two are structural (every tccli call SHOULD return both fields), the
third is operational (wrong command or env misconfig).

## Solution

`scripts/auto_fix_gcl_blockers.py` — dry-run-first fixer with two modes:

1. **traceability mode**: fills missing `started_at / finished_at / commits / files_changed`
   in the trace JSON itself (does NOT fix the Generator; makes the trace self-describing)
2. **idempotency mode**: injects `ClientToken` into generator commands (**dry-run only**;
   actual injection requires `--apply` + user confirm, since past commands cannot be re-run)
3. **race detection**: flags non-monotonic iteration timestamps (possible parallel-write race)

What it CANNOT fix (manual only):
- auth_credential: wrong command or bad credentials — human must fix env / command
- idempotency in already-executed traces: only flags for next run

## Top-3 Suggestions Per Category

### traceability (RequestId missing, 39×)
```
[39x] Response missing RequestId — traceability degraded
```
All occurrences are identical — tccli responses return RequestId but Generator
does not surface it in the result object.

### idempotency (ClientToken missing, 129×)
```
[108x] set ClientToken
[21x]  Response missing ClientToken — idempotency cannot be verified
```
108 iterations received the short-form "set ClientToken" suggestion; 21 received
the full traceability-degraded form. Both indicate the same gap: Generator did
not track or emit ClientToken.

### auth_credential (exit_code=-2, 18×)
```
[18x] Generator exit_code=-2; fix command or credentials
```
exit_code=-2 means the command was rejected by the skill harness (e.g., non-tccli
command attempted). Human must fix the command or the skill permission model.

## Auto-fix Strategy

| Category | Fixable | Strategy |
|---|---|---|
| traceability | **yes** | Add default `started_at / finished_at / commits / files_changed` to trace JSON |
| idempotency (ClientToken) | **flag-only** | Cannot re-run past commands; annotate trace with `gcl_flags.idempotency_flagged` for next run |
| idempotency (race) | **detect** | Flag non-monotonic iteration timestamps for manual review |
| auth_credential | **no** | Human must resolve; log for pattern analysis |

## Schema Notes

Current GCL trace schema (gcl-trace-*.json / evidence-local.jsonl) lacks:
- `started_at` / `finished_at` at trace level — aggregate dashboard shows N/A
- `commits` / `files_changed` — no SCM correlation
- `ClientToken` in generator output — idempotency unverifiable

These are tracked as R5 T1 scope (gcl_runner.py schema extension). The auto-fix
tool adds placeholder values so the dashboard is no longer N/A.

## Files

| File | Purpose |
|---|---|
| `scripts/auto_fix_gcl_blockers.py` | Fixer + race detector |
| `scripts/aggregate_gcl_traces.py` | Enhanced with suggestion Top-3 + fix coverage |
| `docs/superpowers/specs/auto-fix-gcl-blockers.md` | This document |

## Verification

```bash
python3 scripts/auto_fix_gcl_blockers.py --self-test
python3 scripts/auto_fix_gcl_blockers.py --dry-run
python3 scripts/auto_fix_gcl_blockers.py --check-idempotency
python3 scripts/aggregate_gcl_traces.py 2>&1 | tail -30
ruff check scripts/auto_fix_gcl_blockers.py scripts/aggregate_gcl_traces.py
```
