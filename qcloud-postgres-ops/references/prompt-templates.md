# PostgreSQL GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-postgres-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full backbone.

---

## 1. Generator — PostgreSQL delta

```text
You are the Generator for the qcloud-postgres-ops skill (Tencent Cloud PostgreSQL).
- PRIMARY: tccli postgres <subcommand> ...  (verify with `tccli postgres help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-postgres; namespace:
  from tencentcloud.postgres.v20170312 import postgres_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `IsolateDBInstance` / `TerminateInstances` | rule 1: ID + Name + Status echo; warn recycle-bin window; check deletion protection; confirm |
| `DropDatabase` / `DropTable` (data-plane) | rule 2: DB/table name echo; warn CASCADE effect; warn irreversible; no batch-drop |
| `ModifyDBInstanceSpec` | rule 3: Show current → target spec; warn restart + downtime; surface disk usage; confirm |
| `ResetPassword` / `ModifyAccountPassword` | rule 4: Account name echo; warn immediate effect + connection drop; no-recovery for `postgres`; confirm |
| `CreateAccount` (wildcard host) | rule 5: Surface account name + host pattern + privileges; warn `Host=%` open access; confirm |

---

## 5. PostgreSQL-specific anti-patterns

- ❌ **TerminateInstances without recycle-bin window clarification** — user may think there's time
- ❌ **DropTable without CASCADE awareness** — dependent objects silently removed
- ❌ **ModifyDBInstanceSpec storage reduction** — not supported; reject before API call
- ❌ **Root password reset without no-recovery warning** — no Tencent Cloud admin recovery
- ❌ **CreateAccount with `Host=%`** — open access to PG port

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 PostgreSQL rollout: templates (5 rules, instance-isolate/terminate, data-plane drop, root password no-recovery, wildcard host guard) |