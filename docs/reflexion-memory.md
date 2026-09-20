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
| `count` | int | ✅ | Distinct GCL runs (traces) that reported the pattern, plus hits reported by a sink with no trace (`count ≥ len(sources)`, §10). A stored key absent from the current corpus is retired when `count < 3` |
| `sources` | string[] | ❌ | Those runs by name, as a JSON array in one table cell. Empty for the `qcloud-copilot` sink, which emits `—` |
| `reusable` | bool | ✅ | Whether this pattern is generalizable |

## 4. Maintenance Rules

| Rule | Description |
|------|-------------|
| **Token budget** | `docs/failure-patterns.md` ≤ 200 lines, enforced by dropping the least-recurring rows |
| **Dedup** | Before adding, check if pattern exists (match by `skill` + `command` + `error`). If it exists, add this trace to its `sources`; `count` follows the source set (§10) |
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

## 10. Write-Path Invariants (`--min-count` is an aging policy)

**Three** paths write `docs/failure-patterns.md`:

| # | Writer | Granularity | Records `sources`? |
|---|--------|-------------|--------------------|
| 1 | `reflexion_auto_writer.write_trace()` (called by `gcl_runner.py`, one GCL run) | per trace | yes |
| 2 | `reflexion_auto_writer._bulk_update()` (the CLI with no `--input` — `make reflexion-update`, part of `make all`) | per corpus | yes |
| 3 | `reflexion_store.store_failure_pattern()` (the `qcloud-copilot` sink) | per call | **no** |

Writers 1 and 2 both funnel through `failure_pattern_extract.merge()`; writer 3 does not, and
has no trace to attribute a hit to. That is the whole reason `count` and `sources` are two
figures rather than one — see Invariant 2.

**Invariant 1 — `--min-count` only ages out keys absent from the current run's corpus.**
`_bulk_update()` prunes the stored patterns via
`prune_low_frequency(existing, min_count, exclude=observed)`, where `observed` is the set of
dedup keys this run found in the traces. A pattern the run just read has demonstrably *not*
stopped recurring, so retiring it — before or after the merge — would delete it in the very
transaction that records it and `count` could never reach `--min-count`.

This is a statement about the **prune**, not about the file. The line cap (Invariant 3) is a
second, independent loss path that *can* drop an observed pattern, and Invariant 4 is what
makes that loss loud rather than silent.

**Invariant 2 — `count = len(sources) + unattributed`, and re-scanning the same corpus on
the same day changes nothing.** `merge()` keeps the set of trace names (`_source`) seen per
key, so a new GCL run reporting the same failure adds exactly 1 and a re-scan adds 0. `count`
is *not* "how often the extractor ran", so it must never be produced by incrementing a stored
value per occurrence.

Two qualifiers the invariant needs to actually hold:

- **`count` may exceed `len(sources)`.** Writer 3 records no sources, so its hits live in the
  remainder (`count - len(sources)`), which `merge()` carries across writes. A source-less row
  whose table declares a `Sources` column is evidence, not corruption. A row from a table
  that has *no* `Sources` column predates that column and its count was run-multiplicity
  fiction, so the first run over a real corpus replaces it with the observed count.
- **"Byte-for-byte no-op" holds within one day, not across a date boundary.** The rendered
  header embeds today's date, so an unchanged corpus still rewrites the file when the date
  rolls over. Compare the tables, not the file bytes.

`Sources` is a JSON array in one cell, and every cell is escaped: a `|`, an unpaired backtick,
or a space in a trace-supplied `command`/`error` used to shift or split the row, which made
`Count` read from the wrong column and inflated `count` on every re-scan. Writer 3's rows have
no sources at all and show `—`.

**Invariant 3 — a layer's line budget is enforced, not warned about.** `enforce_line_cap()`
drops the least valuable rows (lowest `count`, then oldest `last_seen`) until the rendered
file fits, so the cap cannot be exceeded and the caller's `Total patterns` / `Total hits`
describe what was written. Callers writing a warmer layer must pass that layer's own limit
(`enforce_line_cap(patterns, max_lines=WARM_LIMIT)`); the default is the 200-line **hot** cap,
so omitting it silently re-caps warm/cold and demotion destroys memory instead of preserving
it.

**Invariant 4 — the R3 gate asserts the real loss, and it runs after the cap.** A run that
found a pattern in the traces but does not hold its key afterwards exits 3 and names the
missing keys. The check must come *after* `enforce_line_cap()`, because the cap is the only
path that drops an observed key — evaluated before it, the comparison is against the same
`new_patterns` list that defines `observed`, so it is structurally empty and a truncated
corpus exits 0. The "store is empty" case is reported as a secondary branch (it is what an
all-empty-`skill` corpus produces, since `merge()` drops those). A `--dry-run` never returns
3: it changes nothing, so it only warns in the future tense about what the next real run
would do.

**The writers do NOT share all of this.** `write_trace()` never prunes — one trace cannot tell
whether a stored pattern stopped recurring — and has no empty-store gate; it is allowed to be
a no-op. It does report what the cap evicted, to stderr.

**The store is a committed artefact, not a test workspace.** Its destination derives from the
caller's repo root (`gcl_runner.py` passes `root/docs/failure-patterns.md` and writes evidence
to `root/audit-results/`), so a run against a temporary root — every unit test — cannot mutate
the shipped file. The test suite is not a producer of anything it is then graded on
(`TestShippedArtefactsAreNotATestWorkspace`).

**History.** `4e8e77b` fixed prune-before-first-write in `write_trace()` only; `9bca8fc`
moved the same call in `_bulk_update()` before the merge but still pruned keys the run had
just observed, which reset `count` to 1 on every run; and counts accumulated per occurrence,
so they grew with the number of runs. Regression tests: `reflexion_store_test`
(`TestBulkUpdateFirstSeenSurvival`, `TestLineCapEnforcement`,
`TestShippedArtefactsAreNotATestWorkspace`), `gcl_runner_test` (`CmdRunEndToEndTests`).
