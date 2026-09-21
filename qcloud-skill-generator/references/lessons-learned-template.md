# Per-Skill Lessons-Learned Template (CADL Landing Point)

> **Purpose**: When a lesson only applies to ONE skill (single-product CLI error, API quirk, validator edge case), it does NOT belong in root `AGENTS.md` or `docs/execution-lessons.md`. Land it here instead.
>
> **Decision context**: See root [`AGENTS.md` §CADL Landing Point Routing Table](../../AGENTS.md#c--------p0) for the 6-row routing table and 5-question decision tree.

## When to use this file

Use this template when ALL of the following are true:
- The lesson only triggers when running this ONE `qcloud-{product}-ops` skill
- The lesson involves a specific CLI flag, API field, or error code (not a generic pattern)
- Future runs of this skill would benefit from the note being there

Use one of the other landing points when:
- The lesson applies across multiple skills → root `AGENTS.md` or `docs/execution-lessons.md`
- The lesson is a `skill + command + error` triple for the Reflexion store → `docs/failure-patterns.md`
- The lesson is an architectural decision → `docs/architecture/ADR-NNNN-*.md`

## File location

Per skill: `qcloud-{product}-ops/references/lessons-learned.md`

Example: `qcloud-cvm-ops/references/lessons-learned.md`

This file is **not** required for every skill — only skills that have accumulated single-skill lessons should create it.

## Template

```markdown
# {Product} Lessons Learned (Single-Skill Only)

> Lessons that ONLY apply to `qcloud-{product}-ops`. Cross-skill patterns
> belong in `docs/execution-lessons.md`; CLI/API error triples for the
> Reflexion store belong in `docs/failure-patterns.md`. See root AGENTS.md
> "CADL Landing Point Routing Table" for decision logic.

| ID | Lesson | Key Fix |
|----|--------|---------|
| {SL1} | {one-line lesson statement} | {concrete fix: code snippet, CLI flag, API field} |
| {SL2} | ... | ... |
```

**ID prefix convention**: `{SL}` = "single-skill" (e.g., `CVM-SL1`, `CDB-SL1`).
Avoid using the global `L{N}` prefix reserved for `docs/execution-lessons.md`.

## Linter integration (optional)

`scripts/cadl_lint.py` is the existing linter for the canonical CADL hook on SKILL.md. The per-skill lessons-learned.md is **not** lint-gated by default — skills may create/skip it as needed. If a skill accumulates >20 single-skill lessons, consider promoting the high-frequency ones to `docs/execution-lessons.md` (cross-skill value) or `docs/failure-patterns.md` (if it's a CLI error triple).