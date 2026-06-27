# Commit Hygiene Trial — Run Book

**Status**: trial phase. Trial ends when (a) cumulative commits ≥ 5 AND M1 = 0 AND M2 ≤ 20%, OR (b) operator manually terminates.

## Goal

Verify that the agent can autonomously decide commit granularity while
respecting the 6 hard-stop rules declared in `AGENTS.md` ("Commit hygiene"
section). Trial window: weekly cadence, indefinite until termination.

## Metrics

| ID | Metric | Threshold | Source | Severity |
|----|--------|-----------|--------|----------|
| M1 | Hard-stop violations | = 0 (zero tolerance) | Self-reported by agent when triggering a stop | Critical |
| M2 | Granularity rollback rate | ≤ 20% | Operator 👎 count / commits in window | Warning |

M1 = 0 is non-negotiable. Any violation terminates trial immediately
and triggers a rule review.

## Commit Trailer (non-mandatory but recommended)

Agent MAY append the following trailers to each commit message. Missing
trailers count as a mild M2 deviation (recorded, but not failing).

```
Commit-Hygiene-Verdict: ok | partial | red-line-stop
Commit-Hygiene-Products: cvm,cos
Commit-Hygiene-Files-Modified: 3
Commit-Hygiene-Files-Added: 1
Commit-Hygiene-Reason: <one-line why this granularity>
```

Field semantics:
- `Verdict`: `ok` (clean), `partial` (some uncertainty), `red-line-stop` (trial paused).
- `Products`: which `qcloud-*-ops` skills were touched (empty if none).
- `Files-Modified` / `Files-Added`: counters for traceability.
- `Reason`: free-text justification, surfaces the granularity decision.

## Weekly Pipeline (GitHub Actions)

Trigger: every Monday 09:00 UTC+8 (cron: `0 1 * * 1`).

| Step | Script | Action |
|------|--------|--------|
| 1. Collect | `scripts/commit_hygiene_trial.py collect` | Read `git log` past 7 days, parse trailers, append to `audit-results/commit-hygiene-trial.jsonl` |
| 2. Score | `scripts/commit_hygiene_score.py` | Compute M1 / M2, append to `audit-results/commit-hygiene-trial-scores.jsonl` |
| 3. Report | `scripts/commit_hygiene_trial.py report` | Generate `docs/commit-hygiene-trial-report-YYYYMMDD.md`, update `docs/commit-hygiene-trial-index.md` |
| 4. Commit | Action's auto-commit | Commit jsonl + report back to repo under one `[trial] weekly snapshot YYYYMMDD` commit |

If collect/score fails: action logs and exits silently (per P4).
Operator will see the failure as a missing weekly commit.

## Termination

| Trigger | Condition | Action |
|---------|-----------|--------|
| Auto-soft | ≥ 5 commits AND M1=0 AND M2≤20% | Weekly report recommends "升档"; operator promotes rules to canonical doc, removes Action + scripts |
| Manual-hard | Operator says "试运行结束" at any time | Same as above, fast-track (metric pass not required) |

## Files Layout

```
audit-results/
  commit-hygiene-trial.jsonl            # raw facts, weekly append, in git (S1)
  commit-hygiene-trial-scores.jsonl     # score snapshots, weekly append, in git
docs/
  commit-hygiene-trial.md               # this file
  commit-hygiene-trial-index.md         # auto-updated weekly index
  commit-hygiene-trial-report-YYYYMMDD.md  # one per week
.github/workflows/
  commit-hygiene-trial.yml              # weekly scheduler
scripts/
  commit_hygiene_trial.py               # collect + report
  commit_hygiene_score.py               # pure scoring logic
```

## See Also

- `AGENTS.md` — "Commit hygiene" rules this trial validates
- `.github/workflows/validate-skills.yml` — pattern reference for weekly Action