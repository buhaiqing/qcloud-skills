# KPI Design Pattern

Every KPI a Harness enforces must clear **8 attributes**. Skip any and you
end up with a KPI that nobody trusts, that fires on false positives, or
that nobody knows what to do when it fails.

## The 8 attributes

| # | Attribute | Definition | Failure if missing |
|---|-----------|------------|--------------------|
| 1 | **Observable** | The KPI can be measured from existing artifacts (traces, files, registry) without inventing instrumentation | KPI is invisible until somebody runs it manually |
| 2 | **Thresholded** | A target value exists and is checked by a script (not by human judgement) | Drift goes unnoticed; "good enough" becomes permanent |
| 3 | **Authoritative source** | One canonical place emits the value; all consumers read from it | Two scripts compute it differently; one becomes truth, the other a lie |
| 4 | **Skip-aware** | Missing data is reported as `skipped`, not `fail` (so pre-evidence repos do not perpetually break) | Empty repo fails CI forever; pre-existing state becomes unfixable debt |
| 5 | **Aggregatable** | A single run yields a row; many runs yield a trend (in `audit-results/`) | One-shot insight with no longitudinal view |
| 6 | **Failure-mode-defined** | For each threshold, the runbook says: who fixes it, what file they touch, what command they run | Alert fires; nobody knows what to do |
| 7 | **CI-hooked** | Wired into `make <target>` so a single command fails the build | KPI exists only as a doc nobody reads |
| 8 | **Drift-detectable** | A change to the producer (spec, generator) is checked against the KPI (e.g. spec says "≥5", code says "≥1") | Spec grows, code shrinks; KPI silently passes forever |

## Template

```yaml
# KPI#N — <one-line statement of what we claim>
observable:    <file path or trace field>
threshold:     <operator><value>           # e.g. ">=5", "==0", "<2%"
source:        <authoritative emitter, single file>
skip_when:     <condition that yields SKIP not FAIL>
aggregation:   <how multiple runs combine>
failure_mode:  <who + where + how to fix>
ci_hook:       <Makefile target + script>
drift_check:   <script that compares spec phrase vs code assertion>
```

## Real examples from `qcloud-skills`

### KPI#3 — Golden coverage per executable skill ≥5

```yaml
observable:    qcloud-*-ops/assets/golden/*.json
threshold:     ">=5"
source:        scripts/build_skill_registry.py --check
skip_when:     never  # always enforceable from registry
aggregation:   audit-results/skill-registry.json (per-skill count)
failure_mode:  Author of the affected skill writes 5 golden JSON
ci_hook:       make kpi-gates
drift_check:   docs/superpowers/specs/2026-07-28-harness-engineering-optimization-design.md
               vs build_skill_registry.py --check implementation
```

**Drift case study (2026-09):** Spec said `>=5`. Code allowed `eval_queries.json`
fallback, so 30/31 skills passed without any golden file. KPI was passing
while being meaningless. Fix landed in commit `490df0a` / `041b601`:
removed fallback, raised threshold.

### KPI#7 — Router top-1 / misdelegation / fallback observable

```yaml
observable:    audit-results/router-confusion.json (per skill)
threshold:     ">=0.28 ratchet, <=0.16 misdelegation ceiling (target 0.70)"
               # assets/shared/thresholds.json; both arms from the measured baseline
source:        scripts/harness_router.py:confusion_matrix
skip_when:     skill has no assets/eval_queries.json, or is not scoreable
               (empty intent_keywords); <= half the registry scoreable fails
aggregation:   kpi-gate-report.json (avg across *scoreable* skills; the
               excluded skills are named in the detail string)
failure_mode:  Improve intent_keywords in qcloud-*-ops/SKILL.md frontmatter
               (runbook: runbooks/kpi7-router-confusion-failure.md)
ci_hook:       make kpi-gates; CI step "KPI gates" in
               .github/workflows/validate-skills.yml (blocking; step 16 of 17
               named steps, so it executes only if every preceding step is green:
               a red step 1 aborts the job before this runs — see obs. 7)
drift_check:   none — definition is self-evident
```

**Aggregation basis (2026-09-19).** Both arms are averaged over skills the
router can actually return — a registry skill with `intent_keywords: []`
scores a structural 0.0 on every positive *and* a structural 0.0 on
misdelegation, so averaging it in dilutes both arms. 15 of 31 registry skills
are in that state, which is why the honest figures differ by 2× from the
registry-wide average:

| basis | skills | avg top1 | avg misdelegation |
|---|---|---|---|
| all registry skills (round 1) | 31 | 14.59% | 7.85% |
| scoreable (non-empty `intent_keywords`) | 16 | **28.28%** | **15.21%** |
| reachable (ever returned as top1) | 11 | 41.13% | 22.12% |

