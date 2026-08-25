# SPEC: Shadow Rehearsal Environment (mock tccli shim + GCL integration)

> Status: DONE (GCL 2 iterations; both critics PASS round 2) · Created: 2026-08-26 · GCL task: yes (fix/add trigger)
> Maturity gap #5: destructive ops can only be scored post-hoc by GCL today —
> there is no way to rehearse `TerminateInstances`-class operations against a
> recorded environment before touching real resources.

## Background

GCL scores executions after they happen. For destructive cloud ops the first
real execution IS the incident. This spec adds a **shadow rehearsal layer**:
record real tccli responses once, then replay them deterministically so the
full Generator→Critic loop runs without any cloud side-effect.

## Architecture

```
record (explicit, hits REAL API once)
  tccli_shadow.py record -- 'tccli cvm DescribeInstances ...'
    → subprocess real call → sanitize → audit-results/shadow-fixtures/<key>.json

replay (never touches network)
  tccli_shadow.py exec -- 'tccli cvm TerminateInstances ...'
    → normalize(product, action, flags) → key lookup
    → HIT  : stdout = stored response, exit = stored exit_code
    → MISS : stderr SHADOW_MISS:<key>, exit 2 (NEVER falls through to real API)

gcl_runner integration
  run_command() honors TCCLI_SHADOW=1: argv rewritten to
  [sys.executable, tccli_shadow.py, exec, --, <original command>]
  trace generator block records "shadow": true
```

## Contracts

### Fixture schema (`audit-results/shadow-fixtures/<key>.json`)
```json
{
  "schema_version": "v1",
  "key": "<sha1[:16] of normalized command>",
  "normalized": {"product": "cvm", "action": "TerminateInstances", "flags": {...}},
  "raw_command_masked": "...",
  "stdout": "<response JSON as text>",
  "stderr": "",
  "exit_code": 0,
  "recorded_at": "<ISO8601>",
  "destructive": true
}
```
Normalization: lowercase flag names, strip leading `--`, sort by flag name;
flag VALUES are part of the key EXCEPT volatile tokens replaced by placeholders
(`ins-*`, `sg-*`, `lb-*`, `vpc-*`, `subnet-*`, `cbs-*`, region kept). Two calls
differing only in resource id hit the same fixture — rehearsal is about shape,
not specific ids.

### Safety gates
1. `exec` NEVER executes the real tccli — lookup-only; miss = exit 2.
2. `record` DOES hit the real API: requires explicit `--yes-real-api` AND
   refuses destructive commands unless additionally given
   `--allow-destructive-record` (L21 deny-by-default).
3. Stored fixtures pass credential masking (L3 regex via gcl_runner.mask_secrets).
4. `parse_generator_command` allowlist still applies inside the shim.

### gcl_runner changes
- `run_command(...)`: if `TCCLI_SHADOW=1` in effective env → wrap argv.
- Trace generator block gains `"shadow": true/false`.

## File Manifest

| File | Change |
|---|---|
| `scripts/tccli_shadow.py` (+test) | NEW shim: record/exec/normalize/keys |
| `scripts/gcl_runner.py` (+test additions) | shadow routing in run_command |
| `assets/shared/validation_commands.yaml` | `shadow_rehearsal_smoke` entry |
| `docs/superpowers/specs/shadow-rehearsal-design.md` | this doc |

## Plan

### Phase A — Shim
- [x] A1 normalize/key functions + unit tests (id placeholdering, flag sorting)
- [x] A2 fixture store save/load + masking + tests
- [x] A3 exec replay (hit/miss/destructive metadata) + tests
- [x] A4 record mode with safety gates + tests (PATH-stubbed fake tccli)

### Phase B — GCL integration
- [x] B1 run_command shadow routing + trace `"shadow"` field + tests

### Phase C — GCL loop & sedimentation
- [x] C1 ≥2 isolated Critic reviews on worktree diff; fix until PASS
- [x] C2 merge --no-ff, cleanup worktree, validation_commands entry

## Self-check (DoD)
- Replay of a recorded destructive command returns identical stdout/exit_code with zero network.
- Missed fixture exits 2 with SHADOW_MISS; never invokes real tccli.
- `TCCLI_SHADOW=1 python3 scripts/gcl_runner.py ...` produces trace with `"shadow": true`.
- All new tests green; full scripts suite stays green.
