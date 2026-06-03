# Redis GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-redis-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full backbone.

---

## 1. Generator — Redis delta

```text
You are the Generator for the qcloud-redis-ops skill (Tencent Cloud Redis).
- PRIMARY: tccli redis <subcommand> ...  (verify with `tccli redis help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-redis; namespace:
  from tencentcloud.redis.v20180412 import redis_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DestroyInstances` / `IsolateInstance` | rule 1: ID + Name + Status echo; warn recycle-bin window; warn destroy irreversible; confirm |
| `ClearInstance` (FLUSHALL/FLUSHDB) | rule 2: Instance ID + DB index echo; warn FLUSHALL removes ALL keys; warn invisible to audit logs; literal confirm |
| `ModifyInstanceSpec` / `UpgradeInstance` | rule 3: Show current → target spec; warn failover + downtime; for reduction: warn eviction risk; surface usage; confirm |
| `ResetPassword` | rule 4: Account echo; warn immediate effect + connections closed; no-recovery for `default`; confirm |
| `BackupDownload` | rule 5: File size + time range echo; warn sensitive data content; check output path security; confirm |

---

## 5. Redis-specific anti-patterns

- ❌ **ClearInstance without FLUSHALL audit-log invisible warning** — invisible to CloudAudit
- ❌ **ModifyInstanceSpec memory reduction without usage check** — key eviction
- ❌ **ResetPassword without connection-drop warning** — all clients disconnected
- ❌ **BackupDownload to unsecure path** — sensitive cached data exposure

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Redis rollout: templates (5 rules, FLUSHALL data-plane audit blind spot, spec-change eviction, backup export security) |