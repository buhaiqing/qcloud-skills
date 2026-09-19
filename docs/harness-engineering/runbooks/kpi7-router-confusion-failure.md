# KPI#7 Failure Runbook — router confusion matrix

## Symptom

`make kpi-gates` shows:

```
❌ fail | KPI#7 router confusion matrix | missing skill-registry.json; run build_skill_registry --emit first
❌ fail | KPI#7 router confusion matrix | no skill produced a confusion matrix (missing eval_queries.json everywhere)
❌ fail | KPI#7 router confusion matrix | 16/31 skills scored; avg top1=24.10% avg misdelegation=15.21%; unmeasured: … — below ratchet 28.00%
❌ fail | KPI#7 router confusion matrix | 16/31 skills scored; avg top1=28.28% avg misdelegation=21.00%; unmeasured: … — above misdelegation ceiling 16.00%
❌ fail | KPI#7 router confusion matrix | only 12/31 skills are scoreable (need >= half); unmeasured: qcloud-agsx-ops, …
```

Or — when KPI#7 passes but the avg `top1_accuracy` drops sharply vs
`audit-results/router-confusion.json` history — the gate is thresholded
(`assets/shared/thresholds.json`: ratchet 0.28, misdelegation ceiling 0.16,
target 0.70) and **blocks CI**, so a drop below the ratchet fails the build
while a drop that stays above it is only visible in the detail string and the
trend.

Both arms are averaged over **scoreable** skills — those with a confusion
matrix *and* non-empty `intent_keywords` in the registry. A skill the router can
never return scores a structural 0.0 on both arms, so it is excluded and named
in `unmeasured:`. If that list grows past half the registry the gate fails
outright rather than report a green average over a minority.

## First diagnosis

```bash
ls qcloud-*-ops/assets/eval_queries.json | wc -l   # expect 31
ls audit-results/router-confusion.json              # expect exists after first run
```

## Root cause variants

**V1: eval_queries.json missing for some skill.** `check_kpi_gates.py`
records `{"skipped": "no eval_queries.json"}` for any skill without the
file. Bootstrap:

```bash
cp qcloud-cvm-ops/assets/eval_queries.json qcloud-XXX-ops/assets/
# then edit intent/query pairs to match this skill's domain
```

**V2: skill-registry.json missing.** `kpi7_router_confusion` runs
`build_skill_registry.py --emit` itself; if that fails (e.g.
SKILL.md frontmatter unparseable), the registry is never written.
Fix: read the `build_skill_registry --emit` stderr first.

**V3: Intent keywords too narrow.** avg top1_accuracy < 0.5 means the
frontmatter `intent_keywords` are too sparse to disambiguate. Add
operation aliases from `cli_support_evidence`:

```bash
# In qcloud-XXX-ops/SKILL.md, expand metadata.intent_keywords
# Example: ["DescribeInstances", "RunInstances", "TerminateInstances"]
```

**V4: skill-registry.json stale.** A new skill was added but `make
registry` was not re-run. Add `registry` to the `all` target's
dependencies — actually, `check_kpi_gates.py` already calls
`--emit` inline; this is rare.

**V5: too few skills are scoreable.** The detail reads `only N/31 skills are
scoreable (need >= half)` and names them. A skill becomes unscoreable when its
`eval_queries.json` is missing *or* its SKILL.md frontmatter has empty
`intent_keywords` (the router can never return it, so it measures nothing).

```bash
# who is unmeasured, and why?
jq -r '.skills[] | select((.intent_keywords|length)==0) | .name' audit-results/skill-registry.json
```

Fix: add `metadata.intent_keywords` to that skill's SKILL.md frontmatter
(operation aliases from `cli_support_evidence`) — the same edit that fixes V3.
The gate does not let you fix it by deleting eval_queries.json.

## Fix command

```bash
# Standard recovery
make registry          # refresh audit-results/skill-registry.json
make kpi-gates         # re-run gate
```

## Verification

```bash
make kpi-gates | grep KPI#7
# expect: ✅ pass — "<N>/31 skills scored; avg top1=X.XX% avg misdelegation=Y.YY%; unmeasured: …"
#         plus "(BELOW TARGET 70.00% — …)" while the router is below target
diff <(jq -S . audit-results/router-confusion.json) /tmp/last-known.json
# expect: small delta, not a cliff
```

See also: [kpi-pattern.md § Case study](../kpi-pattern.md#case-study-scoring-qcloud-skills-kpis-against-the-8-attributes) for what
counts as a healthy baseline. Today (measured against owning-skill ground truth,
not the phantom `intent` key): avg top1=28.28%, misdelegation=15.21% over the 16
scoreable skills; 51.64% of queries still route nowhere (`fallback` in
`audit-results/router-confusion.json`). The ratchet is 0.28, the misdelegation
ceiling 0.16, the target 0.70.
