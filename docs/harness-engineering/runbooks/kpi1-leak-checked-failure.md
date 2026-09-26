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
❌ fail | no evidence stream under audit-results/evidence-*.json* (need >= 10 fresh record(s)) …
❌ fail | FAIL only 0 fresh record(s) read; --min-records floor is 10
❌ fail | FAIL only 0 fresh record(s) read; --min-records floor is 10 (12 record(s) were read but aged out beyond 90d)
```

The third form is V5 — the trailing aged-out count is what tells the two apart,
so quote it when you escalate.

## First diagnosis

```bash
python3 scripts/validate_evidence_schema.py --min-records 10 --max-age-days 90 audit-results/evidence-*.json*
```

The graded set is every `audit-results/evidence-*.json*` file unless
`GATE_EVIDENCE_GLOB` names one instead (CI names its committed fixture — see the
"KPI gates" step in `validate-skills.yml`; it is the fixture's verdict, not this
machine's, that CI blocks on).

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
gitignored, so a *fresh clone* is always in this state.

**CI does not need the `GATE_REQUIRE_EVIDENCE=0` escape anymore.** After the
CR-3 job split (validate-skills.yml's `kpi-gates` job), CI grades a committed
fixture staged under a name — `cp scripts/fixtures/evidence/evidence-safety-clean.jsonl
audit-results/evidence-fixture.jsonl && GATE_EVIDENCE_GLOB=evidence-fixture.jsonl
python3 scripts/check_kpi_gates.py` — so the same workflow has both the
graded bytes and the rule it must pass. `GATE_REQUIRE_EVIDENCE=0` is the
documented escape for a *deliberately evidence-free local repo*; CI does not
set it, and a future runbook that mentions it is stale. The H-50 fix in
`scripts/check_kpi_gates.py:aggregate()` ensures any future re-introduction
of the escape would still turn CI red (a silently-skipped rule now exits 1
with a "warn" verdict, not 0).

**V5: The stream is entirely aged out.** Every record is older than
`evidence_max_age_days` (90) — the expiry is working, and the fleet/this machine
has stopped emitting. Confirm with the `aged-out` count in the validator output
(V4 and V5 are the same first line without it), then check that runs are still
happening:

```bash
ls -l audit-results/evidence-*.json*     # portable; `--time-style` is GNU-only (fails on macOS)
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
