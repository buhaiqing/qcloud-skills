# Pre-Merge Self-Review Checklist

Run through this **before `git push`** — not after the PR is open and
not when CI is red. Each item is a class of bug that escaped review
at least once in this repo. Items are deliberately short; if you need
explanation, the linked runbook / spec doc has it.

## 5 operational checks

Each item below names a *concrete* verification command. "I think it's
fine" is not a verification.

### 1. Worktree hygiene (root cause: shared working tree)

`git worktree remove` does not roll back disk changes. A deleted
worktree can leave `main`'s working tree dirty.

```bash
# After ANY worktree remove, before continuing:
git -C <main-repo> status --short   # must be empty
```

If dirty: `git -C <main-repo> checkout -- <files>` before doing
anything else. Do not merge a feature branch while main is dirty.

### 2. Tool path resolution inside worktrees (root cause: relative paths)

`ruff`, `python3 scripts/...`, and similar resolve `.` against the
caller's cwd, which inside a worktree is the worktree's directory —
but inside an IDE or pipe, `.` may resolve to the parent checkout
and silently lint the wrong tree.

```bash
# Inside a worktree, prefer absolute paths for tools that read from cwd:
ruff check /Users/.../worktree-name   # not: ruff check .
```

If you cannot use absolute paths, run the tool from `cd <worktree>`
**before** invoking it.

### 3. Subagent task profile (root cause: silent 0-output exits)

This repo's `subagent` tool has been observed (3 consecutive runs in
Sep 2026) to exit with **no output and no work** when the prompt
contains:

- > ~600 characters of structured scope_lock rules
- "write ≤N lines of structured markdown" tasks
- prompts where the model must infer the file's structure

**Default rule: do not use subagent for documentation writes.** This is
the single category where 0-output exits were observed 3-for-3 in
Sep 2026. Other categories (bulk data generation, scripted refactors,
lint sweeps) were not observed to fail the same way — they may be
fine, but the verify-after rule still applies because "not observed"
is not "guaranteed safe".

```bash
# Verify after EVERY subagent task, regardless of category:
ls <expected-file> && git diff --stat <expected-path>
```

### 4. Code references in docs (root cause: line numbers rot)

Runbooks and design docs name file:line locations. Those rot the
moment any PR changes the file. Before commit:

```bash
# For each "see scripts/X.py:N" reference in your new doc:
sed -n '<N>p' scripts/X.py | grep <expected-content>
```

If the line content does not match, fix the doc — never commit a doc
that points at the wrong line. This is the same discipline that
[kpi-pattern.md — The 8 attributes](./kpi-pattern.md#the-8-attributes)
imposes on KPI checks (Drift-detectable row); apply it to prose too.

### 5. No phantom deliverables (root cause: README lies)

Indexes and READMEs are read first and trusted longest. An index that
lists `foo.md` as Ready when `foo.md` does not exist becomes a lie
that future contributors repeat.

```bash
# Before commit, for every link in README.md / docs index:
for f in $(rg -o '\]\(\./[a-z-]+\.md\)' README.md | sed 's/.*(\.\///;s/)$//'); do
  test -f "$f" || echo "MISSING: $f"
done
```

If any link is missing, either:
- create the file in this same change set (fix-on-find rule), or
- mark the row as `⏳ Pending` with a concrete trigger condition
  (e.g. "needs ≥2 cross-project usage to validate").

**Never** silently leave a Ready row pointing at a non-existent file.

## When NOT to run this checklist

- Trivial typo fixes (<5 lines, no logic change) — the AGENTS.md
  exception clause applies.
- Pure reformat / import-sort / ruff --fix — already covered by
  CI gates; do not double-audit.

## Cross-references

- [spec-drift-gate.md](./spec-drift-gate.md) — drift detection
  methodology
- [kpi-pattern.md § Case study](./kpi-pattern.md#case-study-scoring-qcloud-skills-kpis-against-the-8-attributes)
  — which attributes this checklist protects
- [Failure runbooks](./runbooks/) — what to do when a CI gate fires

## Provenance

Every item in this checklist was extracted from a real bug found in
`qcloud-skills` PRs (Sep 2026 series). Items 1 and 4 each bit the
session twice (same shape, different feature branches), item 3 bit
three times consecutively, items 2 and 5 each bit once. The
checklist is deliberately short because each item must be
remembered; the long version is a smell.
