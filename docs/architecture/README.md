# Architecture Decision Records (ADRs)

> Per [ADR-0001](ADR-0001-establish-adr-mechanism.md), this directory holds
> cross-subsystem architectural decisions for `qcloud-skills`. Each ADR records
> *why* we chose one path over another, *what* the consequences are, and how
> later ADRs may supersede it.

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
