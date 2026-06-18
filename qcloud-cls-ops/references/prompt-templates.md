# CLS GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-cls-ops` |
| CLI | `tccli cls help` |
| max_iterations | 3 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (CLS).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **3**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (CLS — 5 rules). Do not duplicate gate text here.

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


- ❌ **Logging credentials / secrets** — extending the AGENTS.md list with the CLS-specific
  ban on letting `TENCENTCLOUD_SECRET_KEY`, `TENCENTCLOUD_SECRET_ID`, and any cross-skill
  secret content appear unmasked anywhere in command, response, or trace.
- ❌ **`DeleteLogset` without topic enumeration** — CLS-specific: the single most
  dangerous bug in this skill. `DeleteLogset` cascades to all topics and indexes; an
  active shipper targeting a topic in this logset will be silently orphaned. The
  Generator must enumerate every topic + shipper + alarm in the logset, and the
  Critic must require the literal `CONFIRM DELETE LOGSET <name>` token.
- ❌ **`DeleteTopic` without shipping task check** — CLS-specific: if a topic has an
  active shipper to COS or CKafka, deleting the topic breaks the shipping pipeline
  silently (the shipper is configured, the destination exists, but no logs are written
  because the source topic is gone). The most common incident: "I deleted a topic to
  reorganize but the COS shipping task was still configured and failed with 'topic
  not found' on every batch for 2 days". Generator must `DescribeShippers` first.
- ❌ **`ModifyTopic` retention reduction with audit obligations** — CLS-specific:
  retention reduction is a **silent data loss** operation. Unlike `IsolateDBInstance`
  (which has a 7-day window), CLS retention truncation is immediate and irreversible.
  The Generator must surface the projected data loss (current storage × reduction
  ratio) AND verify the COS / CKafka shipper has the historical data before reducing
  retention — otherwise compliance audit obligations are broken silently.
- ❌ **`CreateIndex` full-text without cost projection** — CLS-specific: full-text
  index cost is widely underestimated. The most common incident: "I enabled full-text
  on a 50 GB/day topic with 90-day retention — my CLS bill jumped 4× the next
  month". Generator must surface projected monthly cost = daily × ~1× full-text
  × retention, AND warn that adding `KeyValue` after `FullText` requires
  `DeleteIndex` + `CreateIndex` (search unavailability window).
- ❌ **`DeleteIndex` without re-index cost warning** — CLS-specific: search queries
  on that index fail until recreated. The Generator must surface the rebuild
  window and require explicit confirmation; the most common incident is
  "I deleted the index to fix a typo, but now nothing in this topic is searchable".
- ❌ **`ModifyConfig` path without old-path coverage** — CLS-specific: path changes
  stop ingest from the old path on the next polling cycle (~60s). The most common
  incident: "I changed the log collection path from `/var/log/app/*.log` to
  `/var/log/app/*.json` and the agent stopped collecting `.log` files — we had a
  4-hour gap in the logs". Generator must show BEFORE/AFTER diff and warn per
  changed field.
- ❌ **`DeleteMachineGroup` without agent reassignment** — CLS-specific: silently
  stops log collection on the CVMs in the group. The Generator must enumerate the
  CVM instances + attached configs first; if there are attached configs, the user
  must `DeleteConfigAttachment` first or explicitly accept the collection stop.
- ❌ **`CreateShipper` to non-existent target** — CLS-specific: the shipper is
  configured, the destination is missing, and the first delivery fails silently
  minutes later. The Generator must `HeadBucket` / `DescribeTopics` the target via
  `qcloud-cos-ops` / `qcloud-ckafka-ops` before issuing the create; the Critic
  must catch the missing cross-skill check.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CLS rollout: Generator + Critic + Orchestrator templates for CLS (5 rules: logset cascade, topic data loss, retention truncation, index full-text cost, config change gap); isolated-context enforcement |
| 1.1.0 | 2026-06-19 | Tier A flesh-out: expanded §1 Generator with full variable table, 10-step pre-flight, polling-tail + cross-skill-checks trace fields; expanded §2 Critic with 5-dimension CLS-specific scoring rules, `rule_violations` extended to all CLS mutation ops (DeleteLogset / DeleteTopic / ModifyTopic / CreateIndex / ModifyConfig / ApplyConfigToMachineGroup / DeleteConfigAttachment / DeleteMachineGroup / CreateShipper / CreateCosRecharge); expanded §3 Orchestrator with `max_iter=3` rationale and the 5 unconditional-ABORT triggers; expanded §4 with per-operation pre-flight augmentations, read-only posture for `SearchLog` / `Describe*`, and TKE out-of-scope guard; expanded §5 with 11 CLS-specific anti-patterns; added §7 See also |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-cls-ops` is `recommended`, `max_iter=3`
- [AGENTS.md §9 Anti-Patterns](../../AGENTS.md#9-anti-patterns-banned) — cross-skill banned list
- [AGENTS.md §14 Reflexion Integration](../../AGENTS.md#14-reflexion-integration-lightweight-reflexion) — failure pattern memory for cross-session learning
- [rubric.md](rubric.md) — the rubric instance these templates score against (5 dimensions + 5 CLS-specific safety rules)
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables; `## Quality Gate (GCL)` chapter
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time sibling for DeleteLogset / DeleteTopic / DeleteIndex / DeleteMachineGroup / ModifyConfig
- [SKILL.md §Error Code Reference](../SKILL.md#error-code-reference) — 20+ CLS error codes with HALT vs retry
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (object storage, with FinOpsAnalysis read-only variant)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (database, with SQL out-of-scope guard)
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (compute, the Phase 1 pilot)
