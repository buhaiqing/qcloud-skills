# Redis Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-redis-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. Redis-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DestroyInstances` / `IsolateInstance` (any) | **Instance ID + Name + Status echo; warn that isolation moves instance to recycle bin (short retention period, varies by billing mode); for `DestroyInstances`: warn irreversible — all data including backups are permanently removed; require explicit confirmation with instance name** | Redis has a recycle bin for isolated instances, but the window is very short (3-7 days). Destroy is immediate and irreversible. Most common incident: "I isolated the instance 'for testing' and forgot about it — all my session data is gone" |
| 2 | `ClearInstance` (`FlushInstance` — FLUSHALL / FLUSHDB) | **Instance ID + Name + database index (0-255) echoed; warn that FLUSHALL removes ALL keys in ALL databases (or FLUSHDB removes all keys in the specified DB); this is a Redis wire-protocol operation that is NOT logged in Tencent Cloud API audit; require literal "CONFIRM FLUSH <instance_id>"** | Redis `FLUSHALL` is the most dangerous data-plane command because (a) it has no soft-delete window, (b) it is invisible to Tencent Cloud API audit logs since it goes through the Redis protocol, not the Tencent Cloud API. The most common incident: "I ran FLUSHALL on the prod Redis thinking it was my dev shell session" |
| 3 | `ModifyInstanceSpec` / `UpgradeInstance` (spec change, `MemSize`, `ReplicasNum`, `NodeNum`, `ShardNum`) | **Show current spec → target spec; warn that spec changes trigger a failover (5-30s downtime); for `MemSize` reduction: warn that Redis data must fit in new memory or keys will be evicted; surface current `MemSize` and `RedisUsage` from `DescribeInstanceMonitorBigKey` / `DescribeInstanceParamRecords`; require re-confirmation for any reduction** | Redis spec changes cause a primary-replica failover. Memory reduction is especially dangerous: Redis evicts keys based on the `maxmemory-policy` setting, which can remove important cached data without warning |
| 4 | `ResetPassword` (any, especially `default` account) | **Account name echoed; warn that the password change takes immediate effect and all existing connections are closed; for the `default` account: warn that there is no "forgot password" recovery path; require confirmation with account name** | Redis password change is immediate: all clients lose connectivity and must reconnect with the new password. The `default` account has no admin recovery path |
| 5 | `BackupDownload` / export (sensitive data) | **Backup file size + time range echoed; warn that the backup contains all cached data including any stored sessions, tokens, or sensitive payloads; require the user to confirm that the download destination is secure (not a public bucket / unencrypted channel); check that `OutputFile` path is not world-readable** | Redis backups contain ALL data in memory — including session tokens, API keys, and user PII that may be cached. The most common incident: "I downloaded the Redis backup to troubleshoot a cache issue, then the intern shared it on Slack for debugging" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Redis rollout: rubric (5 rules: instance-destroy/isolate, FLUSHALL data-plane, spec-change failover + eviction, password change no-recovery, backup sensitive-data export) |