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
| `sources` | string[] | ❌ | Those runs by name, as a JSON array in one table cell. Empty for the two sinks with no trace to attribute (the `qcloud-copilot` sink, §10 writer 4, and the self-heal PR workflow, writer 5), which emit `—` |
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

**Five** paths write `docs/failure-patterns.md`. The set below is machine-checked
against the code: `reflexion_store_test.TestTheWriterListIsComplete` derives it
from `scripts/*.py` and fails if the two drift, so a new writer cannot be added
without being named here. (This count was wrong three rounds running while
nothing checked it.)

<!-- store-writers: parsed by reflexion_store_test.TestTheWriterListIsComplete -->
```
failure_pattern_extract.main
reflexion_auto_writer._bulk_update
reflexion_auto_writer.write_trace
reflexion_store.store_failure_pattern
self_heal_pr_workflow._deduplicate_pattern
```

| # | Writer | Granularity | Records `sources`? |
|---|--------|-------------|--------------------|
| 1 | `reflexion_auto_writer.write_trace()` (called by `gcl_runner.py`, one GCL run) | per trace | yes |
| 2 | `reflexion_auto_writer._bulk_update()` (the CLI with no `--input` — `make reflexion-update`, part of `make all`) | per corpus | yes |
| 3 | `failure_pattern_extract.main()` (this module's CLI — both the default path and `--layered`, which reaches the same file through `HOT_PATH`) | per corpus | yes |
| 4 | `reflexion_store.store_failure_pattern()` (the `qcloud-copilot` sink) | per call | **no** |
| 5 | `self_heal_pr_workflow.SelfHealPRWorkflow._deduplicate_pattern()` (called from `self_evolution_loop.py` after a self-heal PR merges; removes the row or decrements its `count`) | per merged fix | **no** |

Writers 1–3 funnel through `failure_pattern_extract.merge()`; writers 4 and 5 do
not, and have no trace to attribute a hit to. That is the whole reason `count`
and `sources` are two figures rather than one — see Invariant 2.

> **Open defect in writer 5 (out of CR-3's scope, reported to the audit
> register).** `_deduplicate_pattern` reads the count as `cells[-2]`, which has
> been the `Severity` column since the Severity column was added — so
> `int("major")` raises, the fallback `count = 1` applies, and the row is
> **deleted** rather than decremented. Verified: a `count=6` row disappears on
> one call. It also means writer 5 ignores the `Sources` column entirely.

**Invariant 1 — `--min-count` retires stored patterns absent from this run's
corpus whose count is below the threshold.** It is an aging policy: a pattern the
run just read has demonstrably *not* stopped recurring, so retiring it — before
or after the merge — would delete it in the very transaction that records it and
`count` could never reach `--min-count`. `_bulk_update()` implements this as
`prune_low_frequency(existing, min_count, exclude=observed)`, where `observed`
is the set of dedup keys this run found in the traces. All three descriptions
(the two `--help` texts and this paragraph) say the same sentence.

This is a statement about the **prune**, not about the file. The line cap (Invariant 3) is a
second, independent loss path that *can* drop an observed pattern, and Invariant 4 is what
makes that loss loud rather than silent.

**Invariant 2 — `count = len(sources) + unattributed`, and re-scanning the same corpus on
the same day changes nothing.** `merge()` keeps the set of trace names (`_source`) seen per
key, so a new GCL run reporting the same failure adds exactly 1 and a re-scan adds 0. `count`
is *not* "how often the extractor ran", so it must never be produced by incrementing a stored
value per occurrence.

Two qualifiers the invariant needs to actually hold:

- **`count` may exceed `len(sources)`.** Writers 4 and 5 record no sources, so their hits live
  in the remainder (`count - len(sources)`), which `merge()` carries across writes. A
  source-less row whose table declares a `Sources` column is evidence, not corruption. A row
  from a table that has *no* `Sources` column predates that column and its count was
  run-multiplicity fiction, so the first run over a real corpus replaces it with the observed
  count. There is no live producer of such a table any more: every emitter (`_emit_store` and
  the `--layered` `emit_layer`) renders the same 8 columns from `_SECTION_HEADERS`.
- **"Byte-for-byte no-op" holds within one day, not across a date boundary.** The rendered
  header embeds today's date (both emitters), so an unchanged corpus still rewrites the file
  when the date rolls over. Compare the tables, not the file bytes.
- **The dedup key is whitespace-normalised.** Leading/trailing whitespace and tabs are stripped
  from every cell on read, and `pattern_key()`/`merge()` strip the same way, so `' lead '` and
  `'lead'` are one pattern rather than two. An interior newline or CR is *escaped* rather than
  stripped — `parse_existing` is line-oriented, so a raw one used to split the row and the
  pattern vanished while the writer still returned success.

`Sources` is a JSON array in one cell, and **every** cell is escaped, `last_seen` and
`severity` included: a `|`, an unpaired backtick, a newline, or a space in a trace-supplied
`command`/`error` used to shift, split or delete the row, which made `Count` read from the
wrong column and inflated `count` on every re-scan. An odd backtick in `severity` was the
sharpest of these — it flipped the parser's backtick state for the rest of the row and
swallowed the `Sources` cell, destroying provenance while leaving `count` untouched. Writers
4 and 5 write no sources, and their rows show `—`.

**Invariant 3 — a layer's line budget is enforced, not warned about.** `enforce_line_cap()`
drops the least valuable rows (lowest `count`, then oldest `last_seen`) until the rendered
file fits, so the cap cannot be exceeded and the caller's `Total patterns` / `Total hits`
describe what was written. Callers writing a warmer layer must pass that layer's own limit
(`enforce_line_cap(patterns, max_lines=WARM_LIMIT)`); the default is the 200-line **hot** cap,
so omitting it silently re-caps warm/cold and demotion destroys memory instead of preserving
it.

`HOT_LIMIT` / `WARM_LIMIT` / `COLD_LIMIT` are **row** counts, not line counts, and they bound
the *layered* store, which does not call `enforce_line_cap` at all. The two budgets are
independent on purpose: a line-capped writer holds ~130 rows, so a row count compared against
`HOT_LIMIT` would never fire there. `merge_failure_batch()` accumulates to the row cap and
demotes; that is the path `--layered` uses.

**Invariant 4 — the R3 gate report runs after the cap, and only an unexplained loss is
fatal.** A run that found a pattern in the traces but does not hold its key afterwards prints
every missing key to stderr. The check must come *after* `enforce_line_cap()`, because the cap
is the only path that drops an observed key — evaluated before it, the comparison is against
the same `new_patterns` list that defines `observed`, so it is structurally empty and a
truncated corpus reports nothing. The exit code is then split by cause:

- **cap-evicted → exit 0**, reported as `REFLEXION GATE (non-fatal)`. `merge()` accepts every
  key `observed` holds, so a cap-evicted key is a designed truncation. It is still loud, still
  after the cap, and still names every key — but failing `make all` for it made the target
  permanently red on a large corpus with no operator remedy, because `--min-count` cannot
  recover a cap-evicted key and `MAX_LINES` is a P0 constraint rather than a knob.
- **anything the cap cannot explain → exit 3.** Reachable: `merge()` losing an observed key is
  a writer defect, and it is the case this gate exists to catch
  (`test_gate_names_an_observed_pattern_merge_dropped` simulates it). Also exits 3 when the
  store ends up empty despite patterns being found (an all-empty-`skill` corpus).

A `--dry-run` never returns 3: it changes nothing, so it only warns in the future tense about
what the next real run would do.

**The writers do NOT share all of this.** `write_trace()` never prunes — one trace cannot tell
whether a stored pattern stopped recurring — and has no empty-store gate; it is allowed to be
a no-op. It does report what the cap evicted, to stderr, and it names the pattern it was called
for when the cap drops *that* one too: `True` means the write happened, not that this pattern
is in the store.

**The store is a committed artefact, not a test workspace.** `write_trace()` has no
destination default — `patterns_path` is required and keyword-only, so the shipped
`docs/failure-patterns.md` cannot be reached by a caller that did not name it, and
`gcl_runner.py` passes `root/docs/failure-patterns.md` (evidence goes to `root/audit-results/`).
A run against a temporary root — every unit test — therefore cannot mutate the shipped file.
That is a property of the signature, not of the callers: the default used to be the module's
`PATTERNS_FILE`, and one call without it rewrote the committed store. The test suite is not a
producer of anything it is then graded on (`TestShippedArtefactsAreNotATestWorkspace`).

**History.** `4e8e77b` fixed prune-before-first-write in `write_trace()` only; `9bca8fc`
moved the same call in `_bulk_update()` before the merge but still pruned keys the run had
just observed, which reset `count` to 1 on every run; and counts accumulated per occurrence,
so they grew with the number of runs. Regression tests: `reflexion_store_test`
(`TestBulkUpdateFirstSeenSurvival`, `TestLineCapEnforcement`,
`TestShippedArtefactsAreNotATestWorkspace`, `TestTheWriterListIsComplete`), `gcl_runner_test`
(`CmdRunEndToEndTests`).
