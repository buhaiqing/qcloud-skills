# Harness Engineering Optimization — Design Spec

## Background

`qcloud-skills` is a collection of 34 Tencent Cloud ops skills (see AGENTS.md
"Skills inventory": 29 product-scoped + 4 cross-product + 1 meta) delivered as
AI-agent runbooks, governed by a heavy but sound quality stack: GCL
(Generator-Critic-Loop)
multi-subagent gating, git-worktree isolation, CADL asset distillation, and a Python
validation toolchain (`scripts/validate_local.py`, `cadl_lint.py`,
`gcl_trace_aggregate.py`).

The harness works, but it has four structural gaps that block it from being
*trustworthy, closed-loop, safe, and efficient* at scale:

1. **No evidence-based trust.** GCL scores exist, but there are no per-skill golden
   scenarios, no CLI-response fixtures, no sandbox E2E, and no machine-generated
   capability manifest. Quality is asserted by scores, not demonstrated by reproducible
   evidence. self-test / sandbox / production telemetry is not cleanly separated.
2. **GCL loop is score-only, not action-closed.** Critic produces scores; there is no
   structured feedback → Generator retry path, no process timeout, no schema validation,
   no mandatory trace masking at the kernel level.
3. **Runtime safety is manually gated.** Destructive-operation detection relies on human
   confirmation steps in prose, not on the harness autonomously classifying the action and
   binding a confirmation token to a specific execution plan.
4. **Harness inefficiency.** Every skill's full content is reachable; there is no unified
   Skill Registry + Router, no lazy frontmatter-only loading, no per-run budgets
   (context / tools / wall-clock), no routing confusion matrix, and the dev/CI entry
   points (Makefile, CI, dependency lock) are fragmented.

Design principle (per user): **additive, non-weakening** — every optimization layers on
top of the existing GCL/worktree/CADL stack without removing or weakening any gate.

Success is measured by a fixed KPI set (see §KPI) that the harness itself must emit.

## Architecture (shared kernel)

All four directions converge on one **Evidence Kernel** + one **Skill Registry**. This
is the single source of truth that lets the four Phases share data instead of
diverging into four parallel schemas (which AGENTS.md already warns against).

The Evidence Kernel has **two faces** (timing matters — gates must act before/within
the run, not only after):

- **PreFlight** (before/during run): budget enforcement, destructive-action
  pre-classification, confirmation-token issuance gate, trace-masking guard.
- **PostRecord** (after run): structured-trace persistence, KPI aggregation, manifest
  emission.

```
  run requested
       │
       ▼
  [PreFlight]  budget ok? destructive? → token required?
       │                                            │
       │ (destructive)                              │ (no token yet)
       ▼                                            ▼
  human issues confirmation token ──┐      refuse execution
  (human-in-the-loop)               │
       │                            │
       ▼                            │
  token <-> plan_hash bound? ───────┘── no → refuse
       │ yes
       ▼
  [Execute]  (wall_clock_ms bounded; trace masked live)
       │
       ▼
  [PostRecord]  persist EvidenceRecord; aggregate KPI; emit manifest
```

```
            ┌──────────────────────────────────────────────┐
            │            Skill Registry (machine-built)     │
            │  aggregates frontmatter + routing metadata    │
            │  of all qcloud-*-ops/SKILL.md                 │
            │  = Capability Manifest source                 │
            └───────────────┬──────────────────────────────┘
                            │ Router loads frontmatter only
                            ▼
            ┌──────────────────────────────────────────────┐
            │         Runtime Router (lazy load)             │
            │  candidate select via frontmatter → on hit,    │
            │  progressive-load references; enforces budgets │
            └───────────────┬──────────────────────────────┘
                            │ every run emits
                            ▼
            ┌──────────────────────────────────────────────┐
            │            Evidence Kernel                     │
            │  EvidenceRecord (one schema for all phases)    │
            │  feeds Golden / A-B / Telemetry / TE gates     │
            │  + KPI aggregation + maturity report           │
            └───────────────┬──────────────────────────────┘
                            │ single CI entry
                            ▼
            ┌──────────────────────────────────────────────┐
            │   Required CI gates (Golden, A-B, Telemetry,   │
            │   TE) — additive to existing validate_local    │
            └──────────────────────────────────────────────┘
```

