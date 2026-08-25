# Failure Patterns — Reflexion Memory

> **Purpose**: Structured failure memory extracted from GCL traces and Self-Review records.
> Agents can optionally load this file during Pre-flight to 预防 (prevent) known errors.
> **Updated**: 2026-08-26 (0 total hits across all patterns).
> **Token budget**: ≤ 200 lines. When exceeded, prune patterns with count < 3.


## Usage Guidelines

### For Agents (Pre-flight)
```
# Optional: Load failure patterns before executing a skill
# 1. Read this file (lazy-load, ~130 lines)
# 2. Filter patterns by current skill name
# 3. Inject relevant patterns into Generator context as prevention hints
```

### For Self-Review (Round 3: Lessons Learned)
```
# After completing R1 + R2:
# 1. Extract new failure patterns from this session
# 2. Check if pattern already exists (dedup by skill + command + error)
# 3. If new: append to appropriate section with count=1
# 4. If existing: increment count
# 5. If total lines > 200: prune patterns with count < 3
```

### For GCL Traces
```json
# When a GCL iteration fails, record the failure pattern:
{
  "failure_pattern": {
    "category": "cli_parameter" | "skill_generation" | "cross_skill" | "runtime" | "token_efficiency",
    "skill": "qcloud-xxx-ops",
    "command": "tccli xxx ...",
    "error": "InvalidParameter: ...",
    "fix": "Use JSON array format for array params",
    "reusable": true
  }
}
```
