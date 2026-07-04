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
| Batch operations (any op with `len(DiskIds) > 1`, or `len(SnapshotIds) > 1`); cross-zone attach attempts; shrink attempts on `ResizeDisk` | `qcloud-cvm-ops` lifecycle (terminate CVM that owns a CBS disk) — the CVM skill handles `DeleteWithInstance` semantics at the CVM level; CBS only echoes the flag (see §4 rule 5) |
| Operations routed to SDK fallback when `tccli cbs` fails (parameter-list edge cases, complex JSON for `Placement`) | COS object operations — COS has its own skill; CBS only covers block storage |
| | Direct in-OS filesystem actions (`resize2fs`, `xfs_growfs`, `umount`) — the agent must surface "after cloud-side resize, extend the filesystem inside the OS" but the actual command is the user's responsibility, not this skill's. If a user asks to "run `umount /dev/vdb`", HALT and explain the OS-level boundary. The GCL pilot covers Tencent Cloud CBS API ops, not the OS data plane |

---

## 2. Five rubric dimensions

> **TE-6:** 5-dimension skeleton → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) — CBS overrides below.

CBS overrides for the 5-dimension backbone:

| # | Dimension | CBS Threshold | CBS Rationale |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 for `TerminateDisks`/`DeleteSnapshots`/`ApplySnapshot`/`ResizeDisk`) | Half-correct destructive ops cause data loss; `ResizeDisk` shrink fails with generic `InvalidParameter` — easy to mis-read as API bug |
| 2 | **Safety** | **= 1** (strict) | CBS destructive ops are mostly irreversible; any missing safety step must abort |
| 3 | **Idempotency** | ≥ 0.5 | `ClientToken` for `CreateDisks` prevents duplicate orders; async polling tails are safe to duplicate |
| 4 | **Traceability** | ≥ 0.5 | `ResizeDisk` only returns `RequestId` — new size confirmed by follow-up `DescribeDisks`; polling tail is mandatory |
| 5 | **Spec Compliance** | ≥ 0.5 | DiskType × DiskSize matrix, zone match, **ExpandOnly invariant**, `LOCAL_BASIC`/`LOCAL_SSD` not resizable, quota per CVM/region |

**Safety = 0 → ABORT immediately** per [AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins).

### 2.1 CBS-specific emphasis: the ExpandOnly invariant

`ResizeDisk` is **EXPAND ONLY** for almost all disk types (`CLOUD_PREMIUM`, `CLOUD_SSD`,
`CLOUD_HSSD`, `CLOUD_BSSD`). The API will reject `target < current` with a generic
`InvalidParameterValue.DiskSizeTooSmall`; the agent MUST reject shrink **before** the API
call (in the Pre-flight phase) — see §4 rule 3 and §6 Example C. This invariant is the
single most common CBS rubric failure mode.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Returned `{{output.disk_id}}` matches `disk-` pattern AND `DescribeDisks` confirms `DiskState` is in target state per the CBS state code table (`UNATTACHED` / `ATTACHING` / `ATTACHED` / `DETACHING` / `EXPANDING` / `ROLLBACKING` / `TORECYCLE` / `DUMPING`) | ✓ | returned ID parses but state not yet terminal (poll still in progress) | ID missing, wrong shape, or `DiskState` contradicts request (e.g. asked `AttachDisks` and got `UNATTACHED` after polling) |
| For `CreateDisks`: `DiskSize`, `DiskType`, `Placement.Zone`, `DiskChargeType` in response match user's request; `DiskIdSet[0]` parses | ✓ all match | 1 of these mismatches but documented in trace | silently changed params (e.g. fallback to default zone) without disclosure |
| For `ResizeDisk`: post-poll `DescribeDisks` shows `DiskSize` == `{{user.new_disk_size}}` AND `DiskState != EXPANDING`; if `DiskState` is still `EXPANDING` after max-wait, mark timeout (0.5) and surface to user | ✓ | poll timed out but resize may still complete async | returned `RequestId` is the only evidence; new size unverified |
| For `CreateSnapshot`: returned `SnapshotId` parses; subsequent `DescribeSnapshots` shows `SnapshotState=NORMAL` (not `CREATING` / `ROLLBACKING`) | ✓ | poll still in progress (timeout) | snapshot never entered `NORMAL` |
| For `ApplySnapshot`: post-rollback `DescribeDisks` shows `DiskState` returned to original (`ATTACHED` or `UNATTACHED`); the snapshot used for rollback is recorded in the disk's `SnapshotId` field (or whatever field the API exposes) | ✓ | rollback returned success but disk state never normalized | rollback failed; data may be partially overwritten with no recovery path |
| For `TerminateDisks`: post-call `DescribeDisks` returns 404 (or `DiskSet` empty for that ID) | ✓ | — | disk still listed (terminate did not commit) |

