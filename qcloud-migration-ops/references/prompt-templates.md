# Migration GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-migration-ops` |
| CLI | `tccli msp` (primary), SDK fallback |
| max_iterations | 2 |

Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (Migration).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (Migration — 3 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–3; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

---

## 5. Anti-patterns (banned)


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.


- ❌ **Deregister running migration task** — Migration-specific: deregistering a migration task that is RUNNING abandons the data transfer mid-process, potentially leaving the target in an inconsistent state; the Generator must verify task is COMPLETED or STOPPED and the Critic must catch it.
- ❌ **Change migration status without warning** — Migration-specific: modifying migration task status (e.g., stopping a running migration) has similar implications to deregister; the Generator must warn about data loss implications and the Critic must catch it.
- ❌ **Register migration without source validation** — Migration-specific: registering a migration task with an invalid or unreachable source config will fail after queue time; the Generator must validate source config and network reachability upfront and the Critic must catch it.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-04 | Initial Migration GCL templates: Generator + Critic + Orchestrator templates for Migration (3 rules, dual-path execution, data loss guard, status change warning, pre-validation). |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [rubric.md](rubric.md) — the rubric instance these templates score against
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables
