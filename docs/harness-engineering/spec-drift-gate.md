# Spec-Code Drift Gate

**Spec says A. Code verifies B. A and B diverge over time.** This drift
is the silent killer of Harness KPIs: every gate stays green while the
underlying guarantee evaporates.

## Three classes of drift (each with a `qcloud-skills` instance)

### 1. Threshold drift
Spec declares a number; code enforces a smaller (or different) number.

**Instance:** `docs/superpowers/specs/2026-07-28-harness-engineering-optimization-design.md`
says "≥5 golden scenarios per executable skill". `scripts/build_skill_registry.py --check`
enforced "≥1 parseable JSON, with `eval_queries.json` as fallback". KPI#3
passed for 30/31 skills while covering nothing. Fixed in commits
`490df0a` / `041b601` (Sep 2026).

### 2. Source drift
Spec references a field; code does not read it.

**Instance:** Spec schema requires `safety.plan_hash` (Phase 3 token-to-plan
binding). `scripts/gcl_runner.py:879` hardcoded `"plan_hash": None` instead
of reading the value computed by `harness_safety.plan_hash(args.command)`.
The audit trail was permanently missing the field, even when the runtime
check actually fired (caught at `gcl_runner.py:1131`, except
`PermissionError` from `bind_token` raised at `harness_safety.py:70`).
Fixed in `e511508` (this PR series).

### 3. Behavior drift
Spec describes an active mechanism; code's "stub" simulates the mechanism
without executing it.

**Instance:** Spec Phase 3 says "refuses execution unless token matches
plan_hash of the specific execution plan". `gcl_runner.py` raised
`PermissionError` correctly (caught at `gcl_runner.py:1131`, raised at
`harness_safety.py:70` from `bind_token`), but the evidence record written
immediately after had `plan_hash: None`. Downstream `validate_evidence_schema.py`
saw the missing field and reported KPI#2 as **pass** because the schema
validator only required `leak_checked: true` for non-destructive ops —
not a `plan_hash` non-null check for destructive ones. Three drift classes
stacked: threshold (no non-null rule), source (no read), behavior (no
evidence that the active check ran).

## Detection: the four checks

Run all four on every PR that touches `scripts/` or `docs/superpowers/specs/`.

### Check 1 — Numeric grep

```bash
# Extract numbers from spec text
rg -on '\b[><=!]+\s*\d+\b' docs/superpowers/specs/ | sort -u
# Extract numbers from code assertions
rg -n 'assert.*[<>=!].*\d|exit.*\d|raise.*\d' scripts/ | sort -u
# Diff manually: are spec numbers reflected in code?
```

### Check 2 — Field-name parity

For each `safety.*`, `provenance.*`, `budgets.*` field named in the spec's
JSON schema, grep `scripts/` for both the read (extraction) and the write
(serialization). A field that is written but never read is suspect.

### Check 3 — Runtime cross-check

Run the script that the spec describes, then read the produced artifact.
If the spec says "evidence record must have non-null `safety.plan_hash`"
but every produced record has `plan_hash: null`, drift exists regardless
of what the code claims.

```bash
python3 scripts/gcl_runner.py --check ...     # produce evidence
rg '"plan_hash":\s*null' audit-results/evidence-*.json   # count nulls
```

### Check 4 — Negative test

Construct a scenario that **should** fail per the spec (destructive
command without token), run it, and confirm the script fails. If it
passes, the spec's safety guarantee is not enforced — regardless of
exit-code-by-luck.

For Phase 3 token binding: run `python3 scripts/gcl_runner.py --help`
first to confirm the exact `--command` / env-var interface, then write
the negative test against that real interface. **Do not invent flag
names** — the negative test is worthless if it fails for the wrong reason.

## One-shot detector (drop into `scripts/detect_spec_drift.py`)

The four checks above are mechanically scriptable. The detector reads
spec files, extracts numeric and field-name claims, scans `scripts/` for
the matching assertions, and emits a Markdown diff. A single
`make drift-check` target is enough.

## Fix-on-find rule

**Fix drift in the same change set, not as a follow-up ticket.** A
follow-up ticket is a drift that the team has agreed to live with for
some time. That is enough time for the next drift to compound it.

The KPI#3 fix (`490df0a`, Sep 2026) followed this rule: spec drift
detected → fix scripted → test ran → CI gate hardened → all in one PR.
A later PR could safely build on a green KPI#3 instead of an illusory
one.

## Anti-patterns

- **"Aligned with spec" in the PR description.** Words, not verification.
  A drift detector's output is verification.
- **Spot-checking two numbers.** Specs have dozens of claims; check them
  all or admit you are sampling.
- **Verifying exit code 0.** Exit 0 is necessary, not sufficient. Check
  the artifact the script produced.
- **Trusting the spec to update itself.** Specs rot the same way code
  does. Run the drift detector against `main` weekly, not just on PRs.
