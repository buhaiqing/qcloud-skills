# Reflexion Integration (Lightweight Reflexion)

> **Purpose**: Enable cross-session learning from failure patterns, complementing the within-session
> GCL loop with persistent failure memory. This is a lightweight adaptation of the Reflexion pattern
> (Shinn et al. 2023) — using structured text files instead of vector memory.

## 1. Motivation

| Gap | Current State | Reflexion Solution |
|-----|---------------|-------------------|
| tccli parameter errors repeat across sessions | GCL catches them per-execution, but doesn't remember | Extract from GCL traces → persist in `docs/failure-patterns.md` |
| Successful op patterns repeat | Agents re-solve known problems | Record in `docs/success-patterns.md` §1 → inject in Pre-flight for faster convergence |
| Skill generation repeats structural issues | Self-Review catches them per-session, but doesn't remember | Record in `failure-patterns.md` §2 → 预防 next generation |
| Cross-skill composition failures | Documented in SKILL.md, but not centralized | Centralize in `failure-patterns.md` §3 |

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GCL Execution (per-session)                   │
│   [0] Pre-flight → [1] Generate → [2] C → [3] Decide           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    failure_pattern (in trace)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Reflexion Memory (cross-session)                    │
│   docs/failure-patterns.md (≤200 lines) + docs/success-patterns.md │
│   failure_patterns: §1 CLI Errors | §2 Skill Gen | §3 Cross-Skill│
│   success_patterns:   §1 Winning Ops  | §2 Convergence Patterns  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              Pre-flight retrieval: failure_patterns (optional)
              Pre-flight injection:  success_patterns (optional)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Prevention (next session)                           │
│   Inject known patterns into Generator context                  │
│   Agent avoids repeating known mistakes                          │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Failure Pattern Schema

Each pattern in `docs/failure-patterns.md` follows this structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `category` | enum | ✅ | `cli_parameter` \| `skill_generation` \| `cross_skill` \| `runtime` \| `token_efficiency` |
| `skill` | string | ✅ | Skill name (e.g. `qcloud-cvm-ops`) |
| `command` | string | ❌ | The command that failed (for CLI errors) |
| `error` | string | ✅ | Error message or pattern description |
| `fix` | string | ✅ | How to fix or prevent this error |
| `count` | int | ✅ | Frequency count (pruned when < 3) |
| `reusable` | bool | ✅ | Whether this pattern is generalizable |

## 4. Maintenance Rules

| Rule | Description |
|------|-------------|
| **Token budget** | `docs/failure-patterns.md` ≤ 200 lines. When exceeded, prune patterns with `count < 3` |
| **Dedup** | Before adding, check if pattern exists (match by `skill` + `command` + `error`). If exists, increment `count` |
| **Source** | Patterns come from: (1) GCL trace `failure_pattern` field, (2) lessons learned captured after Self-Review Round 1/2 findings |
| **Review** | Patterns are reviewed monthly. Patterns with `count ≥ 10` are candidates for promotion to Anti-Patterns sections |

## 5. Success Pattern Pre-flight Retrieval (Optional)

During GCL Pre-flight, the Orchestrator MAY load `docs/success-patterns.md` (lazy-load, ~100 lines), filter by current skill + operation type, and inject winning patterns into Generator context as convergence hints:

```text
Known success patterns for this skill + operation:
tccli cvm DescribeInstances --Region {{user.region}}  # WORKS — standard pagination pattern
```

**Source:** `scripts/success_pattern_mine.py` writes pending entries; `scripts/success_pattern_retrieve.py` reads and filters. The combined `REFLEXION_PATTERNS` env var is built in `gcl_runner.py` pre-flight: `success_block` first, then `fail_block` via `success_pattern_retrieve` and `reflexion_retrieve` respectively.

**Schema:** Each entry in `success-patterns.md`:

| Field | Type | Required | Description |
|-------|------|----------|---------------|
| `skill` | string | ✅ | Skill name (e.g. `qcloud-cvm-ops`) |
| `operation` | string | ✅ | Operation type (e.g. `DescribeInstances`) |
| `pattern` | string | ✅ | The specific tccli invocation pattern that works |
| `success_rate` | float | ✅ | Historical success rate (0.0–1.0) |
| `last_verified` | string | ✅ | ISO8601 timestamp of last successful execution |

**Anti-Patterns:**
- ❌ **Success patterns as mandatory gate** — retrieval is optional hint, not constraint
- ❌ **Stale patterns** — prune entries with `success_rate < 0.7` or `last_verified > 90 days`

## 6. Failure Pattern Pre-flight Retrieval (Optional)

During GCL Pre-flight (see `docs/gcl-spec.md` §4 step [0]), the Orchestrator MAY load `docs/failure-patterns.md` (lazy-load, ~130 lines), filter by current skill name, and inject top-3 relevant patterns into Generator context as prevention hints:

```text
Known failure patterns for this skill:
- InvalidParameter: Use --InstanceIds "[\"ins-xxx\"]" (JSON array, not comma-separated)
- AuthFailure: Check TENCENTCLOUD_SECRET_ID/KEY env vars
- redis-cli not found: Add idempotent install probe before execution
```

**This is a HINT, not a CONSTRAINT** — the Generator should use these patterns to avoid known mistakes, but is not required to follow them if the context differs.

## 7. Relationship with Other GCL Layers

| Layer | Timing | Learning Scope | Reflexion Complement |
|-------|--------|----------------|---------------------|
| **GCL (Generator-Critic)** | Per-execution | Within-session | — |
| **Self-Review** (see `AGENTS.md` “Mandatory rule: 2-round self-review”) | Per-update | Skill authoring | Reflexion captures patterns from Self-Review discoveries |
| **Reflexion Memory** | Cross-session | Persistent failure patterns | Aggregates from all sources above |

## 8. Anti-Patterns

- ❌ **Reflexion as mandatory gate** — Pattern retrieval is optional, not a blocking gate
- ❌ **Unbounded memory** — Hard cap at 200 lines; prune low-frequency patterns
- ❌ **Subjective pattern extraction** — Patterns must come from structured GCL traces or Self-Review records, not ad-hoc observations
- ❌ **Pattern hoarding** — If a pattern is promoted to Anti-Patterns sections, remove from `docs/failure-patterns.md` to avoid duplication

## 9. Changelog

Reflexion changes are tracked in the unified runtime-quality changelog in `docs/gcl-spec.md` §12.
