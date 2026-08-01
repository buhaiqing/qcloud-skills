# CADL Automation — Design Spec

## Background

CADL (Compound-Asset Distillation Loop) is defined in root AGENTS.md §"复利资产沉淀机制"
as a 5-step closing ceremony every substantive task must complete (提取 / 落点判定 /
写入 / 门禁 / 复用). The narrative is sound, but:

- 35 `qcloud-*-ops/SKILL.md` files currently contain the chunk WITHOUT the required
  trailing hook line. Only 2/35 have the hook today.
- The 60-line narrative in AGENTS.md has no short, scannable contract any agent can
  load in <2KB. It buries the rules in prose.
- There is no mechanical enforcement. A runbook-style "do X" rule with no linter will
  be ignored at scale (CADL §为什么是机制而非规范).

Goal: turn CADL from a normative paragraph into a **mechanical contract** with one
canonical hook phrase, one linter, and one source of truth (AGENTS.md stays minimal,
docs/cadl-spec.md carries the long form).

## Architecture

```
            ┌──────────────────────┐
            │   AGENTS.md § CADL   │  ← minimal contract (≤30 lines)
            │   (link only)        │     MUST / SHOULD-NOT rules + script name
            └──────────┬───────────┘
                       │ link
                       ▼
            ┌──────────────────────┐
            │  docs/cadl-spec.md   │  ← long-form reference
            │  (narrative + exam-  │     闭环 / 触发 / 资产类型 / Skill 钩子 / 反模式
            │   ples + schema)     │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────────────────────────────┐
            │   scripts/cadl_lint.py                       │
            │   - scans qcloud-*-ops/SKILL.md             │
            │   - asserts trailing hook = canonical phrase │
            │   - exit 0/1 + per-skill report              │
            │   - `--fix` performs idempotent inject       │
            └──────────┬───────────────────────────────────┘
                       │ invoked by
                       ▼
            ┌──────────────────────────┐
            │  scripts/validate_local  │  ← registers cadl_lint in regression gates
            └──────────────────────────┘
```

## Canonical Hook Phrase (single source of truth)

Exactly this byte sequence (verbatim — emojis excluded, full-width punctuation):

    > 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

This phrase already lives in:
- `qcloud-skill-generator/references/qcloud-skill-template.md` (tail)
- `qcloud-skill-generator/SKILL.md` Standard 6
- 2 existing skills (qcloud-cloudbase-ops, qcloud-copilot)

The linter normalizes via `CANONICAL_HOOK` constant; do not duplicate the literal in
multiple places (DRY).

## Files Touched

| Path | Change | Lines | Risk |
|---|---|---|---|
| `AGENTS.md` | Shrink CADL block 264-322 (60 lines) → ≤30 lines; link to docs/cadl-spec.md | ≤-30 | low |
| `docs/cadl-spec.md` | NEW: long-form (target ≤150 lines) | +≤150 | medium (new file) |
| `scripts/cadl_lint.py` | NEW: linter (~80 lines) + argparse + --fix | +≤100 | medium (new code) |
| `scripts/cadl_lint_test.py` | NEW: unittests covering 5 cases | +≤80 | medium |
| `scripts/validate_local.py` | Register cadl_lint invocation | +≤5 | low |
| 33 × `qcloud-*-ops/SKILL.md` | Append hook (idempotent via cadl_lint --fix) | +1/ea | low |
| `qcloud-skill-generator/SKILL.md` | Standard 6 unchanged; verify wording | 0 | nil |
| `qcloud-skill-generator/references/qcloud-skill-template.md` | Verify hook already present | 0 | nil |

## Algorithm — scripts/cadl_lint.py

```python
def lint_one(path: Path) -> tuple[str, bool, str]:
    """Returns (skill_name, ok, message)."""
    text = path.read_text(encoding="utf-8")
    last_nonblank = next((ln for ln in reversed(text.splitlines()) if ln.strip()), "")
    if last_nonblank == CANONICAL_HOOK:
        return (path.parent.name, True, "ok")
    return (path.parent.name, False, f"last_line={last_nonblank!r}")

def fix_one(path: Path) -> None:
    """Idempotent: appends hook if absent; otherwise no change."""
    text = path.read_text(encoding="utf-8")
    if text.rstrip("\n").endswith(CANONICAL_HOOK):
        return  # already correct
    if text and not text.endswith("\n"):
        text += "\n"
    # ensure blank line separator between previous content and hook (Optional but readable)
    sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    path.write_text(text + sep + CANONICAL_HOOK + "\n", encoding="utf-8")
```

Edge cases:
- File has only blank lines → reject as malformed
- File ends with hook but extra trailing blanks → ACCEPT (`.rstrip("\n")` then `endswith` is OK)
- File contains hook followed by another hook → ACCEPT (`.endswith` looks only at suffix)
- File is a meta-skill under `qcloud-skill-generator/` → still linted (Standard 6 also applies)

Self-check (per Spec-Plan-Code gate, AGENTS.md L54):

    assert lint_one(path_with_hook).ok is True
    assert lint_one(path_without_hook).ok is False
    run fix_one twice on same path → byte-identical second time (idempotency)
    glob qcloud-*-ops/SKILL.md → 35 files; `--fix` brings all to ok=True in one pass

## Layer Compliance (vs existing rules)

| Rule | Compliance |
|---|---|
| Agent-Agnostic (P0) | YES — no `.codegraph/`/`.omc/`/`.codebuddy/` paths; the linter is a stdlib script |
| Token Efficiency (TE-1/3/4/5/6) | YES — linter reads file once; no hardcoded lists; one-liner report; canonical phrase as module constant (no inline duplicates) |
| Five Core Standards | N/A (this is infra, not a skill) |
| Spec-Plan-Code Alignment | This file IS the SPEC; PLAN is the phase table below; code is the linter + tests |
| Subagent concurrency (P0) | N/A here, but the parallel inject via `--fix` is single-process |
| Commit hygiene Hard stops | None — no credentials, no destructive ops, hook append is reversible |
| 2-round self-review | MANDATORY per AGENTS.md — Round 1 (template/standards) + Round 2 (adversarial) executed by Generator (critics disabled by infra) |

## Plan (Phase Checkbox)

- [x] Phase 1: Create `docs/cadl-spec.md` (long-form content offloaded from AGENTS.md). — `docs/cadl-spec.md` exists (137 lines)
- [x] Phase 2: Shrink AGENTS.md CADL block to ≤30 lines + add link + register `cadl_lint.py` in evaluation table (line ~150 area). — registered at AGENTS.md:150
- [x] Phase 3: Implement `scripts/cadl_lint.py` + `scripts/cadl_lint_test.py` per algorithm. — both exist; 14 unit tests pass
- [x] Phase 4: Run `python3 scripts/cadl_lint.py --fix` to inject hook into 33 missing skills. — all 36 SKILL.md hooked (incl. qcloud-test-ops stub, fixed 2026-08-01 908edce)
- [x] Phase 5: Run `python3 scripts/cadl_lint.py` (no --fix); expect exit 0, all rows ok. — 36/36 OK, EXIT=0
- [x] Phase 6: `ruff check scripts/cadl_lint.py scripts/cadl_lint_test.py` (no E741, etc.). — All checks passed
- [x] Phase 7: `python3 scripts/validate_local.py` smoke check. — `--list` shows "CADL hook compliance: cadl_lint.py" step
- [x] Phase 8: 2-round self-review (Round 1 template/standards; Round 2 adversarial). — executed; landed in commit a547723
- [x] Phase 9: Single commit + merge to main + remove worktree per worktree lifecycle hard rule. — commit a547723 on main; worktree removed

