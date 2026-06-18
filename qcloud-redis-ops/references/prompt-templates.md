# Redis GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-redis-ops` |
| CLI | `tccli redis help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (Redis).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (Redis — 5 rules). Do not duplicate gate text here.

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
  Redis-specific ban on letting `{{user.password}}`, `{{user.new_password}}`,
  `TENCENTCLOUD_SECRET_KEY`, `TENCENTCLOUD_SECRET_ID` appear unmasked anywhere in
  command, response, or trace. ClearInstance leaks are particularly dangerous
  because the data-plane call is the only place those passwords were ever typed.

### Redis-specific anti-patterns

- ❌ **ClearInstance FLUSHALL without literal `CONFIRM FLUSH <instance_id>` token**
  — FLUSHALL is invisible to Tencent Cloud API audit; the literal token is the
  only paper trail. A "yes, go ahead" or "proceed" is NOT sufficient.
- ❌ **ClearInstance without DBSIZE / INFO keyspace post-check** — the protocol-level
  `+OK` reply alone is incomplete; without the post-check the trace cannot prove
  the flush actually emptied the targeted DB.
- ❌ **ModifyInstanceSpec memory reduction without usage surface** — shrinking
  Memory below `RedisUsage` triggers `maxmemory-policy` eviction and silently
  destroys cached data; the agent MUST show current Size + RedisUsage before any
  reduction.
- ❌ **ResetPassword on `default` account without the no-recovery warning** —
  there is no admin path to recover the `default` password; if the user forgets
  the new password, the instance must be reset from the API and ALL cached data
  is lost. The agent MUST surface this and capture acknowledgment.
- ❌ **BackupDownload to insecure path** — `/tmp`, `/var/tmp`, public COS bucket,
  world-readable local path, or any path not explicitly confirmed secure. The
  backup contains the full key set including cached sessions, tokens, and any PII.
- ❌ **Re-issuing FLUSHALL on retry** — ClearInstance is NOT idempotent at the
  data-plane level. A retry after `+OK` MUST be flagged "data already flushed"
  and the second FLUSHALL MUST NOT be sent. Otherwise the agent floods the Redis
  protocol channel with redundant FLUSHALL commands.
- ❌ **Treating `CleanInstance` on a non-isolated instance as a real failure** —
  the correct response is `OperationDenied.InstanceNotIsolated`, which is a
  terminal no-op. Treating it as transient and retrying creates an infinite loop.
- ❌ **Echoing the new password in the success message** — "ResetPassword succeeded,
  new password is: <value>" leaks the password through the agent's response
  channel. Mask to `***` and direct the user to the secure channel where they
  typed it.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Redis rollout: §1 Generator skeleton + §4 per-op variants (5 rules) + §5 Redis-specific anti-patterns (FLUSHALL data-plane audit blind spot, spec-change eviction, backup export security) |
| 1.1.0 | 2026-06-19 | Phase 5 Tier A flesh-out: added §2 Critic (full isolated-context template with 5-dimension scoring, 5-rule violations, credential/password hygiene checks, rubric §5 output schema), §3 Orchestrator (decision logic with Redis-specific ABORT triggers, max_iter=2, trace persistence path), expanded §4 per-op variants with `UpgradeType` rationale / DBSIZE post-check / no-recovery default-account warning / secure OutputFile validation, expanded §5 anti-patterns with 8 Redis-specific entries (FLUSHALL token, DBSIZE post-check, memory reduction without usage, default-account no-recovery, insecure backup path, retry FLUSHALL flooding, CleanInstance non-isolated no-op loop, password echo in success message). Cross-references to `rubric.md` §2 / §4 / §5 hardened throughout. |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [rubric.md](rubric.md) — the rubric instance these templates score against
  (Tier A: 8 sections; §2 thresholds, §4 five Redis-specific safety rules, §5 strict-JSON output schema)
- [SKILL.md](../SKILL.md) — the build-time safety gates, execution flows, error code reference
- [SKILL.md §Quality Gate (GCL)](../SKILL.md#quality-gate-gcl) — per-skill GCL header table
  (GCL applicability = required, `max_iterations = 2`)
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (storage pilot)
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (compute pilot)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (database pilot)
