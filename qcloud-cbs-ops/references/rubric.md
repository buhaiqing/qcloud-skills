# CBS Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-cbs-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-cbs-ops` → **required**, `max_iterations = 2`).
>
> Sibling rubrics: [`qcloud-cvm-ops`](../cvm-ops/references/rubric.md), [`qcloud-cdb-ops`](../cdb-ops/references/rubric.md),
> [`qcloud-cos-ops`](../cos-ops/references/rubric.md), [`qcloud-clb-ops`](../clb-ops/references/rubric.md),
> [`qcloud-tke-ops`](../tke-ops/references/rubric.md). The 5-dimension backbone is identical; only §4 differs.
> CBS adds: **disk resize is one-directional (extend only)**, **detach without unmount = data
> corruption**, **snapshot deletion = last recovery line lost**.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| CBS mutation operations: `CreateDisks`, `TerminateDisks`, `AttachDisks`, `DetachDisks`, `ResizeDisk`, `CreateSnapshot`, `DeleteSnapshots`, `ModifyDiskAttributes`, `RenewDisk`, `ApplySnapshot` | Pure read (`DescribeDisks`, `DescribeDiskConfigQuota`, `DescribeSnapshots`) — optional loop |

---

## 4. CBS-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `TerminateDisks` (destroy) | **Disk ID + Name + Size + Status echo; warn that disk destroy is irreversible (snapshot recovery is the only path); surface whether `DeleteWithInstance` is set (automatic deletion on CVM terminate); require explicit confirmation "yes, destroy disk `disk-xxx` (name) permanently"** | Disk destroy = instant data loss. If `DeleteWithInstance` is set and the user doesn't know, the disk may auto-delete when the CVM is terminated — destroying both. The most common CBS support ticket: "I wanted to detach the disk but it was destroyed because of DeleteWithInstance" |
| 2 | `DetachDisks` (force detach) | **Disk ID + attached CVM ID + status echo; warn that detaching a disk attached to a running CVM without `--unmount` flag may cause data corruption; require the user to confirm filesystem is unmounted first (or surface the `Force` flag as the fallback)** | CBS `DetachDisks` with a running CVM skips filesystem flush. The most common CBS incident: "I detached the disk to replace it but lost the last 5 minutes of writes" |
| 3 | `ResizeDisk` (any) | **Show current size → target size; warn that CBS resize is EXPAND ONLY (cannot shrink except by creating a new smaller disk and migrating data); reject if `target < current` with "CBS does not support shrink" (do not submit the API call)** | The CBS API silently rejects a shrink but the user does not get a clear error — the `RequestId` says "invalid parameter" and the user thinks the disk is bugged. The pre-flight rule catches this before the API call |
| 4 | `DeleteSnapshots` (any) | **Snapshot ID + Name + Size + CreatedTime + any dependent `ApplySnapshot` references echoed; warn that deleting the last snapshot removes the ability to recover from catastrophic data loss; require confirmation "yes, delete snapshot `snap-xxx` (name)"; for batch, require `--DryRun` first** | Snapshots are the last recovery line. Deleting them is low-cost (CBS snapshot billing is incremental) but high-impact (recovery path lost). The most common pattern: user deletes "old snapshots" to save costs but the oldest snapshot is the baseline for the incremental chain — deleting it invalidates all newer ones |
| 5 | `ModifyDiskAttributes` (changing `DiskName`, `ProjectId`, or `DeleteWithInstance`) | **Echo new attributes BEFORE the call; for `DeleteWithInstance` toggle from `FALSE` → `TRUE`: warn that the disk will auto-delete when the attached CVM is terminated; for `ProjectId` change: warn that billing/cost allocation shifts; require confirmation for each change** | `DeleteWithInstance` toggle is the most dangerous: user enables it thinking "clean up on decommission" but forgets that any maintenance CVM termination will also destroy the disk. |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CBS rollout: rubric (5 dimensions, 5 CBS-specific safety rules incl. disk destroy irreversibility, detach-without-unmount data corruption, resize-shrink rejection, snapshot-chain deletion, DeleteWithInstance toggle) |

## 8. See also

- [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill), [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud)
- [`prompt-templates.md`](prompt-templates.md)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations)
- Sibling rubrics: [`cvm`](../cvm-ops/references/rubric.md), [`cdb`](../cdb-ops/references/rubric.md), [`cos`](../cos-ops/references/rubric.md), [`clb`](../clb-ops/references/rubric.md), [`tke`](../tke-ops/references/rubric.md)