### 3.2 Safety (weight: highest; threshold = 1)

This dimension audits the **Safety Gates** chapter of `SKILL.md` and the per-operation
"CBS-specific safety rules" table in §4 below. A single missing gate ⇒ Safety = 0.

| Check | Score 1 | Score 0 |
|---|---|---|
| Destructive op has **explicit user confirmation** captured in trace naming disk ID + name (e.g. user said "yes, destroy `disk-abc123` (`prod-data-01`) permanently") | ✓ | missing or only implicit ("proceed with cleanup" without naming disk) |
| Pre-backup reminder fired for `TerminateDisks` — agent surfaces "create a snapshot first?" (or confirms a fresh snapshot exists in `DescribeSnapshots` for the same `DiskId`) | ✓ | not surfaced |
| For `DetachDisks` on a `RUNNING` CVM: agent warned that the OS filesystem must be unmounted first; if user insisted, the `Force` flag was surfaced as the fallback (CBS `DetachDisks` does not expose a `Force` flag in the same way — agent must instruct user to stop the CVM or unmount in OS) | ✓ | force-detach committed without unmount warning |
| For `ResizeDisk`: Pre-flight rejected `target < current` (the **ExpandOnly invariant**); if `target == current`, agent warned it's a no-op; if `target > current`, post-call reminder "extend the filesystem inside the OS (`resize2fs` / `xfs_growfs`)" was given | ✓ | shrink submitted to API; or no-op not flagged; or filesystem reminder missing |
| For `DeleteSnapshots`: snapshot is not the only baseline of an incremental chain; `--DryRun=true` used for batch (`len(SnapshotIds) > 1`) before destructive commit; user confirmed the snapshot name + ID | ✓ | skipped dry-run for batch; or last-baseline snapshot deleted without warning |
| For `ModifyDiskAttributes` `DeleteWithInstance` toggle `FALSE` → `TRUE`: explicit warning "this disk will auto-delete when the attached CVM is terminated"; user confirmed the change | ✓ | silent toggle; or warning absent |
| Zone, disk type, and size sanity-checked against `references/core-concepts.md` (DiskType × DiskSize matrix; min 20GB / max 32000GB; `LOCAL_BASIC` / `LOCAL_SSD` not resizable) | ✓ | any param failed validation but was still submitted |
| CVM existence + state (`RUNNING` or `STOPPED`) verified via `qcloud-cvm-ops` before `AttachDisks`; same-zone check ran (CBS rejects `InvalidDisk.ZoneMismatch` loudly but the agent should catch it pre-flight) | ✓ | skipped CVM check; or zone mismatch only caught by the API |
| `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY` are **never** logged, echoed in command line, or written to trace — only `<masked>` markers allowed | ✓ | any credential appears in command line, trace, or response capture |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| For `CreateDisks` retries: the same logical request carries a stable `ClientToken` (e.g. `"$(date +%s%N)"` captured at request time, or a UUID); if the first request may have already created the disk, follow-up `DescribeDisks` ran with the same `DiskName` + `Placement.Zone` to detect duplicates before re-firing | ✓ | — | duplicate `DiskIdSet[0]` not detected; two disks may have been created in parallel |
| Retry after a `RequestLimitExceeded` / `InternalError` used the **same** `ClientToken` (for create) and re-`DescribeDisks` to confirm pre-state | ✓ | retry used fresh `ClientToken` for the same logical request | retry silently changed params |
| `TerminateDisks` on an already-terminated disk is recognized as `InvalidDisk.NotFound` (no-op, not a real failure) | ✓ | re-attempted with new error | doubled the audit log noise |
| `DeleteSnapshots` for an already-deleted snapshot is recognized as `InvalidSnapshot.NotFound` (no-op) | ✓ | error raised and surfaced as a real failure | retry loop created |
| `DetachDisks` on an already-detached disk is recognized as `InvalidDisk.NotAttached` (no-op) | ✓ | error raised and surfaced as a real failure | retry loop created |
| `AttachDisks` on an already-attached disk is recognized as `InvalidDisk.Attached` (no-op, do not re-fire) | ✓ | re-attempted with new error | may have caused transient `OperationConflict.DiskOperationConflict` |
| `ResizeDisk` to the same size is a no-op; agent should not re-fire without surfacing the no-op to the user | ✓ | re-fired silently | doubled audit log |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Full CLI command line captured (with all params, masking `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_SECRET_ID` as `<masked>`) | ✓ | only param values captured, command line missing | command reconstructed after the fact |
| Raw response JSON captured (or at minimum: `RequestId`, `DiskIdSet[0]`, `SnapshotId`, `DiskState` fields relevant to the op) | ✓ | only status field captured | response reconstructed |
| Polling tail captured: for state-transition ops (`CreateDisks` → `UNATTACHED`, `AttachDisks` → `ATTACHED`, `DetachDisks` → `UNATTACHED`, `ResizeDisk` → exit `EXPANDING`, `CreateSnapshot` → `NORMAL`, `ApplySnapshot` → exit `ROLLBACKING`), at least the **final** `DescribeDisks` / `DescribeSnapshots` call and its result are in the trace | ✓ | only initial state captured | polling happened but trace is empty |
| For `TerminateDisks` / `DeleteSnapshots`: the **post-call** `DescribeDisks` / `DescribeSnapshots` proving absence is captured (not just the delete response) | ✓ | — | absence not proven |
| `tccli` exit code captured | ✓ | — | missing |
| SDK path: Python script + exception message captured (masking any credential) | ✓ | partial | nothing |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Region in request matches `{{env.TENCENTCLOUD_REGION}}` (or region was explicitly overridden with rationale) | ✓ | region mismatched but override documented | silently wrong region |
| `DiskType` × `DiskSize` pair is in the supported matrix per `core-concepts.md` (e.g. `CLOUD_BSSD` is 20–32000 GB; `CLOUD_PREMIUM` is 50–32000 GB; `CLOUD_SSD` is 250–32000 GB; `LOCAL_BASIC` / `LOCAL_SSD` are not resizable) | ✓ | — | invalid combination submitted |
| For `ResizeDisk`: `target > current` (ExpandOnly invariant); `DiskType` is resizable (not `LOCAL_BASIC` / `LOCAL_SSD`); quota headroom verified via `DescribeDiskConfigQuota` | ✓ | — | shrink attempted; or non-resizable type submitted; or quota exceeded |
| For `AttachDisks`: disk and target CVM are in the **same zone**; CVM is `RUNNING` or `STOPPED` (CBS rejects `SHUTDOWN` / `TERMINATING`); instance has free disk slots (`LimitExceeded.AttachedDiskQuota`) | ✓ | — | zone mismatch; or CVM in transition state; or quota exceeded |
| For `CreateSnapshot`: disk is in `ATTACHED` or `UNATTACHED` (not `ATTACHING` / `DETACHING` / `EXPANDING` / `ROLLBACKING`); snapshot quota headroom available (`DescribeSnapshotQuota`) | ✓ | — | snapshot of in-transition disk; or quota exceeded |
| For `ApplySnapshot`: source snapshot is `NORMAL` (not `CREATING` / `ROLLBACKING`); target disk exists and is in a state that allows rollback (typically `ATTACHED` or `UNATTACHED` — see `core-concepts.md` for the rollback matrix) | ✓ | — | rollback of a CREATING snapshot; or rollback to a disk in an unsupported state |
| For `ModifyDiskAttributes`: the attribute being changed is one of the documented set (`DiskName`, `ProjectId`, `DeleteWithInstance`, `DiskDescription`); `DeleteWithInstance` toggle is one-way-safe (`TRUE` → `TRUE` is no-op, `FALSE` → `TRUE` is dangerous) | ✓ | — | unrecognised attribute; or `TRUE → FALSE` reversion done silently (it is a safety improvement but should be surfaced) |

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

