# qcloud-skill-generator GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-skill-generator` |
| CLI | `tccli n/a help` |
| max_iterations | 3 |
- **Meta** — audits generated artifact

Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (Generator).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **3**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (Generator — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

Charter C1–C7: [SKILL.md §Post-Generation Self-Check](../SKILL.md#post-generation-self-check------).

---

## 5. Anti-patterns


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.

- ❌ **Generating without API doc URL** — trace must cite source
- ❌ **Copying from another skill without re-deriving** — API fidelity drift
- ❌ **Credential literals in examples** — Safety=0 → ABORT
- ❌ **Skipping 2-round self-review** — build-time gate bypass
- ❌ **Shared-context G+C** — Critic must not see user request

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-18 | Tier D meta-skill prompt skeletons (Charter C1-C7 variants) |
| 1.1.0 | 2026-06-19 | Tier D conformance rollout |

| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [`rubric.md`](rubric.md) — 5 dimensions + 5 generator safety rules
- [governance-and-adversarial-review.md](governance-and-adversarial-review.md)
- [SKILL.md §Post-Generation Self-Check](../SKILL.md#post-generation-self-check------)
- [AGENTS.md §10 GCL spec](../../AGENTS.md#10-generator-critic-loop-gcl--adversarial-quality-gate)
