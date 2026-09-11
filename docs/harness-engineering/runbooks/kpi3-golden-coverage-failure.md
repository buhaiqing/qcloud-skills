# KPI#3 Failure Runbook — golden coverage ≥5

## Symptom

`make kpi-gates` shows:

```
❌ fail | KPI#3 golden coverage | <skill>: missing assets/golden/ directory
❌ fail | KPI#3 golden coverage | <skill>: 3 golden scenario(s) (spec KPI#3 requires >=5)
```

## First diagnosis

```bash
python3 scripts/build_skill_registry.py --check
```

Lists every failing skill. The two messages map to two different
shapes of failure:

- `missing assets/golden/ directory` → no golden dir at all
- `N golden scenario(s) (spec KPI#3 requires >=5)` → dir exists but <5

## Root cause variants

**V1: New skill added, no golden yet.** Any new `qcloud-*-ops/` skill
with `cli_applicability: dual-path` or `sdk-only` is auto-required.
Bootstrapping via the seed generator is one option; hand-authored
goldens are the production target.

**V2: Author removed goldens during a refactor.** `git log` on the
golden dir; revert the offending commit if unintentional.

**V3: A golden file is unparseable JSON.** `_is_valid_json` skips it
silently, so it does not count toward the ≥5 floor. Run:

```bash
for f in qcloud-XXX-ops/assets/golden/*.json; do
  python3 -c "import json; json.load(open('$f'))" 2>&1 | grep -q Error && echo "BAD: $f"
done
```

**V4: Spec drift.** If the spec text was changed to a different number
(e.g. ≥3) but the code still enforces ≥5, this runbook is wrong and
should be regenerated. Check
`docs/superpowers/specs/2026-07-28-harness-engineering-optimization-design.md`
Phase 1.

## Fix command

```bash
# For new/empty: seed scaffolding (replace seeds by hand-authored goldens later)
python3 scripts/generate_golden_seeds.py
# For unparseable JSON:
python3 -m json.tool qcloud-XXX-ops/assets/golden/broken.json > /tmp/fixed.json
mv /tmp/fixed.json qcloud-XXX-ops/assets/golden/broken.json
```

## Verification

```bash
python3 scripts/build_skill_registry.py --check
# expect: "KPI#3 OK: all executable skills have golden samples"
make kpi-gates | grep KPI#3
# expect: ✅ pass
```
