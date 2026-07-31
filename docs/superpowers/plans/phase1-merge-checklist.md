# Phase 1 — Merge Checklist

> **Purpose**: Operational steps for landing `feature/phase1-l3-adaptive-orchestration`
> into `main`, with explicit verification and rollback hooks.
> **Scope**: Doc finalization + CADL L17/L18 (`AGENTS.md`) landed on the branch as a
> single commit by the doc-finalize sub-agent. Code changes (1.1/1.2/1.3 + partial 1.4)
> were landed earlier on the same branch by other sub-agents.
> **Target**: A reviewer / integrator with shell access to both worktrees.

## 1. Pre-merge verification (run from this worktree)

| # | Check | Command | Pass criterion |
|---|-------|---------|----------------|
| 1 | Working tree of doc-only files | `git status --short` | Only `.md` files staged; no stray `.py` edits |
| 2 | Doc diff is the only delta | `git diff --stat main...HEAD` | `.md` lines only; no `qcloud-copilot/copilot/dispatcher.py` etc. inside this commit |
| 3 | Lint clean (Python unaffected by doc commit) | `ruff check scripts/` | exit 0 |
| 4 | Markdown Python SDK lint | `python3 scripts/check_markdown_python.py --root .` | exit 0 |
| 5 | Markdown link lint | `python3 scripts/check_markdown_links.py` | exit 0 |
| 6 | Frontmatter validator | `python3 scripts/validate_skills_frontmatter.py` | exit 0 |
| 7 | Skill registry schema check | `python3 scripts/build_skill_registry.py --output audit-results/skill-registry.json` | exit 0; JSON well-formed |
| 8 | Local full validation | `python3 scripts/validate_local.py` | exit 0 (KPI gate may skip if no `audit-results/evidence-*.json` — expected on clean tree) |
| 9 | Unit tests | `cd scripts && python3 -m unittest discover -p "*_test.py" -v` | "Ran N tests / OK" with N ≥ 360 |
| 10 | CADL hook lint | `python3 scripts/cadl_lint.py` | exit 0 |

If any step fails, **stop** and resolve before proceeding to §2.

## 2. Merge sequence

```bash
# 2.1 Verify doc commit is clean
git log -1 --stat                # should show only .md + L17/L18 lines in AGENTS.md
git diff main...HEAD --stat      # summary of all Phase 1 commits

# 2.2 Merge feature branch into main with non-fast-forward (preserves history shape)
cd /Users/bohaiqing/opensource/git/qcloud-skills
git checkout main
git merge --no-ff feature/phase1-l3-adaptive-orchestration -m \
  "Phase 1: L3 Adaptive Orchestration — merge ADR-0004 + 1.1/1.2/1.3 + CADL L17/L18"

# 2.3 Verify post-merge
git log --oneline -3
ruff check scripts/
python3 scripts/validate_skills_frontmatter.py

# 2.4 Clean up worktree
cd /Users/bohaiqing/opensource/git/qcloud-skills-phase1
git worktree remove ../qcloud-skills --force   # the main worktree, after merge
# (Branch deletion happens from main checkout:)
cd /Users/bohaiqing/opensource/git/qcloud-skills
git branch -d feature/phase1-l3-adaptive-orchestration
```

> **Worktree note**: the phase1 branch lives in the *sibling* worktree at
> `qcloud-skills-phase1/`. The merge command above targets the main worktree's
> `main` branch. The phase1 worktree can be removed after §2.3 verifies success.

## 3. Post-merge validation (main)

| # | Check | Command | Pass criterion |
|---|-------|---------|----------------|
| 1 | HEAD is the merge commit | `git log --oneline -1` | commit message contains "Phase 1" + ADR-0004 |
| 2 | All 9 Phase 1 commits visible in `main` history | `git log --oneline feature/phase1-l3-adaptive-orchestration ^main^` (before deletion) | 9 commits shown; none dropped |
| 3 | ADR table updated | grep "Phase 1 — L3 Adaptive Orchestration" docs/architecture/README.md | status is `Accepted` |
| 4 | AGENTS.md size | `wc -l AGENTS.md` | within 750 lines (was 693, +30 cap) |
| 5 | New L-rules present | grep -E "^### L17|^### L18" AGENTS.md | both rules present |
| 6 | Frontmatter still validates | `python3 scripts/validate_skills_frontmatter.py` | exit 0 |
| 7 | SkillRegistry rebuilt | `python3 scripts/build_skill_registry.py --output audit-results/skill-registry.json` | exit 0 |
| 8 | CI green | push to remote → wait for `.github/workflows/validate-skills.yml` | all jobs green |

## 4. Known deferred items (NOT blockers for merge)

| Item | Why deferred | Owner | Trigger to revisit |
|------|--------------|-------|--------------------|
| 1.1.5 — Real `gcl_runner run --llm-critic` smoke | Requires user-supplied `GCL_LLM_API_KEY`; mock-LLM tests cover contract | User | User provides credentials |
| 1.3.3 — 30 SKILL.md error tables → 6-column format | Parser handles 2-5 column legacy format; migration is optional churn | Future Phase 1.5 | When `validate_error_tables.py` reports inconsistency |
| 1.3.4 — `tcloud_error_codes.py` product sub-codes | MVP in `error_escalator.py` seeds enough to exercise HALT/RETRY/DELEGATE | Future Phase 1.5 | When products report coverage gap |
| 1.4 — Unified observability spans | Parallel sub-agent in flight; dispatcher integration uncommitted | Parallel sub-agent | Same branch; land before delete worktree |
| End-to-end "CVM high CPU → auto-delegate VPC → retry" M3 scenario | Requires 1.3 dispatcher (in progress) + 1.4 spans | Post-1.4 | After 1.4 commit lands |

## 5. Risk register

| Risk | Probability | Impact | Mitigation |
|------|:-----------:|:------:|------------|
| Merge conflict on `AGENTS.md` (L17/L18 vs concurrent edits) | LOW | LOW | Doc-only commit; other branches editing AGENTS.md should rebase |
| `ruff check` regression from 1.3 uncommitted dispatcher changes | LOW | MEDIUM | Re-run ruff before merge; if fails, commit dispatcher changes first |
| `validate_skills_frontmatter.py` complains about the 30 un-migrated SKILL.md error tables | LOW | LOW | Validator is for metadata fields, not error tables — orthogonal |
| Worktree confusion (two `qcloud-skills` worktrees) | MEDIUM | LOW | `git worktree list` before merge; only one main worktree should remain after §2.4 |
| SkillRegistry scan drift between phase1 branch and main | LOW | MEDIUM | Run `build_skill_registry.py` on both; diff outputs |

## 6. Rollback plan

If post-merge validation in §3 fails (e.g. CI red on `main`):

```bash
# 6.1 Identify the merge commit
git log --oneline -3
# 6.2 Revert the merge (keeps history intact)
git revert -m 1 <merge-commit-sha>
# 6.3 Or hard-reset if the failure was detected immediately
git reset --hard HEAD~1   # only if branch was not pushed
```

**Prefer revert over reset** once `main` has been pushed to remote — reset rewrites
shared history. Revert preserves the merge commit so reviewers can inspect what was
reverted.

## 7. Cadence for this checklist

- Update this file when: (a) a new Phase 1 sub-module lands, (b) merge target changes,
  (c) a §4 deferred item is picked up, (d) a §5 risk actually materializes.
- After successful merge, archive this file at
  `docs/superpowers/plans/archive/phase1-merge-checklist-<date>.md` to keep
  `plans/` lean.