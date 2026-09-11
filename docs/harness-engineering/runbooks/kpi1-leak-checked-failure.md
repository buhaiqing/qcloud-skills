# KPI#1 Failure Runbook — `safety.leak_checked`

## Symptom

`make kpi-gates` reports `❌ fail` for "KPI#1 leak_checked / KPI#2
destructive-token". Drill into the message:

```
FAIL record[N].safety.leak_checked: KPI#1 requires leak_checked=true
```

## First diagnosis

```bash
python3 scripts/validate_evidence_schema.py audit-results/evidence-*.json
```

The failing `N` and file identify the producer.

## Root cause variants

**V1: Producer (`gcl_runner.py`) regressed.** Writer stopped setting
`leak_checked: True`. Check:

```bash
grep -n 'leak_checked' scripts/gcl_runner.py
```

Expected: literal `True`. A `False`, `None`, or variable binding is the bug.

**V2: New producer added without the field.** Schema requires it; new
code emitting records skipped it. Search for `record = {...}` near new code.

**V3: Schema validator regression.** A PR changed `is True` to `== True`
(truthy, accepts `1`). Restore strictness in `validate_evidence_schema.py:64`.

## Fix command

For V1/V2 (literal regressed or new producer):

```bash
# Edit the producer to write literal True
grep -n 'leak_checked' scripts/gcl_runner.py
# Replace any non-True literal on the right-hand side with: True
# Then re-run the failing gcl_runner invocation; a fresh evidence-*.json is written
```

For V3 (validator regression):

```bash
# Edit scripts/validate_evidence_schema.py:64 — verify the strict comparison
grep 'leak_checked.*is not True\|leak_checked.*== True' scripts/validate_evidence_schema.py
# Expected: ...is not True:  Any match for == True means strictness was lost; restore.
```

## Verification

```bash
python3 scripts/validate_evidence_schema.py audit-results/evidence-*.json
# expect: "OK: N file(s) valid"
make kpi-gates | grep KPI#1
# expect: ✅ pass
```
