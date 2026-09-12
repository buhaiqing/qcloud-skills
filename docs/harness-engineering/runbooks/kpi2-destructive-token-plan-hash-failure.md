# KPI#2 Failure Runbook — destructive token + plan_hash

## Symptom

`make kpi-gates` shows:

```
FAIL record[N].safety.token: KPI#2 destructive op requires a non-null confirmation token
FAIL record[N].safety.plan_hash: KPI#2 destructive op requires a non-null plan_hash
```

## First diagnosis

```bash
python3 scripts/validate_evidence_schema.py audit-results/evidence-*.json
```

`N` and file identify the offending run.

## Root cause variants

**V1: Operator ran destructive op without `HARNESS_CONFIRM_TOKEN`.**
Run `gcl_runner.py --command "tccli X TerminateY ..."` without setting
the env var. Result: `bind_token` raises `PermissionError`, command
refused, but `pf["plan_hash"]` was never assigned. Producer side bug —
see `gcl_runner.py:1121-1130`.

**V2: Token set but mismatched.** `HARNESS_CONFIRM_TOKEN` was not the
SHA-256 of the command. Bind fails. Fix: re-run with the right token:

```bash
python3 -c "import hashlib; print(hashlib.sha256(b'<your command>').hexdigest()[:16])"
export HARNESS_CONFIRM_TOKEN=<that value>
```

**V3: `gcl_runner.py` regressed.** Check `gcl_runner.py:1130` still
contains `pf["plan_hash"] = plan_hash(args.command)` inside the
`if is_destructive(args.command):` branch. If missing, producer is
not capturing the hash even when the token matches.

## Fix command

```bash
# After fixing producer, regenerate the failing evidence file by re-running
python3 scripts/gcl_runner.py --check --request "..." --command "..." \
    --trace-id "fix-$(date +%s)" --skill qcloud-XXX-ops
```

## Verification

```bash
python3 scripts/validate_evidence_schema.py audit-results/evidence-*.json
# expect: "OK: N file(s) valid"
make kpi-gates | grep KPI#1
# expect: ✅ pass for both KPI#1 and the destructive sub-row
```

See also: [spec-drift-gate.md § 2. Source drift](../spec-drift-gate.md#2-source-drift) for
how this gap was introduced (plan_hash hardcoded to None in the original
emit_evidence_record) and fixed (commit `9499c35`).
