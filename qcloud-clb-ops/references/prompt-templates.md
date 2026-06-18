# CLB GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-clb-ops` |
| CLI | `tccli clb help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (CLB).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (CLB — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

---

## 5. Anti-patterns (banned)


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.


- ❌ **Silent Internet↔Internal flip** — CLB-specific: switching the LB type without
  surfacing the public-IP release is the same family of bug as a credential leak; the
  Generator must show the BEFORE/AFTER diff and the Critic must catch it.
- ❌ **Mass deregister without drain** — CLB-specific: dropping active sessions
  without `ConnectionDrainTimeout` is the most common "why did our API start returning
  502" incident; the 50% threshold is the heuristic catch.
- ❌ **Register non-running targets** — CLB-specific: a target that is `STOPPED` will
  never receive traffic but stays in the "registered" list, masking the failure as a
  misconfigured LB.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CLB rollout: Generator + Critic + Orchestrator templates for CLB (5 rules, isolated-context enforcement, Internet↔Internal flip hygiene, mass-drain guard, non-running target rejection) |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [rubric.md](rubric.md) — the rubric instance these templates score against
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md), [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md), [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates
