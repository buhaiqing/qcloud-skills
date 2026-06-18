# PostgreSQL GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-postgres-ops` |
| CLI | `tccli postgres help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (PostgreSQL).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (PostgreSQL — 5 rules). Do not duplicate gate text here.

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


- ❌ **Logging passwords** — extending the AGENTS.md list with the PG-specific ban on
  letting `{{user.password}}` / `{{user.new_password}}` / `TENCENTCLOUD_SECRET_KEY`
  appear unmasked anywhere in command, response, or trace.
- ❌ **Silent `Host=%`** — PG-specific: `CreateAccount` with an undiscussed `%` Host
  is the same family of bug as a credential leak; the Generator must surface the
  default and the Critic must catch it. The PG equivalent of `host all all 0.0.0.0/0`
  in `pg_hba.conf` is a routine source of misconfiguration.
- ❌ **`DropDB` / `DROP DATABASE` without backup check** — PG-specific (extending the
  Out-of-scope guard): even when a user explicitly asks to drop a database, the
  Generator must surface `DescribeDBBackups` showing the most recent successful
  backup timestamp and confirm the user has accepted that standard PG has no UNDROP.
  Without this, "drop the test database" can become "drop the prod database with the
  last 90 days of writes".
- ❌ **`REVOKE ALL` without connection draining** — PG-specific: `ModifyAccountPrivileges`
  with `REVOKE ALL` is **silent** on running connections. PG returns "permission
  denied" lazily on the next statement, not at REVOKE time. The Generator must
  surface the BEFORE/AFTER diff and warn that running applications will fail mid-flight;
  the application team must drain connections (rolling restart or `pg_terminate_backend`)
  before the revoke — or revoke on a maintenance window.
- ❌ **`IsolateDBInstance` without retention-window warning** — PG-specific: the
  recycle-bin window is **fixed at 7 days** and **not** user-configurable (unlike
  CVM's pre-paid / post-paid distinction which carries 1 day vs 7 days — PG is
  always 7 days). The Generator must surface the literal "7-day recycle-bin window,
  no extension" before the call.
- ❌ **Storage shrink via `UpgradeDBInstance`** — PG-specific: CBS does not support
  storage reduction. The Generator must reject the call **before** the API round-trip
  with a clear "CBS does not support shrink; please choose `Storage >= current`";
  do not let the API return `InvalidParameterValue.IllegalStorageReduction` and
  confuse the user.
- ❌ **Direct system-table queries via `psql`** — PG-specific: `pg_database`,
  `pg_roles`, `pg_class` reads are data-plane execution and fall under the
  Out-of-scope guard in §4. Use the API (`DescribeAccounts`, `DescribeDBBackups`)
  for the audit surface; reserve `psql` for user-initiated data-plane operations
  that explicitly acknowledge the GCL boundary.
- ❌ **`ResetAccountPassword` for `postgres` superuser without no-recovery warning** —
  PG-specific: the Tencent Cloud console has no "forgot PG password" recovery path.
  The Generator must surface the literal "no admin recovery; rebuild from backup if
  lost" warning before the call; the Critic must catch any trace that omitted it.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 PostgreSQL rollout: templates (5 rules, instance-isolate/terminate, data-plane drop, root password no-recovery, wildcard host guard) |
| 1.1.0 | 2026-06-19 | Tier A conformance flesh-out: added full §1 Generator (system-table audit via API, SKU matrix, account Host wildcard audit, password masking, storage-shrink pre-flight rejection), §2 Critic (5-dimension scoring + PG silent-failure patterns: lazy REVOKE ALL, recycle-bin window, no-recovery, storage shrink, silent Host=%), §3 Orchestrator (decision logic with 6 PG-specific ABORT triggers + failure_pattern extraction for Reflexion), §5 Anti-patterns extended with DropDB without backup check, REVOKE ALL without connection draining, IsolateDBInstance retention warning, storage shrink, direct system-table psql, postgres-superuser no-recovery. §4 per-operation variants expanded with retention-window warning, OVERWRITES-not-PITR semantics, Host=% misconfiguration analogy, lazy privilege error semantics. §7 See also added |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill) — rubric backbone (5 dimensions)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-postgres-ops` is `required`, `max_iter=2`
- [AGENTS.md §14 Reflexion Integration](../../AGENTS.md#14-reflexion-integration-lightweight-reflexion) — failure_pattern extraction
- [`rubric.md`](rubric.md) — the rubric instance these templates score against (PG-specific rules 1-5)
- [SKILL.md](../SKILL.md) — the build-time safety gates, state-transition table, and pre-flight tables
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (CDB pilot; MySQL — closest RDBMS analog)
- [`qcloud-cdb-ops/references/rubric.md`](../cdb-ops/references/rubric.md) — sibling rubric for the MySQL-compatible PG analog (5-dimension backbone shared; CDB §4 rules mirror PG §4 with MySQL-specific operations)
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (CVM pilot; compute, no data plane)
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — Tier A canonical templates (object storage)
- [`docs/failure-patterns.md`](../../docs/failure-patterns.md) — Reflexion memory for cross-session failure-pattern learning (PG patterns extracted here on Critic suggestions)
