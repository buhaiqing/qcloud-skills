# Failure Patterns — Reflexion Memory

> **Purpose**: Structured failure memory extracted from GCL traces and Self-Review records.
> Agents can optionally load this file during Pre-flight to 预防 (prevent) known errors.
> **Updated**: 2026-09-19 (7 total hits across all patterns).
> **Token budget**: ≤ 200 lines, enforced — when exceeded, the least-recurring rows are dropped.
> **Count**: distinct GCL runs (traces) that reported the pattern; re-scans do not inflate it.

## 4. Runtime Execution Patterns

| Skill | Operation | Error Pattern | Root Cause | Count | LastSeen | Severity | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qcloud-test-ops` | `tccli cvm DescribeInstances` | idempotency=0.00<0.5 | set ClientToken | 6 | 2026-09 | major | gcl-trace-20260919-155113.json gcl-trace-20260919-155125.json gcl-trace-20260919-155205.json gcl-trace-20260919-155220.json gcl-trace-20260919-155308.json gcl-trace-20260919-155317.json |
| `qcloud-cvm-ops` | `echo mock-cvm-output` | correctness=0.00<0.5 | Generator exit_code=-2; fix command or credentials | 1 | 2026-09 | major | gcl-trace-20260831-165139.json |


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
