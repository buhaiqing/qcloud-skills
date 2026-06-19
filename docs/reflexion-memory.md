# Reflexion Integration (Lightweight Reflexion)

> **Purpose**: Enable cross-session learning from failure patterns, complementing the within-session
> GCL loop with persistent failure memory. This is a lightweight adaptation of the Reflexion pattern
> (Shinn et al. 2023) — using structured text files instead of vector memory.

## 1. Motivation

| Gap | Current State | Reflexion Solution |
|-----|---------------|-------------------|
| tccli parameter errors repeat across sessions | GCL catches them per-execution, but doesn't remember | Extract from GCL traces → persist in `docs/failure-patterns.md` |
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
│   docs/failure-patterns.md (structured text, ≤200 lines)        │
│   §1 CLI Parameter Errors | §2 Skill Generation | §3 Cross-Skill│
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    Pre-flight retrieval (optional)
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

## 5. Pre-flight Retrieval (Optional)

During GCL Pre-flight (see `docs/gcl-spec.md` §4 step [0]), the Orchestrator MAY load `docs/failure-patterns.md` (lazy-load, ~130 lines), filter by current skill name, and inject top-3 relevant patterns into Generator context as prevention hints:

```text
Known failure patterns for this skill:
- InvalidParameter: Use --InstanceIds "[\"ins-xxx\"]" (JSON array, not comma-separated)
- AuthFailure: Check TENCENTCLOUD_SECRET_ID/KEY env vars
- redis-cli not found: Add idempotent install probe before execution
```

**This is a HINT, not a CONSTRAINT** — the Generator should use these patterns to avoid known mistakes, but is not required to follow them if the context differs.

## 6. Relationship with Other GCL Layers

| Layer | Timing | Learning Scope | Reflexion Complement |
|-------|--------|----------------|---------------------|
| **GCL (Generator-Critic)** | Per-execution | Within-session | — |
| **Self-Review** (see `AGENTS.md` “Mandatory rule: 2-round self-review”) | Per-update | Skill authoring | Reflexion captures patterns from Self-Review discoveries |
| **Reflexion Memory** | Cross-session | Persistent failure patterns | Aggregates from all sources above |

## 7. Anti-Patterns

- ❌ **Reflexion as mandatory gate** — Pattern retrieval is optional, not a blocking gate
- ❌ **Unbounded memory** — Hard cap at 200 lines; prune low-frequency patterns
- ❌ **Subjective pattern extraction** — Patterns must come from structured GCL traces or Self-Review records, not ad-hoc observations
- ❌ **Pattern hoarding** — If a pattern is promoted to Anti-Patterns sections, remove from `docs/failure-patterns.md` to avoid duplication

## 8. Changelog

Reflexion changes are tracked in the unified runtime-quality changelog in `docs/gcl-spec.md` §12.
