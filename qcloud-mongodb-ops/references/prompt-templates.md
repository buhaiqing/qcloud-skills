# MongoDB GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-mongodb-ops` |
| CLI | `tccli mongodb help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (MongoDB).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (MongoDB — 5 rules). Do not duplicate gate text here.

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


- ❌ **Logging passwords or credentials** — extending the AGENTS.md list with the
  MongoDB-specific ban on letting `{{user.password}}` / `{{user.new_password}}` /
  `TENCENTCLOUD_SECRET_KEY` appear unmasked anywhere in command, response, or trace.
- ❌ **`DropDatabase` / `DropCollection` without backup check** — MongoDB-specific:
  `DropDatabase` removes ALL documents + indexes + the namespace's oplog window
  entries. Unlike `IsolateDBInstance` (per-instance recycle bin), there is **no
  per-database recycle bin**. The agent must call `DescribeDBBackups` first and
  refuse to drop if any in-retention backup can still cover the namespace.
- ❌ **`TerminateDBInstances` batch without enumerating replica-set members** —
  MongoDB-specific: each `cmgo-` instance in a batch may be a primary of its own
  replica set; the agent must call `DescribeDBInstanceNodeProperty` for EACH
  instance, surface the count of secondaries, and run `--DryRun` first. Skipping
  this strands the secondaries with no path to elect a new primary.
- ❌ **`ModifyDBInstanceSpec` downgrade without surfacing `RealInstanceUsage` /
  `MemoryUsage`** — MongoDB-specific: shrinking `Volume` below `1.2 × used disk`
  is rejected with `SetDiskLessThanUsed` (the API catches this), but shrinking
  `Memory` below peak working set is NOT caught by the API — the instance
  silently OOM-kills connections and queries. The agent must query
  `DescribeDBInstanceNodeProperty` + Cloud Monitor `MemoryUsage` and warn the
  user before committing.
- ❌ **Treating `IsolateDBInstance` as a soft pause** — MongoDB-specific: a
  postpaid isolated instance has a 7-day recycle bin, but **the instance cannot
  be mutated** while isolated (`Status=3`). Calling `ModifyDBInstanceSpec` or
  `ModifyAccountPassword` on an isolated instance returns
  `InvalidParameterValue.IllegalInstanceStatus`. The agent must surface the
  recycle-bin window AND the "no-mutation-while-isolated" constraint.
- ❌ **Logging the new password after `ResetDBInstancePassword`** — MongoDB-specific:
  the password rotation is sensitive; the agent should report "password reset
  succeeded" without echoing the new value. Duplicate calls (response lost
  scenario) could otherwise apply a second password without obvious failure.
- ❌ **Silent `Mask=3` privilege escalation** — MongoDB-specific: `SetAccountUserPrivilege`
  with `Mask=3` (read-write) is immediate; existing read-only sessions are upgraded
  on next reconnect. The agent must surface the BEFORE/AFTER privilege diff and
  warn the user.
- ❌ **Re-firing `FlashBackDBInstance` / `RestoreDBInstance` on transient async
  errors** — MongoDB-specific: these are destructive + slow; the original
  `FlowId` may still be running. The agent must `DescribeAsyncRequestInfo` first
  to confirm the original task status before any retry.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 MongoDB rollout: Generator + Critic + Orchestrator templates for MongoDB (5 rules, instance-isolate/destroy, data-plane drop guard, spec-change OOM risk, root password no-recovery, SG lockout guard). Initial delta scaffold under §1 / §4 / §5 / §6 only |
| 1.1.0 | 2026-06-19 | Tier-A conformance flesh-out (7 sections): expanded §1 Generator (~150 lines, includes replica-set + oplog invariants, spec-downgrade invariants, drop invariants, account/password masking), new §2 Critic (5-dimension scoring + Critic isolation + replica-set/spec-downgrade structured checks), new §3 Orchestrator (decision logic, thresholds, trace persistence with failure_pattern extraction), expanded §4 (full per-operation table with 11 ops + out-of-scope data-plane guard + read-only Well-Architected variant), expanded §5 (8 MongoDB-specific anti-patterns: DropDatabase no-UNDROP, batch Terminate without replica-set enumeration, ModifySpec downgrade without RealInstanceUsage, IsolateDBInstance as soft pause, password leak, Mask=3 silent escalation, FlashBack/Restore re-fire), new §7 See also |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [rubric.md](rubric.md) — the rubric instance these templates score against
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — canonical Tier-A template (object storage, 7 sections)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (RDBMS, 7 sections)
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (compute, 7 sections)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-mongodb-ops` is `required`, `max_iter=2`
- [AGENTS.md §6 Trace & Audit](../../AGENTS.md#6-trace--audit-mandatory) — trace schema for `failure_pattern` extraction
- [docs/failure-patterns.md](../../docs/failure-patterns.md) — Reflexion memory; cross-session failure pattern learning