Pooled over positives, the scoreable set is 46/161 = 28.57%; over the full
36-directory corpus round 1 measured 46/466 = 9.87%. Fallback (queries
matching no skill) is **51.64%** over the 31 registry skills — the router's
single most informative number, and until now a hardcoded `0.0`.

**Metric-integrity case study (2026-09):** KPI#7 used to be threshold-less *and*
its metric was a constant. `harness_router.confusion_matrix` decided correctness
by looking up `q["intent"]` in the top-1 skill's `intent_keywords`, but only 7 of
36 `eval_queries.json` files carry an `intent` key — for the other 29 the lookup
compared `None`, so `top1_accuracy` and `misdelegation` were structurally `0.0`.
(Same split on the 31-skill executable registry: 24 of 31 files carry none — the
other 7 do. `29` is the *corpus* numerator and does not pair with the registry
denominator.)
The gate printed `avg top1=14.72%` (a different, phantom quantity) and returned
**PASS** with no threshold to cross. Measured honestly against owning-skill
ground truth the same router scores **9.87% (46/466 positive queries)** across
all 36 skill directories, with 26 skills at 0.0. Same lesson as the KPI#3 drift
case study above: *a KPI that passes while measuring nothing is worse than no
KPI* — the anti-pattern below. The metric was rebuilt on owning-skill labels and
ratcheted at the measured baseline, with an explicit 0.70 target whose gap is
printed on every run.

**Second pass (2026-09-19).** Round 1 ratcheted at 0.10 against a metric whose
denominator was still wrong: it averaged in 15 skills the router cannot return
(see the aggregation basis table above), so the movers sat at 15.21%
misdelegation against a bound derived from the *aspirational* target
(`1 - 0.70 = 30%`), i.e. 4× headroom that only the 11 reachable skills could
ever close. Both ratchets now come from the same measured baseline
(0.28 / 0.16) and the excluded skills are named in the detail string. Both sit
within a percentage point of the measurement they came from (0.28 vs 28.2755%,
0.16 vs 15.2083%). Granularity is sub-percentage-point: one flipped query moves
the *average* by `1 / (positives × 16)`, from **0.2315pp** in the largest
scoreable skill (`qcloud-cvm-ops`, 27 positives) to **2.0833pp** in the smallest
(3 positives). The ratchet's headroom is only 0.2755pp, so that single query trips
the floor in **15 of the 16 scoreable skills**; `qcloud-cvm-ops` alone absorbs one
flip, and a second trips it. The ratchet is therefore not a guard against
*meaningful* regression — for nearly the whole fleet it fires on the smallest
possible move, which makes it a near-"no degradation at all" floor rather than a
rubber stamp (obs. 8).

> ⚠️ **The ratchet is self-referential — know what that buys.** `router_min_top1_accuracy`
> and `router_max_misdelegation` live in `assets/shared/thresholds.json`, which
> ships in the same tree the gate grades: the commit that measures a new value
> can also lower the floor to it. That is *not* a claim that "no KPI number is
> hardcoded" — the number simply moved into a reviewed, single-source file. The
> real protection is the diff review of `thresholds.json` (a ratchet change is a
> visible line in the PR) and the failure-mode runbook; it is not a property of
> the gate. Treat any PR that lowers a ratchet without a matching runbook note as
> a KPI weakening, not a KPI fix.

> ⚠️ **Threshold-less KPIs are settled here: don't ship one.**
> The "observable only" option was the state this KPI shipped in, and the result
> was a ✅ that survived months of telling nobody anything — the *KPI that always
> passes* anti-pattern listed below, reached through the threshold door instead of
> the drift door. A threshold taken from the **measured baseline** (even a bad
> one) is strictly better than no threshold: it makes today's number the floor
> and turns every regression into a failure. If the current value is nowhere near
> a useful target, ratchet at the baseline *and* print the gap against the target
> — see [spec-drift-gate.md](./spec-drift-gate.md) for detecting when an
> "observable only" KPI has silently stopped being useful.

## Anti-patterns

- **KPI with no consumer.** Computing a metric nobody reads. Fix: either
  CI-hook it or remove it.
- **KPI computed in three places.** Whoever owns one of them will be
  wrong. Fix: collapse to one authoritative source.
- **KPI that fails on empty repos.** Every new repo fails CI forever.
  Fix: skip-aware semantics; ensure the gate also fires when data appears.
  Make the skip an explicit opt-out (`GATE_REQUIRE_EVIDENCE=0`), never the
  default reading of an empty file — otherwise deleting the data *is* the fix
  (see observation 4).