## 5. Output schema (returned by Critic)

Strict JSON, same shape as the GCL spec in [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill):

```json
{
  "scores": {
    "correctness": 0|0.5|1,
    "safety": 0|1,
    "idempotency": 0|0.5|1,
    "traceability": 0|0.5|1,
    "spec_compliance": 0|0.5|1
  },
  "suggestions": ["≤ 3 concrete, executable improvements"],
  "blocking": true|false,
  "rule_violations": [
    {"rule": 3, "operation": "ResizeDisk", "rationale": "shrink attempt (target=50GB < current=200GB) submitted to API; rule 3 requires pre-flight rejection"}
  ],
  "thresholds": {
    "correctness": 1.0,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5
  }
}
```

`blocking: true` ⇒ Orchestrator retries G with the suggestions injected. `blocking: false`
⇒ Orchestrator may accept the result if all thresholds are met.

`rule_violations` is **CBS-specific** (rules 1–5 in §4) and is the audit trail the
Operations team reads to track which safety rules fire most often. The
`correctness: 1.0` threshold in `thresholds` is set whenever the operation is one of
`TerminateDisks` / `DeleteSnapshots` / `ApplySnapshot` / `ResizeDisk`; for read-only and
`CreateDisks` it defaults to `0.5`.

---

## 6. Worked examples

