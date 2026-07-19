# Success Patterns — Reflexion Memory (Success Branch)

> **Purpose**: Structured success memory extracted from GCL traces and Self-Review records.
> Agents can optionally load this file during Pre-flight to achieve faster convergence
> by reusing known-working operation patterns.
>
> **Maintenance**: Updated automatically via `scripts/success_pattern_mine.py --batch` (cron daily 02:00).
> **Token budget**: ≤ 100 lines. When exceeded, prune low-frequency patterns (count < 3).
> **Schema source**: `docs/reflexion-memory.md` §5.

---

## 1. Winning CLI Operation Patterns

> Extracted from GCL traces where final.status=PASS.

| Skill | Operation | Pattern | success_rate | last_verified |
|-------|-----------|---------|-------------|---------------|
| — | — | — | — | — |

**注**: 本表初始为空，首次成功执行后由 `success_pattern_mine.py` 自动填充。

---

## Usage Guidelines

### For Agents (Pre-flight)

```
# Optional: Load success patterns before executing a skill
# 1. Read this file (lazy-load, ~50 lines)
# 2. Filter patterns by current skill name + operation type
# 3. Inject relevant patterns into Generator context as convergence hints
```

### For Mining (success_pattern_mine.py)

```
# After GCL iteration passes with PASS status:
# 1. Extract skill + operation + command from trace
# 2. Append to audit-results/gcl-success-pending.jsonl (non-blocking)
# 3. Daily cron aggregates pending → this file
```
