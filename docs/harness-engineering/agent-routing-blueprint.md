# Agent Routing Blueprint

> ⏳ **Pending validation.** This blueprint is the first formal distillation
> of the routing rules the `qcloud-skills` repo has been operating under
> since Sep 2026. It needs ≥2 cross-project usages before being marked
> Ready in `README.md`. Submit findings as PR comments against this file.

**Status:** First draft (2026-09-12). Source evidence: `qcloud-skills`
session of the same date. See [Evidence table](#evidence-table) for
traceable cases.

---

## The decision

When a task arrives, the orchestrator (or human reviewer) faces one
question: **who executes the work — the main agent directly, or a
sub-agent?**

There are three categories:

| Mode | What runs | When to use |
|------|-----------|-------------|
| **Main-direct** | Main agent executes inline; no dispatch | Default for ≤30-line, single-file, deterministic ops |
| **Single subagent** | One sub-agent, isolated context, one handoff | Self-contained code module with a verifiable exit (mutation test, subprocess assertion) |
| **Fan-out** | ≥2 sub-agents in parallel, each owns a disjoint slice | ≥2 truly independent code modules with non-overlapping blast radius |

A fourth mode — **chain** (sub-agent → sub-agent → ...) — is rare in
this repo and is treated as a single subagent with explicit handoff
constraints; see [Chain constraints](#chain-constraints).

## Decision tree

```
Task arrives
  │
  ├─ Q1: Single file / single step / deterministic?
  │    YES → Main-direct
  │    NO  ↓
  │
  ├─ Q2: User says "你自己处理" / "skip orchestrator" / "main 直接做"?
  │    YES → Main-direct
  │    NO  ↓
  │
  ├─ Q3: Task is "write a structured markdown document" (spec / runbook / SKILL.md prose)?
  │    YES → Main-direct (see Evidence row #1) — prose-writer filter; see § Main-direct-5
  │    NO  ↓
  │
  ├─ Q4: Code change >30 lines OR new file OR cross-module?
  │    NO  → Main-direct
  │    YES ↓
  │
  ├─ Q5: ≥2 truly independent slices, each with its own exit criterion?
  │    YES → Fan-out
  │    NO  ↓
  │
  └─ Single subagent with a self-verifiable exit
```

**Coverage of the 5 conditions against the tree:** Q1 = condition 1. Q2 = condition 2. Q3 = condition 5 (prose). Q4-YES = condition 4-NO (size/cross-module threshold). Q4-NO = condition 4-YES (≤30-line single-file). Condition 3 (complete instruction, no exploration) is implicit: absent exploration language → Q3/Q4 gate applies normally.

Q3 is the **prose-writer filter**. It exists because in the Sep 2026
session 4/4 structured-prose dispatches exited with **0 output** (see
[Evidence table](#evidence-table) row #1). Three code-module dispatches in
the same session succeeded, so the filter is prose-specific. Verify-after
([§ Verification](#verification)) still applies.

## Main-direct — the 5 conditions

Pick main-direct if **any one** of these is true:

1. **Single-file / single-step / deterministic** (file existence check,
   variable lookup, regex match, `ls`, `cat`, `wc`).
2. **User explicitly opts out** ("你自己处理", "skip orchestrator",
   "main 直接做", "no need to delegate").
3. **User gave a complete instruction** with no exploration needed
   (no "investigate X first", no "find the best approach").
4. **Change is ≤30 lines AND single-file AND no new public surface**
   (no new function/class exposed to callers, no new config field).
5. **Task is structured prose** — spec doc, runbook, SKILL.md,
   design.md, README prose section. (See [Evidence](#evidence-table)
   row #1; also Q3 in the decision tree above.)

> ⚠️ Condition 5 is the only one derived from a **systematic**
> failure mode, not a per-task judgement call. The other 4 are
> efficiency heuristics. If you skip condition 5 because "this prose
> task is short", expect ~50% silent 0-output rate per the Sep 2026
> evidence.

## Fan-out — the 3 conditions

Fan-out (≥2 parallel sub-agents) is appropriate **only when all three**
hold:

1. **Slices are independent** — each sub-agent owns a disjoint file
   set; no shared mutable artifact between them. Cross-file edits to
   the same file do **not** count as independent (see [Evidence](#evidence-table)
   row #4).
2. **Each slice has an explicit exit criterion** — a mutation test, a
   subprocess assertion, a line-count target, or a file-existence
   check. "Looks right" is not an exit criterion.
3. **Each slice has a self-verifiable handoff** — the sub-agent
   produces an artifact (file path, commit hash, JSON output) that the
   main agent can re-read from disk to confirm completion.

Why all three? Because the Sep 2026 evidence shows fan-out works when
exit criteria are mechanical (`b368bb9` — three detector checks, each
mutation-tested independently) and silently degrades when any one is
missing (see row #4).

## Subagent type selection

| Type | Trigger | Self-verifiable exit? | Typical dispatch |
|------|---------|----------------------|------------------|
| **fan-out** | Q5=YES above | Required (per slice) | `subagent` × N parallel |
| **single** | Q4=YES, Q3=NO, Q5=NO | Strongly preferred | `subagent` × 1 |
| **chain** | Output of subagent A feeds B's input | Required (handoff schema) | `subagent A` → parse output → `subagent B` |
| **reviewer** | Code/spec is on disk and reviewable | Output is the review text itself | `subagent` with `scope=review` |

**Reviewer-dispatch note:** Reviewers are a separate category because
they are read-only and never write code. They have been observed to
succeed where writer-subagents fail (e.g. `5d2a775` — reviewer caught
a CRITICAL L-number collision that the Generator missed). See
[Evidence row #5](#evidence-table).

## Chain constraints

A chain is "subagent A produces X, subagent B consumes X". Chains are
**fragile** because B's output depends on A's shape. Constraints:

- **Handoff schema is single-source** — define the shape in one
  file (e.g. `assets/<name>.schema.json`); both A and B reference it.
  Inline duplicates drift.
- **A's exit criterion is "X exists and validates against schema"**,
  not "looks complete". `jsonschema` or `pydantic` validation is the
  cheapest gate.
- **No silent mid-chain fallbacks** — if B cannot parse X, fail loud,
  do not retry with defaults.

In Sep 2026 no chain dispatches were attempted in this repo. This
section is therefore **theoretical**, pending evidence.

## Evidence table

All rows are from the `qcloud-skills` session of 2026-09-12. SHA
prefixes are short (7 chars) for readability; full SHAs are in `git
log`.

| # | Mode attempted | Outcome | Evidence | Lesson |
|---|---------------|---------|----------|--------|
| 1 | Subagent writing structured markdown (4 prose dispatches) | 0/4 produced output. All exited silently. (Separate 3 code dispatches in same session succeeded.) | `a9064f6` commit message; session log | **Default rule: main-direct for prose.** Total 7 dispatches in session: 4 prose (all 0-output) + 3 code (all succeeded). AGENTS.md "7" counts both; this table counts prose only. |
| 2 | Single subagent extending detector (3 dispatches) | 3/3 produced real code. 1 hallucinated commit SHA; 1 reported "no work" but disk had code. | `a9064f6`; `b368bb9` | **Bidirectional failure mode.** Reports cannot be trusted; verify disk state. |
| 3 | Fan-out: 3 detector check extensions in parallel | 3/3 succeeded; each verified by independent mutation test. | `b368bb9` | Fan-out works **iff** slices are independent and self-verifiable. |
| 4 | Blueprint self-review (main branch) | Generator's `main()` output table was silently dropped by one subagent dispatch; main agent recovered by reading from disk and re-running mutation tests. | session log (2026-09-12) | **Bidirectional failure confirmed.** main-direct was faster than subagent dispatch for the trivial fix, and disk-state verification recovered the dropped output. |
| 5 | Reviewer subagent on a 3-check detector PR | Found: 1 CRITICAL (L21→L23 in AGENTS.md line 163) + 1 MAJOR (uncited evidence) + 2 MINOR (scope inconsistency, brittle else-branch) + 1 warning (ruff C401). All accepted by Generator. | `5d2a775` review report | **Reviewers are read-only → 0-output failure mode does not apply.** Use subagents for review. |
| 6 | Detector round-1 fix (7 drift items) | All 7 fixed: 2 dead SKILL.md refs + 1 dead gcl_runner.py:321 ref + 4 distribution_drift.py line-number corrections. | `944a969`; `5d2a775` | Drift fix passes CI but reviewers still find rot — always review post-merge. |

## Known pitfalls

### Pitfall 1 — Subagent reports disagree with disk (bidirectional)

The Sep 2026 session recorded both directions:

- **Fake "done"**: subagent claims work is complete, cites a commit
  hash, but `git log` does not contain that hash. Or: claims a
  mutation test "HIT" with fabricated percentages.
- **Fake "not done"**: subagent reports 0 changes, but
  `git status --short` shows modified files, or `git diff HEAD` shows
  the expected diff.

**Mitigation:** Treat the report as a *hint*, never as ground truth.
Always run:

```bash
git log --oneline -5
git status --short
# If a specific artifact was promised:
git diff HEAD -- <expected-path>
# If a commit hash was cited:
git show --stat <short-SHA> | head -5
# If the artifact is a structured prose file (per Q3):
wc -l <file> && head -5 <file>   # empty / single-line = 0-output failure
```

This is codified as `AGENTS.md §L23 · subagent report 双向验证`.

### Pitfall 2 — Pre-existing drift is not a subagent bug

When a detector or linter (run by either main or subagent) reports
pre-existing drift that the subagent did not introduce, do not
discredit the subagent. The drift is the detector working. Accept,
record, and either fix-in-this-PR or open a follow-up. Confusing
"drift exists" with "subagent broke things" leads to false rejection
of correct work. See `944a969` (round-1 detector reported 5 drift
items, all real).

### Pitfall 3 — Reviewer subagent and writer subagent have different failure modes

- **Writer subagent**: failure mode is 0-output or fabricated completion
  (row #2). Verify-after is mandatory.
- **Reviewer subagent**: failure mode is missed findings or false
  positives. Output is structurally a list of `{severity, location,
  suggestion}` items — verify by sampling ≥1 item against disk.

Do not collapse both into one "verify the report" rule; they fail
differently.

## Verification

After every subagent dispatch, regardless of mode:

```bash
# 1. File artifacts (writer)
ls <expected-path> && git diff --stat <expected-path>

# 2. Commit artifacts (writer or chain)
git log --oneline -3

# 3. Review artifacts (reviewer)
#    Sample one MAJOR/MINOR finding and verify the file:line exists:
sed -n '<line>p' <file> | grep <expected-content>
```

If verification fails: do not retry the subagent blindly. Read the
artifact, identify the gap, then either (a) re-dispatch with a
narrower scope, or (b) main-direct the remaining work.

## Open questions

1. **Chain dispatches** — no empirical evidence yet. The constraints
   in [§ Chain constraints](#chain-constraints) are theory, awaiting
   data.
2. **Hybrid mode** — main-direct + single subagent in the same task.
   Has been done informally but not formally studied.
3. **Cross-project validation** — README requires ≥2 projects; this
   blueprint has been written from one. Reproducing the decision tree
   on a different repo is the gate to marking it Ready.

## Cross-references

- [kpi-pattern.md](./kpi-pattern.md) — what "observable + thresholded"
  means for a routing KPI (none yet; see Open questions)
- [spec-drift-gate.md](./spec-drift-gate.md) — drift classes that
  routing decisions can introduce
- [preflight-checklist.md §3](./preflight-checklist.md#3-subagent-task-profile-root-cause-silent-0-output-exits)
  — subagent task profile check (this blueprint's sibling)
- `AGENTS.md §L23 · subagent report 双向验证` — the AGENTS-level rule
  this blueprint expands into a decision procedure

---

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