## EvidenceRecord schema (kernel contract)

```json
{
  "skill": "string",
  "run_id": "string",
  "phase": "self-test | sandbox | production",   // telemetry split dimension
  "intent": "string",
  "router_decision": {                            // efficiency + confusion matrix
    "top1_skill": "string",
    "candidates": ["string"],
    "misdelegated": false,
    "fell_back": false
  },
  "trace": { },                                  // reuses existing GCL trace
  "golden_ref": "string|null",                   // links to assets/golden/*.json
  "fixture_ref": "string|null",                  // links to CLI-response fixture
  "safety": {
    "destructive": "bool",
    "token": "string|null",                      // confirmation token
    "plan_hash": "string|null",                  // token <-> plan 1:1 binding
    "leak_checked": "bool"                       // Critic raw-request leakage guard
  },
  "provenance": {                                // 100% trace provenance
    "source": "string",
    "tool": "string",
    "captured_at": " ISO8601"
  },
  "budgets": {                                   // per-run efficiency budgets
    "context_tokens": "int",
    "tool_calls": "int",
    "wall_clock_ms": "int"
  },
  "cost": { "tokens": "int", "usd": "float|null" },
  "scores": {                                    // existing GCL dimensions
    "correctness": 0, "safety": 0, "idempotency": 0,
    "traceability": 0, "spec_compliance": 0
  }
}
```

Every `EvidenceRecord` is persisted under `audit-results/evidence-*.json` (gitignored,
parallel to existing `gcl-trace-*`).

## KPI / measurement layer

The kernel MUST emit these metrics; CI fails if any target is unmet:

| # | Metric | Target | Kernel field |
|---|--------|--------|--------------|
| 1 | Critic raw-request leakage | 0 | `safety.leak_checked` |
| 2 | destructive Guardrail coverage | 100% | `safety.destructive` + `token` present when true |
| 3 | Golden coverage per executable skill | ≥5 | count of `golden_ref` per `skill` |
| 4 | Changed-skill regression execution rate | 100% | `phase=self-test` required on change |

**KPI #4 trigger mechanism**: CI runs
`git diff --name-only origin/main...HEAD | grep '^qcloud-.*-ops/'` to collect
affected skills, then forces their golden scenarios (`phase=self-test`) to pass
before merge. A changed skill with no passing self-test run fails CI.

**A-B gate definition**: A-B = output-consistency comparison between the
**candidate** model/version and the current **production baseline** on the same
golden input set. Divergence beyond an allowed threshold blocks promotion. (A-B is
distinct from Golden, which checks the candidate against the expected fixture alone.)
| 5 | Trace provenance completeness | 100% | `provenance` non-empty |
| 6 | self-test↔production metric mixing | 0% | `phase` strictly separated |
| 7 | Router Top-1 / misdelegation / fallback | observable | `router_decision` |
| 8 | P95 latency / avg token / tool calls / cost | observable | `budgets` + `cost` aggregation |

## Phase 1 — Evidence-based Trust

