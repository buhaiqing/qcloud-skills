# Architecture Decision Records (ADRs)

> Per [ADR-0001](ADR-0001-establish-adr-mechanism.md), this directory holds
> cross-subsystem architectural decisions for `qcloud-skills`. Each ADR records
> *why* we chose one path over another, *what* the consequences are, and how
> later ADRs may supersede it.

## Glossary

| Term | Full name | Purpose | Doc |
|---|---|---|---|
| **ADR** | Architecture Decision Record | Documents a cross-subsystem decision: why we chose X over Y, consequences, and how later ADRs supersede it. | `docs/architecture/ADR-*.md` |
| **CADL** | Compound-Asset Distillation Loop | Per-task lesson → persistent reusable asset. 5 steps: Extract → Place → Write → Gate → Reuse. | `docs/cadl-spec.md` |
| **GCL** | Generator-Critic Loop | Runtime quality gate: Generator produces, Critic scores (Safety, Quality), loop bounded by max_iterations. | `docs/gcl-spec.md` |
| **Reflexion** | Reflexion Memory | Cross-session failure pattern store. Dedupe by `skill + command + error`. Patterns from GCL traces or self-review. | `docs/reflexion-memory.md` |
| **Hook** | CADL Hook Line | Canonical marker at end of `SKILL.md` that triggers CADL self-reflection. | `qcloud-skill-generator/references/qcloud-skill-template.md` |
| **CLI** | Command Line Interface (Tencent Cloud) | Primary execution path (`tccli`). SDK fallback when CLI unavailable. | `qcloud-*-ops/references/cli-usage.md` |

**Boundary rule**: Single-task lessons / CLI error patterns → CADL. Cross-subsystem / long-term direction → ADR. (See [ADR-0001 §2.5](ADR-0001-establish-adr-mechanism.md#25-boundary-with-cadl-critical))

## Index

```
README.md                              # This file
ADR-0001-establish-adr-mechanism.md   # ADR mechanism definition
ADR-0002-l3-to-l4-daemon-migration.md # L3→L4 daemon decision
ADR-0003-faiops-event-driven-architecture.md # FinOps/AIOps/SecOps events
```

## When to write an ADR

Write an ADR (instead of, or in addition to, a CADL entry) when the decision:

- Affects **more than one subsystem** (e.g. introduces a new top-level package, changes cross-skill data flow, alters the runtime topology).
- Commits the project to a **long-term direction** (e.g. dual-mode execution model, choice of bus technology).
- Would otherwise be **re-litigated** by future contributors/agents.

See [ADR-0001 §2.5](ADR-0001-establish-adr-mechanism.md#25-boundary-with-cadl-critical) for the CADL boundary.

## ADR lifecycle

```
Proposed ──► Accepted ──► Superseded by ADR-NNNN
                 │
                 └────► Deprecated
   │
   └──► Rejected
```

See [ADR-0001 §2.2](ADR-0001-establish-adr-mechanism.md#22-lifecycle-states) for full semantics.

## Index

| ID | Title | Status | Date | Topic |
|---|---|---|---|---|
| [ADR-0001](ADR-0001-establish-adr-mechanism.md) | Establish ADR mechanism | Accepted | 2026-07-28 | Meta / process |
| [ADR-0002](ADR-0002-l3-to-l4-daemon-migration.md) | L3→L4 via `qcloud-agent-daemon/` | Accepted | 2026-07-28 | Runtime topology |
| [ADR-0003](ADR-0003-faiops-event-driven-architecture.md) | FinOps/AIOps/SecOps event-driven | Accepted | 2026-07-28 | Business events |

## Related (not ADRs themselves)

| Document | Purpose |
|---|---|
| `docs/superpowers/specs/qcloud-agent-daemon-design.md` | Design for ADR-0002 + ADR-0003 |
| `docs/superpowers/plans/qcloud-agent-daemon-implementation.md` | Phase 1+2 implementation plan |
| `../gcl-spec.md` | GCL protocol (called from daemon ExecutionPipeline) |
| `../reflexion-memory.md` | Reflexion (auto-mode runs feed this) |
| `../cadl-spec.md` | CADL (per-task lessons, not decisions) |
| `../../AGENTS.md` | P0 rules + ADR reference |

## Review cadence

Quarterly: each `Accepted` ADR is re-checked; if reality has drifted, mark `Superseded` or `Deprecated` with a link to the replacement.
