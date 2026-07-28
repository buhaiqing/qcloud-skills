# ADR-0001: Establish Architecture Decision Record (ADR) Mechanism

> **Status**: Accepted
> **Date**: 2026-07-28
> **Deciders**: Architecture review (orchestrator + FinOps/AIOps/SecOps scope)
> **Supersedes**: —
> **Related**: AGENTS.md §"Spec-Plan-Code Alignment Gate", docs/cadl-spec.md, docs/gcl-spec.md

## 1. Context

The repo currently documents **technical implementations** well (`docs/gcl-spec.md`, `docs/reflexion-memory.md`, `docs/cadl-spec.md`) but has **no canonical place** for cross-subsystem *architectural* decisions — choices that span multiple skills, affect runtime topology, or commit the project to a long-term direction.

Concrete gaps observed while planning the L3→L4 daemon migration:

1. The decision "we will introduce a persistent daemon + EventSource abstraction" affects 30+ skills, the runtime topology, and the failure model. There is no current document that records *why* we chose this over alternatives.
2. New contributors (and AI agents) re-litigate the same architectural questions every session.
3. JDCloud already maintains `docs/architecture/*.md` as ADR container (see `2026-07-28-l3-to-l4-agent-daemon-adr.md` upstream). Cross-repo alignment benefits from a sibling convention.

## 2. Decision

We adopt a lightweight ADR mechanism with the following contract.

### 2.1 Where ADRs live

| Aspect | Choice |
|---|---|
| Directory | `docs/architecture/` (new, see §2.6) |
| Filename | `ADR-NNNN-<kebab-case-topic>.md` (zero-padded 4-digit) |
| Index | `docs/architecture/README.md` (chronological + topic-grouped) |
| Format | Markdown with H1 + structured H2 sections (see §2.3) |

**Rationale for `ADR-NNNN` over date-prefix**: stable cross-references (`see ADR-0002 §3.2`) survive renames and rewrites; date-prefix filenames duplicate information already in frontmatter.

### 2.2 Lifecycle states

| Status | Meaning | Allowed transitions |
|---|---|---|
| `Proposed` | Drafted, seeking consensus | → `Accepted` / `Rejected` |
| `Accepted` | Decision in force | → `Superseded by ADR-NNNN` / `Deprecated` |
| `Superseded` | Replaced by a later ADR (must link it) | terminal |
| `Rejected` | Considered but not adopted (kept for history) | terminal |
| `Deprecated` | No longer applicable (must give reason) | terminal |

### 2.3 Required sections

Every ADR MUST contain these H2 sections (in this order):

1. **Status / Date / Deciders / Supersedes / Related** — frontmatter block
2. **Context** — problem, forces, constraints
3. **Decision** — what we will do (numbered sub-decisions when more than one)
4. **Alternatives Considered** — at least one with explicit rejection reason
5. **Consequences** — positive, negative, mitigations
6. **Changelog** (optional) — version-by-version edits to the same ADR

ADRs MAY reference other ADRs and MAY include code snippets, but MUST NOT contain executable scripts or runtime artifacts.

### 2.4 Boundary with existing docs

| Document | Scope | When to use |
|---|---|---|
| `AGENTS.md` | P0 rules, hard constraints, agent-agnostic principles | Always referenced; never duplicated |
| `docs/gcl-spec.md` | GCL protocol (Generator/Critic/Decide loop) | Implementation protocol |
| `docs/reflexion-memory.md` | Cross-session failure pattern memory | Runtime learning system |
| `docs/cadl-spec.md` | Per-task asset distillation | Post-task closure |
| **`docs/architecture/ADR-NNNN-*.md`** | **Cross-subsystem architectural decisions** | **This ADR mechanism** |

### 2.5 Boundary with CADL (critical)

| Aspect | ADR | CADL |
|---|---|---|
| Trigger | Affects >1 subsystem or runtime topology | Per-task lesson, even single-file |
| Owner | Architecture review (multi-role) | Each task executor |
| Output size | 100-400 lines | ≤30 lines per entry, ≤200 lines per file |
| Update cadence | Months | Per task |
| Example | "We adopt `qcloud-agent-daemon/` as a new top-level package" | "E741 ambiguous `l` in `validate_local.py` (count+=1)" |

**Rule of thumb**: If the lesson is "I learned a tricky parameter combination", it's CADL. If the lesson is "We picked X over Y because …", it's ADR.

### 2.6 Directory creation

We create `docs/architecture/` and seed it with:

| File | Purpose |
|---|---|
| `README.md` | ADR index + writing rules pointer to this ADR |
| `ADR-0001-establish-adr-mechanism.md` | This file |
| `ADR-0002-l3-to-l4-daemon-migration.md` | L3→L4 daemon decision (sibling) |
| `ADR-0003-faiops-event-driven-architecture.md` | FinOps/AIOps/SecOps event model (sibling) |

`.gitignore` already excludes `.runtime/` (generated) — `docs/architecture/` is committed.

## 3. Alternatives Considered

### A. No ADR — rely on AGENTS.md and PR descriptions
**Rejected**: PR descriptions are ephemeral; AGENTS.md is for rules not decisions. Future contributors cannot reconstruct *why*.

### B. Embed ADRs in each subsystem's docs/
**Rejected**: Spreads decisions across 30+ skill directories; impossible to index or audit cross-subsystem effects.

### C. Use ADR tools (e.g. `adr-tools`, `log4brains`)
**Rejected**: Adds external dependency for what is essentially "numbered Markdown files". Tools can be retrofitted later if scale demands.

### D. Date-prefix filenames (JDCloud style)
**Rejected**: Stable cross-references prefer numeric IDs. We can still surface the date in frontmatter.

## 4. Consequences

**Positive**:
- Decisions are reviewable in isolation; supersession chain preserves history.
- Cross-repo consistency with JDCloud reduces context-switch cost.
- Low overhead: zero tooling, zero CI changes, ~120 lines per ADR.

**Negative**:
- Requires discipline to write ADRs vs. defaulting to inline PR descriptions.
- ADR sprawl risk (mitigated by quarterly review of `docs/architecture/README.md`).

**Mitigations**:
- AGENTS.md references ADR-0001 for "when to write an ADR" (updated in this initiative).
- Quarterly: each ADR's `Status` is re-checked; outdated ones marked `Deprecated` or `Superseded`.

## 5. Related

- AGENTS.md §"Spec-Plan-Code Alignment Gate" — Spec/Plan must trace to ADRs when applicable
- docs/cadl-spec.md §4 — CADL asset types table distinguishes "Decision record" landing here
- JDCloud `2026-07-11-llm-native-agent-inband-adr.md` (upstream) — pattern inspiration

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-28 | Initial ADR-0001 |