- **Executable skill** = any `qcloud-*-ops` skill whose `cli_applicability` is
  `dual-path` / `cli-first` / `sdk-only` (i.e. performs mutating or read actions),
  excluding pure cross-product meta references. Read-only `cli-only` skills need ≥2
  golden scenarios (coverage KPI #3 scales accordingly).
- **Golden scenarios**: each executable skill gets ≥5 golden scenarios in
  `qcloud-*-ops/assets/golden/*.json` (input intent + expected structured output).
- **CLI fixtures + sandbox E2E**: `scripts/sandbox_e2e.py` runs skills against recorded
  `tccli`/SDK response fixtures (no live credentials) and asserts golden match.
- **CI gates**: Golden / A-B / Telemetry / TE gates become *required* in
  `scripts/validate_local.py` (additive).
- **Telemetry split**: `phase` dimension strictly separates self-test / sandbox /
  production; mixing is a CI failure (KPI #6).
- **Capability Manifest + maturity report**: machine-generated from Registry + Evidence,
  emitted on every CI run.

## Phase 2 — GCL Loop Hardening

- **Closed retry**: Critic emits structured feedback (field-level diff + blocking flag),
  Orchestrator feeds it back to Generator as a concrete retry spec — not just a score.
- **Process timeout**: every Generator/Critic subprocess bounded by `wall_clock_ms`.
- **Schema validation**: every `EvidenceRecord` validated against the schema before
  persistence (CI gate).
- **Trace masking**: kernel enforces `{{env.*}}` / `{{output.operation_intent}}`
  sanitization; `safety.leak_checked` recorded (KPI #1).

## Phase 3 — Autonomous Runtime Safety

- **Destructive detection**: harness classifies each action against a destructive-action
  dictionary + schema; sets `safety.destructive` automatically (PreFlight).
- **Token issuance = human-in-the-loop (NON-WEAKENING)**: the harness generates the
  execution plan and its `plan_hash`, but the confirmation token is **issued by a human**
  at the plan-review gate — NOT auto-generated by the harness. This preserves the
  existing AGENTS.md hard rule that destructive ops require explicit human confirmation.
  The harness only binds the human-issued token 1:1 to `plan_hash` and refuses execution
  unless they match (KPI #2, 100% coverage).
- **Token↔plan binding**: execution is refused unless the human-issued token matches the
  `plan_hash` of the specific execution plan.

## Phase 4 — Harness Efficiency

- **Unified Registry + Router** (kernel layer 2): machine-built Registry; Router loads
  only frontmatter for candidate selection, progressive-loads `references/` on hit.
- **Per-run budgets**: `budgets` enforced by Router (context tokens / tool calls /
  wall-clock).
- **Intent confusion matrix**: Registry emits confusion matrix from `router_decision`
  over the **existing** `assets/eval_queries.json` intent-classification set (reused as
  ground truth, not newly built) (KPI #7).
- **Convergence**: single `make` entry wrapping validate_local, sandbox_e2e, manifest
  generation, and CI; lock dependencies; unify local-dev entry point.

## File / artifact placement

| Artifact | Location | Owner |
|----------|----------|-------|
| EvidenceRecord schema | `docs/evidence-kernel-schema.json` | harness core |
| Golden scenarios | `qcloud-*-ops/assets/golden/*.json` | owning skill |
| CLI fixtures | `qcloud-*-ops/assets/fixtures/*.json` | owning skill |
| sandbox E2E runner | `scripts/sandbox_e2e.py` | harness core (shared) |
| Evidence schema validator | `scripts/validate_evidence_schema.py` | harness core (shared) |
| Registry builder | `scripts/build_skill_registry.py` | harness core (shared) |
| Manifest + maturity | `audit-results/capability-manifest.json` | generated |
| Router | `scripts/harness_router.py` | harness core (shared) |

Follows AGENTS.md asset-placement rule: shared executables in `scripts/`, skill-specific
data in owning skill's `assets/`.

## Self-check / verification

- `python3 scripts/build_skill_registry.py --check` asserts every executable skill has
  ≥5 golden scenarios (KPI #3) and Registry frontmatter is parseable.
- `python3 scripts/sandbox_e2e.py` exits non-zero if any golden mismatch (Phase 1 gate).
- `python3 scripts/validate_evidence_schema.py` rejects any `EvidenceRecord` with empty
  `provenance` or missing `safety` (KPI #1, #2, #5).
- `assert not errors` in each runner; CI treats KPI unmet as failure.
- Existing `validate_local.py`, `cadl_lint.py`, `gcl_trace_aggregate.py` remain required
  and untouched in behavior.

## Out of scope (YAGNI)

- Rewriting existing GCL/worktree/CADL rules.
- Live-cloud execution paths (fixtures only; tccli stays primary for real runs).
- Per-skill UI/dashboards beyond the maturity report JSON.
