# CADL — Compound-Asset Distillation Loop (long-form spec)

> **Contract authority** lives in root [`AGENTS.md`](../AGENTS.md) §"复利资产沉淀机制
> (CADL)" (≤30 lines, rules only). This file is the **narrative companion** — read when
> you need background, examples, schema, or anti-patterns. Do not duplicate rules here.

---

## 1. Why a mechanism, not a rule

A rule like "remember to write AGENTS.md" is forgettable. CADL turns accumulation into a
**mandatory exit** — a task that does not close the loop is, by definition, not done.
That is the same logic GCL uses for Generators (`Safety = 0` → abort), and the same
logic Self-Review uses for R1+R2. CADL is the post-task equivalent.

Before CADL: lessons evaporate after the session. After CADL: every踩坑 becomes a
cross-task asset.

---

## 2. Trigger conditions (any ONE → must run CADL)

| # | Trigger | Example |
|---|---|---|
| 1 | Multi-step / cross-file task completed | "Refactor `scripts/validate_*.py`" |
| 2 | Cross-skill delegation (delegation matrix used) | `qcloud-cvm-ops` → `qcloud-cdb-ops` |
| 3 | Review or fix loop (GCL, 2-round self-review, adversarial review) | Any GCL PASS path |
| 4 | Found a repo defect (even outside scope) | "Pre-existing FAIL in `tccli cvm` arg parsing" |
| 5 | Pre-existing FAIL observed and assigned root cause | "E741 ambiguous `l` in `scripts/<name>.py`" |
| 6 | User supplied a reusable workflow preference | "Use the dual-write subcommand to bypass tccli bug" |

If unsure → run it. False positives are cheap (~30 seconds of file write).

---

## 3. Closed loop (5 steps, all required)

```
1. EXTRACT   → abstract reusable pattern from finished task
                format: "Problem → Anti-pattern → Correct approach (with code)"
2. LANDING   → Decide destination:
                * cross-repo reusable?     → user-level guidance file (path varies
                                             by coding agent — never hardcode)
                * repo-specific?           → root AGENTS.md (this repo)
                * single-skill callable?   → independent Skill file (via
                                             qcloud-skill-generator)
3. WRITE     → executable, with example, with boundaries
                MUST grep existing AGENTS.md to avoid duplication
4. GATE      → before write: wc -l AGENTS.md (≥500 → consolidate first)
                before write to docs/failure-patterns.md: ≤200 line cap + dedup by
                skill+command+error (see Reflexion hard constraints in AGENTS.md)
5. REUSE     → next session reads AGENTS.md → asset in scope → 复利生效
```

Skipping any step breaks the loop. Skipping just step 4 (line cap) is the most common
real-world failure mode — fix it by moving the example into a linked doc, not by
overriding the cap.

---

## 4. Asset types (the `WRITE` step options)

| Type | Typical landing point | Example |
|---|---|---|
| `failure_patterns.md` entry | `docs/failure-patterns.md` (≤200 lines) | E741 ambiguous `l` in `validate_local.py` (count+=1) |
| Checklist / rule | root `AGENTS.md` (with grep-dupe check) | "Always pre-flight branch before GCL worktree" |
| Script / helper | `scripts/` (shared executables) | `scripts/cadl_lint.py` for hook enforcement |
| Template | `qcloud-skill-generator/references/` | `qcloud-skill-generator/references/qcloud-skill-template.md` |
| Decision record | repo root or docs/ | "WHY we excluded SDT-7 destructive ops from auto" |
| Troubleshooting flow | skill-level `references/` or docs/ | "tccli cvm 401 → re-check `TENCENTCLOUD_SECRET_ID`" |

Drift heuristic: if the asset is shorter than the explanation it replaces, it wins.
The point is reuse-time cost, not authorship-time beauty.

---

## 5. Skill-side hook (so every skill self-reminds)

The canonical hook line MUST be the trailing non-blank line of every
`qcloud-*-ops/SKILL.md`:

```
> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
```

- `qcloud-skill-generator/references/qcloud-skill-template.md` already ends with this
  line. New skills inherit it.
- `qcloud-skill-generator/SKILL.md` Standard 6 enforces the rule at generate time.
- `scripts/cadl_lint.py` enforces the rule at validate time (any existing skill that
  lacks the hook → linter exits 1; `--fix` injects it idempotently).
- Old skills (`qcloud-*-ops/SKILL.md` predating this spec) MUST have the hook added.
  See `scripts/cadl_lint.py --fix` for the safe bulk path.

---

## 6. Reflexion ↔ CADL relationship

Reflexion memory (`docs/reflexion-memory.md` + `docs/failure-patterns.md` +
`docs/success-patterns.md`) is one of the **WRITE destinations** in step 3 of CADL.
The Reflexion hard constraints (in AGENTS.md) — 200-line cap, dedup by
`skill+command+error`, source from GCL/Self-Review only — are enforced during
the WRITE step.

Schema for `failure_patterns.md` rows and the EVO-1 auto-consumption pipeline live in
`docs/reflexion-memory.md`. CADL does NOT define schema; it directs traffic there.

---

## 7. Anti-patterns

| Anti-pattern | Correct practice |
|---|---|
| Task done, no accumulation | Walk the full loop before delivery |
| One-shot context dumped into AGENTS.md | Only cross-task patterns belong in AGENTS.md |
| Duplicate an existing entry | `grep` AGENTS.md / failure-patterns.md before write |
| Only on GCL / CodeGraph-aware tasks | Any review, fix, collaboration, or verification triggers CADL |
| Bypass 500-line cap by deleting the rule | Move examples/checklists to linked docs, keep the rule |
| Skip the line-cap → 600-line AGENTS.md | Rule 4 is the gate; trim first, write second |

---

## 8. Maintenance

When CADL itself evolves (e.g., a new asset type, a new trigger condition):

1. Update the **contract** in AGENTS.md first (≤30 lines).
2. Update this file (long-form) second with rationale.
3. Bump `docs/cadl-spec.md` footer version: `vN.NN`.

Do not allow drift between AGENTS.md and this file. The hook line, in particular,
is a single byte-for-byte constant across every skill — if any skill drifts, the
linter will catch it; if AGENTS.md drifts, the source of truth is gone.

---

v1.0