- **KPI that "always passes".** Worse than no KPI — gives false confidence.
  Fix: drift_check or remove.
- **KPI with no failure-mode runbook.** Alert fires at 3am; nobody knows
  what to do. Fix: write the failure_mode row.

## Case study: scoring qcloud-skills KPIs against the 8 attributes

The 8 attributes are not a checklist for show. Applied to the four KPIs
that `make kpi-gates` actually enforces today (Sep 2026), the matrix is:

| Attribute | KPI#1 leak | KPI#2 token | KPI#3 golden | KPI#7 router |
|-----------|------------|-------------|--------------|--------------|
| Observable | ✅ | ✅ | ✅ | ✅ |
| Thresholded | ✅ `evidence_min_records` / `evidence_max_age_days` — **neither has fired on real data** (obs. 6) | ✅ same | ✅ | ✅ ratchet 0.28 / ceiling 0.16, target 0.70 (gap printed); plus a registry floor, `router_min_registry_skills` |
| Authoritative source | ✅ | ✅ | ✅ | ✅ |
| Skip-aware | ✅ an absent, short or aged-out stream FAILS — **unless** `GATE_REQUIRE_EVIDENCE=0`, which returns before any file is read and so skips all three; CI never sets it (obs. 4) | ✅ same | ✅ | ⚠️ never skips in practice |
| Aggregatable | ✅ | ✅ | ✅ | ✅ |
| Failure-mode-defined | ✅ [rb1](./runbooks/kpi1-leak-checked-failure.md) | ✅ [rb2](./runbooks/kpi2-destructive-token-plan-hash-failure.md) | ✅ [rb3](./runbooks/kpi3-golden-coverage-failure.md) | ✅ [rb7](./runbooks/kpi7-router-confusion-failure.md) |
| CI-hooked | ✅ `make kpi-gates` locally; the **blocking** "KPI gates" step in `validate-skills.yml` stages `scripts/fixtures/evidence/` and asserts the clean fixture passes *and* the violating one exits 1 (obs. 7). The fleet stream is never graded in CI — it cannot be. **Conditional:** the step is step 16 of 17 and runs only if every preceding step is green, so a red step 1 skips it silently (obs. 7) | ✅ same (same step, same condition — obs. 7) | ✅ same step, same condition (obs. 7) | ✅ `make kpi-gates`, **blocking** CI step "KPI gates" in `validate-skills.yml` — step 16 of 17, so conditional exactly as the first column (obs. 7) |
| Drift-detectable | ⚠️ | ⚠️ | ✅ | ⚠️ |

**Observations:**

1. **KPI#3 is the strongest.** All 8 attributes are addressed (with
   "generic" failure-mode as the only weakness). That is the level other
   KPIs should aim for.
2. **"Failure-mode-defined" is the universal weak spot.** All four KPIs
   have a generic failure_mode line; none has a one-click runbook that
   tells the on-call engineer exactly which file to open and which
   command to run. Fixing this for KPI#3 alone would halve the time to
   recover from a Golden regression.
   *(Resolved 2026-09: see [./runbooks/](./runbooks/) — each KPI now has
   a concrete runbook with file paths, commands, and verification steps.)*
3. **KPI#7's ⚠️ rows were real, and are now closed.** The missing target was
   not a display problem: with no threshold, nothing forced anyone to notice
   that the metric underneath was a constant (see the metric-integrity case
   study above). It now ratchets at the measured baseline (0.28 / 0.16) against
   a 0.70 target, and prints the gap while it sits below target.
4. **"Skip-aware" was over-applied to KPI#1/#2.** Attribute 4 exists so a *new*
   repo is not red forever; it was implemented as "empty stream → ✅ skip", which
   also meant a *truncated* stream scored better than a full one — zero evidence
   graded as evidence. The attribute is now bounded by a floor: the honest option
   for a repo with no evidence is an explicit `GATE_REQUIRE_EVIDENCE=0` skip that
   says so, not a silent pass. Prefer the escape to a permissive default: an
   opt-out is auditable in the CI file, a default is invisible.
   *Correction (2026-09-20):* that escape is a **total** escape — it returns
   before the glob, so with it set an absent, a present-but-empty and an
   aged-out stream all `skip`, and a safety KPI can never fail the build. It is
   an opt-out for machines that are *deliberately* evidence-free, not a floor
   and not a freshness check; CI no longer sets it (obs. 7).
5. **Drift detection is uneven.** Only KPI#3 has a working
   drift-detector (the threshold-drift case in
   [spec-drift-gate.md](./spec-drift-gate.md)). The other three could
   silently rot.
