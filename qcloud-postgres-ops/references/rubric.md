# PostgreSQL Quality-Gate Rubric (GCL)

> Runtime scoring rubric for **Generator-Critic-Loop (GCL)** of `qcloud-postgres-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the 5-dimension backbone.

---

## 4. PostgreSQL-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `IsolateDBInstance` / `TerminateInstances` (any) | **Instance ID + Name + Status echo; warn isolation moves to recycle bin (7-day retention); for `TerminateInstances`: warn permanent destruction; check deletion protection via `IsolateDBInstance` pre-flight; require explicit confirmation with instance name** | PostgreSQL has a recycle bin for isolated instances, but the window is short. Terminate is irreversible. The most common pattern: "I isolated the instance and forgot to un-isolate it" |
| 2 | `DropDatabase` / `DropTable` (PostgreSQL wire protocol — data plane boundary) | **Database/table name echoed; warn that ALL data in the database/table will be permanently removed; require explicit confirmation; for drop table: warn that dependent views/triggers/indexes are also removed (CASCADE); do NOT batch-drop** | PostgreSQL data-plane operations are irreversible. `DROP TABLE ... CASCADE` can remove more than the user expects. The most common incident: "I dropped a table in the dev database, but it was also referenced by the prod schema" |
| 3 | `ModifyDBInstanceSpec` (upgrade/downgrade: `Memory`, `Storage`) | **Show current spec → target spec; warn that spec changes trigger a restart (30-60s downtime); for storage reduction: warn that PostgreSQL disk cannot be shrunk (CBS attached); surface current disk usage; require explicit confirmation** | PostgreSQL spec changes cause a failover. Storage reduction is not supported (CBS attached). The most common PostgreSQL incident: "I downgraded storage to save costs and the database ran out of disk" |
| 4 | `ResetPassword` / `ModifyAccountPassword` (any account, especially `postgres` / root) | **Account name echoed; warn that the password change takes immediate effect; all active connections using the old password will be dropped; for the `postgres` superuser: warn that there is no Tencent Cloud admin recovery path; require confirmation with account name** | PostgreSQL root password is the superuser. There is no "forgot password" recovery. The most common pattern: user changes the password and forgets it — the instance must be rebuilt |
| 5 | `CreateAccount` (especially with `Host=*` / `Host=%`) | **Surface the account name, host pattern, and privileges; warn if `Host` is `%` or `*` — the account can connect from any IP that can reach the PG port; require explicit confirmation for wildcard host; warn that privilege escalation (superuser + wildcard host) is equivalent to open access** | PostgreSQL `Host=%` is the same class of risk as CDB's `ModifyAccountPrivileges` or COS's `PutBucketACL public-read`. A single wildcard host opens the database to brute-force attack from any network that can reach the PG endpoint |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 PostgreSQL rollout: rubric (5 rules: instance-isolate/terminate, data-plane drop guard, spec-change restart, root password no-recovery, wildcard host account) |