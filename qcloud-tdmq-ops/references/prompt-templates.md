# TDMQ GCL Prompt Templates

> **TE-6:** G/C/O backbone → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4.

| Override | Value |
|---|---|
| skill | `qcloud-tdmq-ops` |
| CLI | `tccli tdmq help` |
| max_iterations | 2 |

Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (TDMQ).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (TDMQ — 3 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–3; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Validate → Recover).

---

## 5. Anti-patterns (banned)

> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.

- ❌ **Deleting a RocketMQ cluster without emptying it first** — TDMQ-specific: `DeleteRocketMQCluster` destroys all child namespaces/topics/groups/messages; verify empty first.
- ❌ **Deleting a topic with active consumers** — TDMQ-specific: in-flight messages and subscription state are lost; warn and detach consumers.
- ❌ **Resetting consumer offset without confirming target** — TDMQ-specific: wrong timestamp reprocesses or skips large message volumes; confirm with user.
- ❌ **Using TDMQ for Kafka workloads** — TDMQ-specific: Kafka → delegate to `qcloud-ckafka-ops`.
- ❌ **Credential in trace** — SecretKey / password literals ⇒ safety=0.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-09 | Initial TDMQ prompt templates: G/C/O + per-op variants + anti-patterns. TE-6 → gcl-prompt-backbone. |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill)
- [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned)
- [rubric.md](rubric.md)
- [SKILL.md](../SKILL.md)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations)
