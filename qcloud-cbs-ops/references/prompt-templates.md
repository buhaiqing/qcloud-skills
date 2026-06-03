# CBS GCL Prompt Templates

> Prompt skeletons for the **Generator (G)**, **Critic (C)**, and **Orchestrator (O)**
> of the `qcloud-cbs-ops` skill, instantiated from
> [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill).
>
> The G/C/O backbone is identical across all Phase 1 pilots (see
> [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full template).
> This file documents only the **CBS delta**: namespace, per-operation augmentation,
> and CBS-specific anti-patterns.

---

## 1. Generator — CBS delta

```text
You are the Generator for the qcloud-cbs-ops skill (Tencent Cloud CBS block storage).
- PRIMARY: tccli cbs <subcommand> ...  (verify with `tccli cbs help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-cbs; namespace:
  from tencentcloud.cbs.v20170312 import cbs_client, models
```

Variables: `user.disk_id`, `user.snapshot_id`, `user.target_size` (GB), `user.project_id`;
outputs: `$.Response.DiskId`, `$.Response.SnapshotId`, `$.Response.DiskSet[i].DiskSize`.

Pre-flight for `ResizeDisk`: reject if `target_size <= current_size` before calling API.
Pre-flight for `DetachDisks`: check CVM running state; flag filesystem unmount requirement.

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `TerminateDisks` (destroy) | rule 1: Disk ID + Name + Size + Status echo; warn irreversible; surface `DeleteWithInstance` flag; explicit confirm |
| `DetachDisks` | rule 2: Disk ID + attached CVM echo; warn running CVM data corruption risk; require unmount confirmation |
| `ResizeDisk` | rule 3: Show current → target; warn EXPAND ONLY; reject shrink before API call |
| `DeleteSnapshots` | rule 4: Snapshot ID + Size + CreatedTime echo; warn last-snapshot chain invalidation; require confirm; `--DryRun` for batch |
| `ModifyDiskAttributes` (esp. `DeleteWithInstance` toggle) | rule 5: Echo new attributes; warn `DeleteWithInstance` auto-delete risk; require confirmation per change |

---

## 5. CBS-specific anti-patterns

- ❌ **ResizeDisk shrink submitted** — CBS does not support shrinking; API silently rejects
- ❌ **DetachDisks without unmount warning** — data corruption on running CVM
- ❌ **DeleteSnapshots without snapshot-chain awareness** — oldest snapshot is baseline for incremental chain
- ❌ **DeleteWithInstance toggle turned ON without warning** — disk auto-destroys on CVM termination

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CBS rollout: templates (5 rules, resize-shrink rejection, detach-without-unmount guard, DeleteWithInstance toggle warning) |