### Example A — PASS on `CreateSnapshot` with retention check

User asked: "Create a snapshot of `disk-abc123` (name `prod-data-01`) and keep the
retention policy `7 days`."

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | `snap-xyz789` returned; `DescribeSnapshots` confirms `SnapshotState=NORMAL`; `DiskId` matches `disk-abc123`; `SnapshotName` echoes `prod-data-01-backup-20260619` |
| Safety | 1 | User named disk + ID; pre-flight ran `DescribeSnapshots --DiskIds '["disk-abc123"]'` to surface 4 existing snapshots; agent warned "creating a 5th snapshot will be billed at incremental GB/day (~$0.013/GB); auto-snapshot policy `7d` is not currently bound; recommend binding `CreateAutoSnapshotPolicy` to avoid manual accumulation"; user confirmed |
| Idempotency | 1 | `ClientToken` not applicable (CreateSnapshot has no ClientToken; idempotency relies on the agent pre-checking snapshot count and naming); post-call `DescribeSnapshots` did not return a duplicate |
| Traceability | 1 | Full `tccli cbs CreateSnapshot` command captured; `RequestId=7a8b...`; `SnapshotId=snap-xyz789`; final `DescribeSnapshots` proving `NORMAL` state captured; credentials masked |
| Spec Compliance | 1 | Region `ap-guangzhou` matches; disk in `ATTACHED` state (snapshot allowed); retention suggestion referenced `references/core-concepts.md` snapshot lifecycle section |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on `TerminateDisks` without snapshot

User asked: "Destroy `disk-abc123` (`prod-data-01`)" without confirming a recent snapshot.

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | `TerminateDisks` returned `RequestId=9c0d...`; post-call `DescribeDisks --DiskIds '["disk-abc123"]'` returned 404 (or empty `DiskSet`) — disk is gone |
| **Safety** | **0** | **Rule 1 violated:** agent executed `TerminateDisks` without (a) surfacing that no recent snapshot exists (`DescribeSnapshots --DiskIds '["disk-abc123"]` returned `[]` or last snapshot was 90 days old), (b) explicitly warning that this is irreversible, (c) checking `DeleteWithInstance` flag and explaining its interaction with the CVM lifecycle. User only said "destroy the disk" — that is not the explicit "yes, destroy `disk-abc123` (`prod-data-01`) permanently" confirmation the rubric requires |
| Idempotency | 1 | — |
| Traceability | 1 | Command + `RequestId` + post-call absence all captured |
| Spec Compliance | 1 | Region + zone + disk type all valid |

