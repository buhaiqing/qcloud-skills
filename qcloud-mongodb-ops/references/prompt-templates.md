# MongoDB GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-mongodb-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full backbone.

---

## 1. Generator — MongoDB delta

```text
You are the Generator for the qcloud-mongodb-ops skill (Tencent Cloud MongoDB).
- PRIMARY: tccli mongodb <subcommand> ...  (verify with `tccli mongodb help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-mongodb; namespace:
  from tencentcloud.mongodb.v20190725 import mongodb_client, models
```

Variables: `user.instance_id`, `user.database_name`, `user.collection_name`,
`user.new_password`, `user.security_group_ids`, `user.spec_memory`, `user.spec_volume`;
outputs: `$.Response.InstanceId`, `$.Response.TaskId`.

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `IsolateDBInstance` / `DestroyDBInstance` | rule 1: ID + Name + Status echo; warn recycle-bin window (7d); check deletion protection; confirm with name |
| `DropDatabase` / `DropCollection` (data-plane) | rule 2: DB/collection name echo; warn irreversible; no batch-drop; each DB confirmed separately |
| `ModifyDBInstanceSpec` | rule 3: Show current → target spec; warn restart + 30-120s downtime; for downgrade: surface `RealInstanceUsage` and `MemoryUsage`; confirm |
| `ModifyAccountPassword` | rule 4: Account name echo; warn immediate effect; surface no-recovery-path for root; confirm with account name |
| `ModifySecurityGroup` / network change | rule 5: Show current SG(s) → target; warn client connection lockout; for VPC change: warn endpoint IP changes |

---

## 5. MongoDB-specific anti-patterns

- ❌ **IsolateDBInstance without deletion protection check** — user may think it's safe but deletion protection prevents accidental isolation
- ❌ **DropDatabase in batch** — each database must be confirmed separately; no "DROP ALL"
- ❌ **ModifyDBInstanceSpec downgrade without memory check** — OOM risk
- ❌ **Root password change without fallback confirmation** — no recovery path
- ❌ **Security group change that locks out all clients** — surface current ACL before change

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 MongoDB rollout: templates (5 rules, instance-isolate/destroy, data-plane drop guard, spec-change OOM risk, root password no-recovery, SG lockout guard) |