# Manual Anchor — Doc-Drift R5 (2026-09-01)

## Context

G-Anchor-Drift R4 applied auto-fix (G-Extend-Autofix) to 16 HIGH-confidence blocks.
5 blocks remained: auto-fix's 5 inference patterns (comment header / class name / function name / same-name spec / import fallback) found no HIGH-confidence anchor for any of them.

Root causes:
- Pseudocode usage examples (no disk implementation)
- Plan-specified code for files that don't yet exist
- Design-spec algorithm blocks (no import, no class name matching a real file)

## Strategy Applied: A — AUTHORITATIVE Marker

All 5 blocks received `# AUTHORITATIVE:` as the first line of the code block,
permitted by `check_doc_code_drift.py` EXEMPT_PATTERNS.

No changes to the check script's detection logic. No block content modified.

## Per-File Results

| File | Block Line | Lines | Strategy | AUTHORITATIVE Reason |
|------|-----------|-------|----------|----------------------|
| `docs/gcl-enforcement-plan.md` | 74 | 35 | A | usage example, no disk implementation |
| `docs/gcl-multi-subagent-rule.md` | 118 | 45 | A | planned validation script stub, no disk implementation |
| `docs/superpowers/plans/2026-07-28-harness-engineering-optimization-plan.md` | 144 | 65 | A | plan-specified script (`scripts/validate_evidence_schema.py`), file does not yet exist |
| `docs/superpowers/specs/aiops-cruise-enhancement-design.md` | 376 | 49 | A | self-check pseudocode, no disk implementation |
| `docs/superpowers/specs/obs-1-observability-enhancement-design.md` | 62 | 39 | A | design spec for planned `copilot/observ.py`, file does not yet exist |

## Before / After Line Counts

| File | Before | After | Δ |
|------|--------|-------|---|
| `docs/gcl-enforcement-plan.md` | 208 | 209 | +1 |
| `docs/gcl-multi-subagent-rule.md` | 260 | 261 | +1 |
| `docs/superpowers/plans/2026-07-28-harness-engineering-optimization-plan.md` | 729 | 730 | +1 |
| `docs/superpowers/specs/aiops-cruise-enhancement-design.md` | 540 | 541 | +1 |
| `docs/superpowers/specs/obs-1-observability-enhancement-design.md` | 194 | 195 | +1 |
| **Total** | 1931 | 1936 | **+5** |

## Verification

```bash
python3 scripts/check_doc_code_drift.py  # exit 0, SUMMARY: 0 file(s) with drift
ruff check scripts/check_doc_code_drift.py  # exit 0
python3 -m py_compile scripts/check_doc_code_drift.py  # exit 0
```

Result: **5 → 0 drift files**.

## Not Introduced

- No change to check script detection logic
- No new exemption patterns added to `EXEMPT_PATTERNS`
- No block content altered (only 1-line AUTHORITATIVE header prepended)
- No M-state files modified
