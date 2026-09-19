# KPI#7 Failure Runbook — router confusion matrix

## Symptom

`make kpi-gates` shows:

```
❌ fail | KPI#7 router confusion matrix | missing skill-registry.json; run build_skill_registry --emit first
❌ fail | KPI#7 router confusion matrix | no skill produced a confusion matrix (missing eval_queries.json everywhere)
❌ fail | KPI#7 router confusion matrix | 31/31 skills scored; avg top1=8.90% avg misdelegation=7.85% — below ratchet 10.00%
❌ fail | KPI#7 router confusion matrix | 31/31 skills scored; avg top1=14.59% avg misdelegation=45.00% — above derived misdelegation bound 30.00%
```

Or — when KPI#7 passes but the avg `top1_accuracy` drops sharply vs
`audit-results/router-confusion.json` history — the gate is thresholded
(`assets/shared/thresholds.json`: ratchet 0.10, target 0.70) and **blocks
CI**, so a drop below the ratchet fails the build while a drop that stays
above it is only visible in the detail string and the trend.

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

## Fix command

```bash
# Standard recovery
make registry          # refresh audit-results/skill-registry.json
make kpi-gates         # re-run gate
```

## Verification

```bash
make kpi-gates | grep KPI#7
# expect: ✅ pass — "<N>/31 skills scored; avg top1=X.XX% avg misdelegation=Y.YY%"
#         plus "(BELOW TARGET 70.00% — …)" while the router is below target
diff <(jq -S . audit-results/router-confusion.json) /tmp/last-known.json
# expect: small delta, not a cliff
```

See also: [kpi-pattern.md § Case study](../kpi-pattern.md#case-study-scoring-qcloud-skills-kpis-against-the-8-attributes) for what
counts as a healthy baseline. Today (measured against owning-skill ground truth,
not the phantom `intent` key): avg top1=14.59%, misdelegation=7.85% — the ratchet
is 10.00%, the target 0.70.
