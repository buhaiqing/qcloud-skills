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
threshold:     ">=0.10 ratchet (target 0.70)"  # assets/shared/thresholds.json
source:        scripts/harness_router.py:confusion_matrix
skip_when:     skill has no assets/eval_queries.json
aggregation:   kpi-gate-report.json (avg across skills)
failure_mode:  Improve intent_keywords in qcloud-*-ops/SKILL.md frontmatter
               (runbook: runbooks/kpi7-router-confusion-failure.md)
ci_hook:       make kpi-gates; CI step "KPI gates" in
               .github/workflows/validate-skills.yml (blocking)
drift_check:   none — definition is self-evident
```

**Metric-integrity case study (2026-09):** KPI#7 used to be threshold-less *and*
its metric was a constant. `harness_router.confusion_matrix` decided correctness
by looking up `q["intent"]` in the top-1 skill's `intent_keywords`, but only 7 of
36 `eval_queries.json` files carry an `intent` key — for the other 29 the lookup
compared `None`, so `top1_accuracy` and `misdelegation` were structurally `0.0`.
(Same split on the 31-skill executable registry: 29 of 31 files carry none.)
The gate printed `avg top1=14.72%` (a different, phantom quantity) and returned
**PASS** with no threshold to cross. Measured honestly against owning-skill
ground truth the same router scores **10.3% (48/466 positive queries)**, with 26
skills at 0.0. Same lesson as the KPI#3 drift case study above: *a KPI that
passes while measuring nothing is worse than no KPI* — the anti-pattern below.
The metric was rebuilt on owning-skill labels and ratcheted at the measured
baseline (0.10) with an explicit 0.70 target whose gap is printed on every run.

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
| Thresholded | ✅ | ✅ | ✅ | ✅ ratchet 0.10, target 0.70 (gap printed) |
| Authoritative source | ✅ | ✅ | ✅ | ✅ |
| Skip-aware | ✅ | ✅ | ✅ | ⚠️ never skips in practice |
| Aggregatable | ✅ | ✅ | ✅ | ✅ |
| Failure-mode-defined | ✅ [rb1](./runbooks/kpi1-leak-checked-failure.md) | ✅ [rb2](./runbooks/kpi2-destructive-token-plan-hash-failure.md) | ✅ [rb3](./runbooks/kpi3-golden-coverage-failure.md) | ✅ [rb7](./runbooks/kpi7-router-confusion-failure.md) |
| CI-hooked | ✅ | ✅ | ✅ | ✅ `make kpi-gates`, **blocking** CI step "KPI gates" in `validate-skills.yml` |
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
   study above). It now ratchets at the measured baseline (0.10) against a 0.70
   target, and prints the gap while it sits below target.
4. **Drift detection is uneven.** Only KPI#3 has a working
   drift-detector (the threshold-drift case in
   [spec-drift-gate.md](./spec-drift-gate.md)). The other three could
   silently rot.

**Use this template to score your own KPIs.** A KPI with two ⚠️ rows
is acceptable; four is a smell. If a KPI has ⚠️ on Failure-mode-defined
AND Drift-detectable, treat it as a known-loose KPI and schedule a
tightening pass.