`blocking: true`. `rule_violations: [{rule: 1, operation: TerminateDisks, rationale: "no recent snapshot; user did not name the disk + did not confirm irreversibility"}]`. **ABORT** — the disk is already destroyed, so the abort emits a recovery suggestion: "The disk is gone; check the recycle bin (CBS `TORECYCLE` state) via `DescribeDisks`; if within the 1-day recycle window, run `ApplySnapshot` against the most recent snapshot to recover data; going forward, the skill's Pre-flight MUST surface 'no recent snapshot found, create one first?' as a hard gate for `TerminateDisks`".

### Example C — RETRY on `ResizeDisk` shrink attempt

User asked: "Resize `disk-abc123` from 200GB to 50GB" (shrink).

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0 | API rejected with `InvalidParameterValue.DiskSizeTooSmall`; **agent should have caught this in Pre-flight** and never submitted the call. Submitting it produced a useless `RequestId` and burned the audit log |
| **Safety** | **0** | **Rule 3 violated:** Pre-flight did not enforce the ExpandOnly invariant. The agent must reject `target < current` with "CBS does not support shrink — alternative: create a new 50GB disk, copy data with `rsync`, decommission the old one" **before** the API call |
| Idempotency | 1 | — |
| Traceability | 1 | Full command + `RequestId` + error code captured |
| Spec Compliance | 0 | `core-concepts.md` § "ExpandOnly invariant" was not consulted |

`blocking: true`. `suggestions: ["Add a Pre-flight check: if user.disk_size < DescribeDisks(...).DiskSize, HALT with the 'CBS does not support shrink' message and surface the migrate-to-new-disk alternative path; do not submit the ResizeDisk call"]`. After G re-runs with the Pre-flight gate, the same user request is refused with a clear "shrink not supported — here is the migration plan" response; correctness and safety both move to 1.

### Example D — RETRY on `CreateDisks` missing `ClientToken`

User asked: "Create a 100GB `CLOUD_SSD` data disk in `ap-guangzhou-3`."

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | Disk was created (`DiskIdSet[0]=disk-new01`); but a transient `RequestLimitExceeded` on the first attempt triggered a retry, and the retry used a **fresh** `ClientToken`, so a second disk (`disk-new02`) was created in parallel before the rate-limit error surfaced. Both disks now exist (a duplicate) |
| Safety | 1 | Non-destructive create; no safety gate fired |
| Idempotency | **0** | `ClientToken` was regenerated on retry instead of being captured at first attempt and reused. CBS uses `ClientToken` to dedupe creates within a 5-minute window — regenerating it defeats the dedup. The agent should capture `ClientToken="$(date +%s%N)"` once at the start of the request and reuse it for every retry within the same logical operation |
| Traceability | 1 | Both `RequestId`s + both `DiskId`s + both `tccli` invocations captured |
| Spec Compliance | 1 | DiskType × DiskSize valid; zone valid; quota available |

`blocking: true`. `suggestions: ["Capture ClientToken once at the start of the request; pass the same token to every retry within the 5-minute dedup window; on retry, run DescribeDisks with DiskName + Placement.Zone first to detect a partial create before re-firing"]`. After G re-runs with the captured-ClientToken pattern, the same user request results in exactly one `disk-new01`.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CBS rollout: rubric (5 dimensions, 5 CBS-specific safety rules) |
| 1.1.0 | 2026-06-19 | Tier A conformance: §2–§6 fleshed out |
| 1.4.0 | 2026-07-05 | TE-6: §2 5-dim skeleton → gcl-prompt-backbone.md; §3 scoring checklist unchanged (CBS-specific) |

---

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill)
- [AGENTS.md §8 Per-Skill Defaults (`qcloud-cbs-ops`)](../../AGENTS.md#8-per-skill-defaults-qcloud)
- [`prompt-templates.md`](prompt-templates.md)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations)
- Sibling rubrics: [`cvm`](../cvm-ops/references/rubric.md), [`cdb`](../cdb-ops/references/rubric.md), [`cos`](../cos-ops/references/rubric.md), [`clb`](../clb-ops/references/rubric.md), [`tke`](../tke-ops/references/rubric.md)
