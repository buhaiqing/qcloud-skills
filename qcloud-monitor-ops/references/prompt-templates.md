# Monitor GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-monitor-ops` |
| CLI | `tccli monitor help` |
| max_iterations | 3 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (Monitor).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **3**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (Monitor — 5 rules). Do not duplicate gate text here.

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


- ❌ **Logging credential / webhook auth token** — extending the AGENTS.md list
  with the Monitor-specific ban on letting `TENCENTCLOUD_SECRET_KEY` or webhook
  URL auth tokens (path/query of the URL) appear unmasked anywhere in command,
  response, or trace.
- ❌ **`DeleteAlarmPolicy` without listing bindings** — Monitor-specific: this is
  the most common silent-incident bug. The agent must surface the
  `DescribeBindingAlarmPolicy` BEFORE snapshot (resource count + types + IDs)
  before the destructive call. Deleting an in-use policy stops notifications for
  every bound resource, with no error and no signal to the resource owner.
- ❌ **`ModifyAlarmPolicy` threshold drift without explicit diff** — Monitor-specific:
  the agent must render a field-level BEFORE/AFTER diff for any condition change
  and require explicit confirmation per changed field. Threshold drift in either
  direction is dangerous (higher = missed incidents, lower = false positives),
  and the change is applied immediately.
- ❌ **`DeleteAlarmNotices` in-use** — Monitor-specific: notice templates are shared
  across alarm policies. Deleting an in-use template stops notifications for all
  referencing policies, with no error. The agent must list referencing policies via
  `DescribeAlarmPolicies` filtered by NoticeId BEFORE the destructive call.
- ❌ **`SetDefaultAlarmPolicy` without scope understanding** — Monitor-specific: the
  default alarm policy applies to ALL un-bound / future resources in the namespace.
  Changing it has the largest blast radius of any Monitor mutation. The agent must
  warn explicitly and require blast-radius acknowledgement.
- ❌ **`CreateAlarmNotice` with empty receivers** — Monitor-specific: alarms that
  fire with no notification channel configured are invisible. The agent must
  verify at least one populated receiver (UserIds / UserGroups / WebHook) matches
  the chosen NoticeType BEFORE commit.
- ❌ **Mutating during read-only assessment mode** — Monitor-specific: when invoked
  by `qcloud-well-architected-review`, the agent MUST restrict to
  `GetMonitorData` + `DescribeAlarm*` + `DescribeAllNamespaces`. Any Create /
  Modify / Delete op is a spec_compliance = 0 + safety = 0 violation ⇒ ABORT.
- ❌ **Mutating auto-remediation tasks without per-task confirmation** — Monitor-specific:
  `ModifyAlarmPolicyTasks` (auto-remediation, e.g. AS reactions) may trigger
  automatic scaling/replacement without human approval. The agent must require
  explicit confirmation per task and warn that enabling may have production
  consequences.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Monitor rollout: templates (5 rules, alarm-policy deletion silent incident, unbinding coverage loss, threshold drift, notice template silence, default policy reach) |
| 1.1.0 | 2026-06-19 | Tier A flesh-out: full G/C/O detail; **BEFORE/AFTER double snapshot** mandatory in §1 Generator and §2 Critic (Monitor-specific audit-grade traceability for silent-incident class); §4 expanded with per-operation variants including `BindAlarmRuleResource` and `CreateAlarmNotice` empty-receiver guard; §5 Anti-patterns expanded with Monitor-specific bans (binding-less delete, threshold drift without diff, in-use notice delete, default policy blast radius, empty receivers, read-only mode mutations, auto-remediation without confirmation); §7 See also added; placeholder convention and Critic isolation hardened per AGENTS.md §7 |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §9 Anti-Patterns](../../AGENTS.md#9-anti-patterns-banned) — shared anti-patterns
- [AGENTS.md §14 Reflexion Integration](../../AGENTS.md#14-reflexion-integration-lightweight-reflexion) — failure pattern memory
- [rubric.md](rubric.md) — the rubric instance these templates score against (5 dimensions, 5 Monitor-specific safety rules)
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables
- [SKILL.md §Quality Gate (GCL)](../SKILL.md#quality-gate-gcl) — per-skill GCL header table (max_iter=3)
- [SKILL.md §Read-Only Assessment Mode](../SKILL.md#read-only-assessment-mode-delegate-from-qcloud-well-architected-review) — `qcloud-well-architected-review` delegation contract
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (object storage pilot)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (SQL database pilot)
- [`qcloud-cos-ops/references/rubric.md`](../cos-ops/references/rubric.md) — sibling rubric (canonical Tier A format reference)