6. **The two evidence thresholds have never fired on real data.** Every stream
   measured so far — 357 and 550 records — reported `0 aged-out`, and none was
   near the floor of 10, so `evidence_min_records` / `evidence_max_age_days` are
   asserted only by tests and by the CI fixture. They are not arbitrary (10
   records / 90 days are reasonable values), but the **first** time they fire
   will also be the first time anyone sees them work — read
   [rb1](./runbooks/kpi1-leak-checked-failure.md) V4/V5 before touching them.
   Both are genuinely exercised by `scripts/fixtures/evidence/`: 12 fresh records
   (above the floor) and 3 dated 2020 (aged out, reported and not counted).
7. **For KPI#1/#2, "CI-hooked" now means a fixture, not the fleet.** Evidence
   records are *output* of the code under review, so no CI job can grade the
   fleet's behaviour offline. What CI can prove — and the blocking "KPI gates"
   step now does — is that the safety **rules** are alive: the committed clean
   fixture must pass and the committed violating fixture must exit 1.
   `GATE_EVIDENCE_GLOB` names the graded set and the step writes that file
   itself, so the verdict cannot come from whatever else sits in
   `audit-results/` on the runner: that directory is machine-local and holds no
   fleet evidence, only the records earlier steps left there (the workflow's own
   smoke test writes one today; the unit-test step minted 17 more until it was
   isolated in 2026-09, which is what the old escape was hiding).
   **The step is blocking, but its *execution* is conditional — and that gap is
   the whole point.** "KPI gates" is step 16 of 17 named steps in the `validate`
   job, and Actions runs steps sequentially and aborts the job at the first
   failure that is not `continue-on-error`. So a red step 1 (Ruff) aborts
   everything downstream, this gate is never executed, and the run reports a
   Ruff failure with no KPI verdict at all — a red run is honest, but a *green*
   run proves only "nothing upstream was red". It never, on its own, proves the
   KPI gate ran or passed. Read the step list, not the run badge. This is a
   property of CI step order rather than of the gate, and it is why `CI-hooked`
   in the matrix above is stated as conditional rather than absolute: the claim
   to make about this step is "wired and blocking, and positioned 16th, so it
   executes only when everything before it is green" — a claim that stays true
   whether or not step 1 happens to be green today.
8. **KPI#7's ratchet has sub-percentage-point granularity.** `0.28` sits
   0.2755pp under the measured 28.2755% (the misdelegation ceiling is 0.79pp
   under its own baseline). The smallest reachable step is one flipped query,
   worth `1 / (positives × 16)` of the average: 0.2315pp in the largest scoreable
   skill (`qcloud-cvm-ops`, 27 positives) and 2.0833pp in the smallest (3). No
   scoreable skill has 5 positives (the set is 3, 4, 6, 7, 7, 8, 9, 10×7, 20,
   27), so the ≥1.25pp figure is not a floor — it is the step for a skill size
   that does not occur here. Because the 0.2755pp of headroom exceeds the
   0.2315pp step and nothing above it, one flipped query trips the floor in 15 of
   the 16 scoreable skills; `qcloud-cvm-ops` absorbs exactly one. Read literally that is "no degradation
   at all" for nearly the whole fleet: a legitimate coverage change (a new hard
   positive) can trip it, and the printed `BELOW TARGET 70.00%` gap understates
   how tight the floor is. The *ceiling* arm is the loose one by contrast: its
   0.79pp of headroom absorbs the step in the 7 skills carrying ≥10 negatives, so
   one flipped negative trips it in only the other 9 — the ceiling is the weaker
   of the two signals, not the tighter. Treat a first-time KPI#7 failure as "a query
   moved" until the diff says otherwise; the value is deliberately left where
   the measurement put it, because 0.28 is the measured 28.2755% rounded down
   and the granularity above is exactly what makes it fire on a one-query move.



> **H-53 update:** `router_min_top1_accuracy` now has a buffer zone.
> Effective fail floor = `min_top1 - noise_band - meaningful_regression`
> (defaults: 0.015 + 0.025; see `assets/shared/thresholds.json`). Measured
> accuracy in `(effective_floor, min_top1)` reports `pass` with a noise-band
> note; below `effective_floor` reports `fail`. This guards against false
> positives on single-skill flips while still tripping on regressions.
> Per-skill noise bands are recomputed at runtime from query-set size; the
> 1.5pp fleet-level floor is a 95th-percentile worst case, not a guardrail
> for any single skill.

**Use this template to score your own KPIs.** A KPI with two ⚠️ rows
is acceptable; four is a smell. If a KPI has ⚠️ on Failure-mode-defined
AND Drift-detectable, treat it as a known-loose KPI and schedule a
tightening pass.
