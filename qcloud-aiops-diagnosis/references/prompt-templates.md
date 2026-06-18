# AIOps Diagnosis GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-aiops-diagnosis` |
| CLI | `tccli monitor help` |
| max_iterations | 5 |
- **Read-only** — no mutations in trace

Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (AIOps).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **5**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (AIOps — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

Diagnosis routing: [`cross-skill-orchestration.md`](cross-skill-orchestration.md).

---

## 5. Anti-patterns


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.

- ❌ **Critic sees user request** — rubber-stamping; banned per AGENTS.md §9
- ❌ **Mutation in read-only skill** — any Create/Modify/Delete in trace → Safety=0
- ❌ **Correlation without evidence** — HIGH confidence requires ≥ 2 layers + time overlap
- ❌ **Auto-execute recommendation** — must prefix and delegate, never run product mutating ops
- ❌ **Stale data silent** — Rule 4 requires source_recency and stale warnings

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-09 | Initial Generator, Critic, Orchestrator templates |
| 1.1.0 | 2026-06-19 | Renumbered to canonical 7 sections (Tier C conformance) |

| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7 Prompt Templates](../../AGENTS.md#7-prompt-templates-mandatory-per-skill)
- [`rubric.md`](rubric.md) — 5 dimensions + 5 AIOps safety rules
- [`cross-skill-orchestration.md`](cross-skill-orchestration.md)
- [SKILL.md](../SKILL.md)
