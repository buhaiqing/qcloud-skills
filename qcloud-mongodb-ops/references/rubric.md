# MongoDB Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-mongodb-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the 5-dimension backbone.

---

## 4. MongoDB-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `IsolateDBInstance` / `DestroyDBInstance` (any) | **Instance ID + Name + Status echo; warn that isolation moves the instance to recycle bin (7-day retention for pay-as-you-go, immediate for prepaid expired); for `DestroyDBInstance`: warn irreversible — the instance and all data are destroyed permanently; check deletion protection status (`SetDBInstanceDeletionProtection`); require explicit confirmation with instance name** | MongoDB has a recycle bin (IsolateDBInstance) but the window is short (7 days). The most common MongoDB support ticket: "I isolated the instance to test but forgot to un-isolate it within the window, and it was destroyed permanently" |
| 2 | `DropDatabase` / `DropCollection` (MongoDB wire protocol / `tccli mongodb` API equivalent) | **Database/collection name echoed; warn that ALL documents, indexes, and user-defined roles for that database/collection will be permanently removed; require explicit confirmation; do NOT batch-drop — each database must be confirmed separately** | Data-plane operations in MongoDB are irreversible at the database level. MongoDB has no "recycle bin" for collections unlike CDB's IsolateDBInstance. The most common pattern: user runs `db.dropDatabase()` in the wrong shell session and loses the prod database |
| 3 | `ModifyDBInstanceSpec` (upgrade/downgrade: `NodeNum`, `Memory`, `Volume`) | **Show current spec → target spec; warn that spec changes trigger a restart (30-120s downtime); for downgrade (`Memory` or `Volume` reduction): warn that MongoDB data must fit in the new spec; surface current `RealInstanceUsage` (disk usage) and `MemoryUsage` from `DescribeDBInstanceNodeProperty`; require explicit confirmation** | Spec changes in MongoDB cause a primary-standby switchover (downtime). Downgrading memory below peak usage causes OOM kills. The most common MongoDB incident: "I downgraded the instance to save costs, then MongoDB started OOM-killing connections because the working set exceeded memory" |
| 4 | `ModifyAccountPassword` (any account) | **Account name echoed; warn that the password change takes immediate effect; all active connections using the old password will be closed; for the root/mongouser account: warn that there is no "forgot password" recovery path — the account is the Tencent Cloud MongoDB admin; require confirmation with account name** | MongoDB root password reset is irreversible: once changed, the old password is gone forever and there is no Tencent Cloud admin portal to recover it. The most common pattern: user changes the root password "temporarily" then loses the new password in Slack |
| 5 | `ModifySecurityGroup` / `ModifyNetworkAccess` (security group or VPC network change) | **For security group change: show current security group ID(s) → target; warn that the wrong security group can lock out all client connections; surface current network ACL status; require explicit confirmation. For network access: warn that changing the VPC will change the instance's endpoint IP — DNS-connected applications will break** | Security group misconfiguration is the #1 MongoDB connectivity issue: "I can't connect" tickets are 90% SG-related. Changing the VPC is even worse — the endpoint IP changes and the user must update all application connection strings |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 MongoDB rollout: rubric (5 rules: instance-isolate/destroy, database/collection drop, spec-change restart + OOM risk, password change without recovery, security group / VPC misconfiguration) |