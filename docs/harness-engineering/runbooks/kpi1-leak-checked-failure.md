# KPI#1 Failure Runbook — `safety.leak_checked`

## Symptom

`make kpi-gates` reports `❌ fail` for "KPI#1 leak_checked / KPI#2
destructive-token". Drill into the message:

```
FAIL record[N].safety.leak_checked: KPI#1 requires leak_checked=true
```

The gate also fails (and this runbook covers) the three *evidence-supply*
failures, which never name a record because there is nothing to name:

```
❌ fail | no evidence stream under audit-results/ (need >= 10 fresh record(s)) …
❌ fail | FAIL only 0 fresh record(s) read; --min-records floor is 10
❌ fail | FAIL only 0 fresh record(s) read; --min-records floor is 10
         (N records were read but all aged out — see V5)
```

## First diagnosis

```bash
python3 scripts/validate_evidence_schema.py --min-records 10 --max-age-days 90 audit-results/evidence-*.json*
```

The failing `N` and file identify the producer. A count line
`OK: N record(s) valid, M aged-out` tells you how much of the stream is too old
to count (`evidence_max_age_days` in `assets/shared/thresholds.json`).

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
(truthy, accepts `1`). Restore strictness in `validate_evidence_schema.py`
(`validate_record`, the `leak_checked is not True` branch).

**V4: No evidence stream at all.** The gate read zero files. Either this machine
has never run the harness (`make kpi-gates` needs at least one real run:
`python3 scripts/gcl_runner.py run --skill … --request …`), or the stream was
deleted/truncated, or `audit-results/` was cleaned. `audit-results/` is
gitignored, so a *fresh clone* is always in this state — that is why CI runs the
gate with `GATE_REQUIRE_EVIDENCE=0` (an explicit, visible skip). Do not add that
escape to a machine that is supposed to be emitting evidence; it is not a fix
for an empty stream.

**V5: The stream is entirely aged out.** Every record is older than
`evidence_max_age_days` (90) — the expiry is working, and the fleet/this machine
has stopped emitting. Confirm with the `aged-out` count in the validator output,
then check that runs are still happening:

```bash
ls -l --time-style=long-iso audit-results/evidence-*.json*
```

Note the two rules are deliberately different: a *stale-but-violating* record
still fails KPI#1/#2 (a destructive op without a token is a violation whenever it
happened), while a stale record no longer counts toward the floor. Ageing out
cannot launder a safety violation.

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
python3 scripts/validate_evidence_schema.py --min-records 10 --max-age-days 90 audit-results/evidence-*.json*
# expect: "OK: N record(s) valid, M aged-out (…)" with N >= the floor
make kpi-gates | grep KPI#1
# expect: ✅ pass
```
