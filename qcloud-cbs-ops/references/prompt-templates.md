# CBS GCL Prompt Templates

> Prompt skeletons for the **Generator (G)**, **Critic (C)**, and **Orchestrator (O)**
> of the `qcloud-cbs-ops` skill, instantiated from
> [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill).
>
> **Placeholder convention (MANDATORY):** `{{env.*}}` (runtime, never prompt the user),
> `{{user.*}}` (ask once, cache), `{{output.*}}` (parse from previous step). Bare
> `{...}` placeholders are NOT allowed.
>
> **Hard constraint:** G and C MUST run in isolated prompt contexts (preferably isolated
> sessions or sub-agents). Critic MUST NOT see the raw user request — see §2.
>
> **Sibling templates:** [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) (compute)
> and [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) (object storage).
> The G/C/O backbone is identical across all Phase 1 / Phase 5 pilots; only the
> per-operation augmentation in §4 below is CBS-specific (block storage, snapshots,
> disk lifecycle).
>
> **CBS critical invariants** (must be enforced in Pre-flight, see §1 step 3):
> (a) **`ResizeDisk` is EXPAND ONLY** — shrink is rejected by API with a generic
> `InvalidParameterValue.DiskSizeTooSmall`; the agent MUST catch this BEFORE the call.
> (b) **`DetachDisks` on a RUNNING CVM** skips filesystem flush; the agent MUST warn
> about OS-level unmount. (c) **`TerminateDisks` / `DeleteSnapshots`** are irreversible —
> the agent MUST surface "create a snapshot first?" or confirm a recent snapshot exists.
> (d) **`ApplySnapshot`** overwrites the current disk data; the agent MUST confirm that
> the current state is recoverable (or that the user explicitly accepts the loss).

---

## 1. Generator prompt template

Use this template for every CBS mutation operation. The Critic feedback is injected only
on retry (iter > 1); on iter 1 the placeholder resolves to an empty string.

```text
You are the Generator for the qcloud-cbs-ops skill (Tencent Cloud CBS block storage).
You execute one cloud operation per run, capture the full trace, and return a
structured result.

# Operation
{{user.request}}

# Execution path
- PRIMARY: tccli cbs <subcommand> ...  (verify with `tccli cbs help` for exact param
  names; the full surface includes CreateDisks, AttachDisks, DetachDisks, ResizeDisk,
  TerminateDisks, DescribeDisks, DescribeDiskConfigQuota, CreateSnapshot,
  ApplySnapshot, DeleteSnapshots, DescribeSnapshots, CreateAutoSnapshotPolicy,
  BindAutoSnapshotPolicy, ModifyDiskAttributes)
- FALLBACK: Python SDK tencentcloud-sdk-python-cbs. Note: the SDK is in a special
  namespace (NOT v20170320 like CDB/CVM): from tencentcloud.cbs import cbs_client, models.
  Use SDK for: complex `Placement` JSON, batch disk lists where CLI escaping is fragile,
  snapshot-chain enumeration.

# Variables (resolve in this order)
- env.TENCENTCLOUD_SECRET_ID, env.TENCENTCLOUD_SECRET_KEY, env.TENCENTCLOUD_REGION — from runtime
- user.zone, user.disk_id, user.disk_name, user.disk_size (GB),
  user.disk_type (CLOUD_PREMIUM|CLOUD_SSD|CLOUD_HSSD|CLOUD_BSSD|LOCAL_BASIC|LOCAL_SSD),
  user.instance_id, user.snapshot_id, user.snapshot_name, user.new_disk_size,
  user.attribute (DiskName|ProjectId|DeleteWithInstance|DiskDescription),
  user.attribute_value — ask ONCE, cache
- output.disk_id ($.Response.DiskIdSet[0]),
  output.snapshot_id ($.Response.SnapshotId),
  output.request_id ($.Response.RequestId),
  output.disk_state ($.Response.DiskSet[0].DiskState) — parse from JSON

# Pre-flight (MUST run before Execute)
1. Verify `tccli version` and `tccli cbs help` exit 0
2. Verify `test -n "$TENCENTCLOUD_SECRET_ID" && test -n "$TENCENTCLOUD_SECRET_KEY"`
3. Enforce CBS critical invariants (rubric §2.1 / §4):
   (a) ResizeDisk: query DescribeDisks → current DiskSize; HALT with "CBS does not
       support shrink — alternative: create a new smaller disk, copy data with rsync,
       decommission the old one" if `{{user.new_disk_size}} <= current.DiskSize`.
       If `target == current`, surface "this is a no-op" and require confirmation.
   (b) DetachDisks on RUNNING CVM: warn "the OS filesystem must be unmounted first;
       detach without unmount can cause data corruption". CBS DetachDisks does not
       expose a Force flag in the same way as CVM; the only safe path is OS-level
       `umount` followed by CVM STOPPED, then DetachDisks.
   (c) TerminateDisks / DeleteSnapshots: query DescribeSnapshots --DiskIds '[...]'
       and surface the freshness of the latest snapshot; if no recent snapshot,
       HALT with "create a snapshot first?" gate. For batch (len > 1), require
       `--DryRun` first.
   (d) ApplySnapshot: confirm the source snapshot is SnapshotState=NORMAL and the
       target disk is in a state that allows rollback (ATTACHED or UNATTACHED — see
       core-concepts.md rollback matrix); surface "this overwrites current data;
       confirm you have a snapshot of the current state if recovery is needed".
4. Validate DiskType × DiskSize against `core-concepts.md` matrix (CLOUD_BSSD
   20–32000 GB; CLOUD_PREMIUM 50–32000 GB; CLOUD_SSD 250–32000 GB; LOCAL_BASIC
   and LOCAL_SSD are not resizable). HALT on invalid combination.
5. For AttachDisks: verify the target CVM exists and is RUNNING or STOPPED via
   qcloud-cvm-ops DescribeInstances; verify disk and CVM are in the SAME zone
   (CBS rejects `InvalidDisk.ZoneMismatch` loudly but catch it pre-flight);
   verify CVM has free disk slots via DescribeInstances.Instance.DiskCount.
6. For CreateDisks: capture `ClientToken="$(date +%s%N)"` ONCE and reuse on every
   retry within the 5-minute dedup window. Before retry, run DescribeDisks with
   DiskName + Placement.Zone to detect a partial create.
7. Mask any credential in command lines and trace; never log TENCENTCLOUD_SECRET_KEY.

# Execute
- Run the operation; capture the full command line (with TENCENTCLOUD_SECRET_KEY
  masked as `<masked>`)
- Capture raw response JSON. For state-transition ops, the response often contains
  only `RequestId`; poll DescribeDisks / DescribeSnapshots for the final state.
- For ResizeDisk: the response is ONLY RequestId (no new size in response). Poll
  DescribeDisks until `DiskState != EXPANDING` AND `DiskSize == {{user.new_disk_size}}`
- For TerminateDisks: capture RequestId; post-call DescribeDisks must return 404
  (or empty DiskSet) to prove absence.
- For DetachDisks / AttachDisks / CreateDisks: poll terminal state per SKILL.md
  "Expected State Transitions" table (5s interval, 120s–600s max wait).

# Validate
- Parse the relevant `{{output.*}}` fields per SKILL.md "Response Field Table"
- For ResizeDisk: post-poll DescribeDisks must show DiskSize == {{user.new_disk_size}}
  AND DiskState != EXPANDING; if DiskState is still EXPANDING after max-wait (300s),
  mark timeout and surface to user.
- For destructive ops, confirm post-state (404 / absent / new DiskSize / ROLLBACKING
  exit).
- For ModifyDiskAttributes: confirm the attribute changed; if DeleteWithInstance
  toggled FALSE → TRUE, surface "this disk will auto-delete when the attached CVM
  is terminated".

# Recover (on failure)
- See SKILL.md "Error Code Reference (CBS-Specific)" — distinguish HALT (0 retries)
  from retryable (3 retries with exponential backoff)
- For CreateDisks RequestLimitExceeded: reuse the SAME ClientToken captured in
  Pre-flight; do NOT regenerate
- For OperationConflict.DiskOperationConflict: wait 30s, poll DescribeDisks to
  confirm the disk has left the transition state, then retry
- For InvalidDisk.NotFound / InvalidSnapshot.NotFound: treat as a no-op (already
  in target state) and return success, NOT a retry loop
- For InvalidParameterValue.DiskSizeTooSmall on ResizeDisk: this is the API's
  generic reject of a shrink attempt; HALT (the pre-flight should have caught
  this) and surface "CBS does not support shrink — alternative: create a new
  smaller disk, copy data with rsync, decommission the old one"

# Critic feedback from previous iteration (may be empty)
{{output.critic_feedback}}

# Rubric to optimize against
{{output.rubric}}

# Return (strict JSON)
{
  "status": "OK" | "ERROR",
  "operation": "<subcommand>",
  "command": "<full tccli or python invocation, credentials masked>",
  "exit_code": 0,
  "raw_response": { ... },
  "outputs": {
    "disk_id": "disk-xxx",
    "snapshot_id": "snap-xxx",
    "request_id": "...",
    "disk_state": "UNATTACHED|ATTACHED|EXPANDING|ROLLBACKING|TORECYCLE|...",
    "disk_size": 50,
    "client_token": "<captured once at request start, reused on retries>",
    "final_state": "EXISTS|DELETED|ATTACHED|DETACHED|RESIZED|ROLLED_BACK|..."
  },
  "trace": {
    "preflight": [...],
    "execute": [...],
    "validate": [...],
    "recover": [...]
  },
  "errors": [ {"code": "...", "message": "...", "retried": 0|1|2|3} ],
  "safety_gates_fired": [
    "expand_only_invariant_check",
    "snapshot_freshness_probe",
    "delete_with_instance_warning",
    "filesystem_unmount_warning",
    "zone_match_check"
  ]
}
```

---

## 2. Critic prompt template

**Critic MUST NOT see the raw user request.** It judges only what was actually done,
against the rubric. This prevents "answer-aligned" rubber-stamping.

```text
You are an independent cloud-operation auditor for the qcloud-cbs-ops skill.
You will see one execution result and its full trace. Score it STRICTLY against the
rubric below. Do NOT consider the original user request — judge only what was
actually done.

# Rubric
{{output.rubric}}

# Generator output (raw)
{{output.generator_output}}

# Trace (command, params, raw response, errors, polling tail)
{{output.trace}}

# Scoring rules
- correctness: 0 / 0.5 / 1 — disk/snapshot state matches the operation (post-poll
  DescribeDisks / DescribeSnapshots; DiskIdSet[0] parses; DiskSize matches for
  ResizeDisk)
- safety: 0 / 1 — strict: any missing safety gate from rubric §4 ⇒ 0. CBS-specific:
  shrink attempt submitted to API ⇒ 0; TerminateDisks without snapshot probe ⇒ 0;
  DetachDisks on RUNNING CVM without unmount warning ⇒ 0; ApplySnapshot without
  rollback warning ⇒ 0
- idempotency: 0 / 0.5 / 1 — ClientToken captured once and reused on retry; no-op
  recognition (InvalidDisk.NotFound / InvalidSnapshot.NotFound treated as success);
  no silent regen of ClientToken on RequestLimitExceeded retry
- traceability: 0 / 0.5 / 1 — full command line + raw response + RequestId +
  polling tail + post-call DescribeDisks/DescribeSnapshots captured; credentials
  masked
- spec_compliance: 0 / 0.5 / 1 — DiskType×DiskSize matrix; zone match (AttachDisks);
  resizability check (ResizeDisk); snapshot quota (CreateSnapshot); rollback
  matrix (ApplySnapshot); credential masking throughout

# CBS-specific rule checks (rubric §4)
For each of the 5 rules (TerminateDisks / DetachDisks / ResizeDisk /
DeleteSnapshots / ModifyDiskAttributes), decide: VIOLATED / SATISFIED /
NOT-APPLICABLE. Record violations in `rule_violations` with operation name and
short evidence-based rationale.

# CBS critical invariants (rubric §2.1)
- ExpandOnly: did the Pre-flight reject target < current for ResizeDisk BEFORE the
  API call? If the call was submitted and the API returned InvalidParameterValue,
  this is a violation even if the operation eventually "succeeded" (it did not).
- Snapshot-before-destroy: did the Pre-flight probe DescribeSnapshots and surface
  the freshness before TerminateDisks? An empty or 90-day-old snapshot is a
  violation of rule 1.
- DeleteWithInstance toggle: was the FALSE → TRUE transition surfaced with a
  clear "this disk will auto-delete when the attached CVM is terminated" warning
  AND explicit user confirmation? A silent toggle is a violation of rule 5.
- Filesystem unmount: was a DetachDisks on a RUNNING CVM gated by a "the OS
  filesystem must be unmounted first" warning? A direct detach on RUNNING CVM
  without warning is a violation of rule 2.

# Credential / secret hygiene (rubric §3.2 / §3.4)
Confirm TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY are NEVER present in the
command line, raw response, or trace beyond `<masked>` / `***`. If any appears,
traceability and safety BOTH score 0.

# Return (strict JSON)
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
    {
      "rule": 1|2|3|4|5,
      "operation": "TerminateDisks|DetachDisks|ResizeDisk|DeleteSnapshots|ModifyDiskAttributes",
      "rationale": "short, evidence-based reason"
    }
  ],
  "invariants": {
    "expand_only_enforced": true|false,
    "snapshot_freshness_probed": true|false,
    "delete_with_instance_warning_fired": true|false,
    "filesystem_unmount_warning_fired": true|false
  },
  "thresholds": {
    "correctness": 1.0,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5
  },
  "rubric_version": "v1"
}
```

---

## 3. Orchestrator prompt template

The Orchestrator controls the loop and decides PASS / RETRY / ABORT. It does **not**
score on its own — it consumes the Critic's JSON.

```text
You are the Orchestrator for the qcloud-cbs-ops GCL loop.
Inputs: the user's request, the rubric, the latest Generator output, and the latest
Critic output. You decide whether to PASS, RETRY (and inject feedback into the next
Generator run), or ABORT.

# State
- skill: qcloud-cbs-ops
- max_iterations: 2  (per AGENTS.md §8 Per-Skill Defaults — qcloud-cbs-ops → required, max_iter=2)
- current_iter: {{output.current_iter}}
- previous iterations: {{output.iterations}}
- latest critic: {{output.critic_output}}
- latest generator: {{output.generator_output}}

# Decision logic (first match wins — per AGENTS.md §5)
1. If any critic score is 0 in safety OR a rule_violation has rule ∈ {1, 2, 3, 4, 5}:
   ABORT. Do NOT return partial result. For CBS especially:
   (a) ResizeDisk shrink attempt submitted to API (rule 3 violation) ⇒ ABORT
   (b) TerminateDisks without snapshot probe + explicit confirmation (rule 1) ⇒ ABORT
   (c) DetachDisks on RUNNING CVM without unmount warning (rule 2) ⇒ ABORT
   (d) DeleteSnapshots last-baseline without warning (rule 4) ⇒ ABORT
   (e) ModifyDiskAttributes DeleteWithInstance toggle silent (rule 5) ⇒ ABORT
   (f) credential leakage in trace ⇒ unconditional ABORT
2. If current_iter >= max_iterations: return BEST-SO-FAR (highest weighted total)
   plus UNRESOLVED rubric items. Mark final.status = "MAX_ITER".
3. If all thresholds met: PASS. Return generator output as-is.
4. Otherwise: RETRY. Inject critic.suggestions into Generator's
   {{output.critic_feedback}} for next iteration.

# Thresholds (from rubric.md)
- correctness ≥ 0.5 (1.0 required for TerminateDisks / DeleteSnapshots / ApplySnapshot
  / ResizeDisk — all four are destructive or one-way)
- safety = 1
- idempotency ≥ 0.5
- traceability ≥ 0.5
- spec_compliance ≥ 0.5

# Trace persistence (MANDATORY — AGENTS.md §6)
On every iteration, append to:
  ./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json
Schema: see AGENTS.md §6.

# Return (strict JSON)
{
  "decision": "PASS" | "RETRY" | "ABORT" | "MAX_ITER",
  "iter": <int>,
  "next_feedback": "<string to inject into Generator's {{output.critic_feedback}}>",
  "final": {
    "status": "PASS" | "MAX_ITER" | "SAFETY_FAIL",
    "output": <generator output or best-so-far>
  }
}
```

---

## 4. Per-operation variants (when to inject extra rules)

The base templates above cover all CBS operations. For destructive or sensitive ops,
the **Generator's pre-flight** is augmented with the CBS-specific safety rules from
`rubric.md` §4. Concretely, the agent appends to the trace's `preflight` array:

| Operation | Pre-flight augmentation |
|---|---|
| `TerminateDisks` (destroy) | rule 1: Disk ID + Name + Size + Status echo; warn irreversible; surface `DeleteWithInstance` flag (CBS-only attribute on the disk itself, distinct from the CVM-level flag); explicit confirm "yes, destroy disk `disk-xxx` (name) permanently"; for batch (len > 1) require `--DryRun=true` first; probe `DescribeSnapshots --DiskIds '["disk-xxx"]'` and surface snapshot freshness (last snapshot within 7 days ⇒ safe; older ⇒ warn) |
| `DetachDisks` (force detach) | rule 2: Disk ID + attached CVM ID + DiskState echo; warn that detaching a disk attached to a `RUNNING` CVM without `--unmount` (i.e. without `umount` in OS) may cause data corruption; require the user to confirm filesystem is unmounted first OR instruct them to STOP the CVM before detach; if user insists, surface the failure mode ("the OS file system page cache has not been flushed; last 5 minutes of writes may be lost") |
| `ResizeDisk` (any) | rule 3: Show current size → target size; reject `target < current` with "CBS does not support shrink — alternative: create a new 50GB disk, copy data with rsync, decommission the old one" BEFORE the API call (do not submit); if `target == current`, warn "this is a no-op"; if `target > current`, surface post-call reminder "extend the filesystem inside the OS (`resize2fs` for ext4 / `xfs_growfs` for XFS)"; check DiskType is resizable (LOCAL_BASIC / LOCAL_SSD ⇒ HALT); check quota via DescribeDiskConfigQuota |
| `DeleteSnapshots` (any) | rule 4: Snapshot ID + Name + Size + CreatedTime + any dependent image/ApplySnapshot references echoed; warn that deleting the last baseline of an incremental chain invalidates all newer snapshots; require confirmation "yes, delete snapshot `snap-xxx` (name)"; for batch (len > 1) require `--DryRun` first; for the oldest snapshot in a chain, surface "this is the baseline — deleting it forces full re-snapshot of all newer disks" |
| `ModifyDiskAttributes` (esp. `DeleteWithInstance` toggle) | rule 5: Echo new attributes BEFORE the call; for `DeleteWithInstance` toggle `FALSE` → `TRUE`: warn "this disk will auto-delete when the attached CVM is terminated — any CVM lifecycle event (decommission, replacement, maintenance termination) will destroy this disk"; for `TRUE` → `FALSE` reversion: surface "this is a safety improvement — disk will no longer auto-delete on CVM termination"; for `ProjectId` change: warn that billing / cost allocation shifts; require explicit confirmation per change |

The Critic's rule-violation check is symmetric — it consults the same five rules
independently of which operation was actually run.

### Read-only variant (optional, max_iter=3, advisory)

`DescribeDisks`, `DescribeSnapshots`, `DescribeDiskConfigQuota`, `DescribeSnapshotQuota`
are read-only and may be run through a lighter G/C loop (max_iter=3, no ABORT on
correctness, suggestions only). Concretely, the prompt template's "Operation"
placeholder resolves to "Describe*(read-only)" and the Critic scores:

- correctness: did the API return the expected entity set / quota headroom?
- traceability: are the CLI invocations and JSON paths captured?
- spec_compliance: is the region / zone valid?

Safety / idempotency / destructive-rule violations are N/A for read-only ops.

### Well-Architected assessment variant (read-only, delegate-from `qcloud-well-architected-review`)

When invoked by the orchestrator with `{{user.mode}} = well-architected-readonly` and
`{{user.scope}}` ∈ {single-resource, account-wide}, only `Describe*` operations are
allowed. Return `{{output.product_assessment}}` per the Well-Architected Worker Output
Contract ([worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md),
`product: cbs`). The Critic's safety / idempotency scores are N/A; the Generator must
not perform any mutation regardless of `{{user.request}}` content. See
[`references/well-architected-assessment.md`](../cbs-ops/references/well-architected-assessment.md)
for the four-pillar scoring (Reliability, Security, Cost, Efficiency).

---

## 5. Anti-patterns (banned)

Carried over from [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) and re-stated
for the CBS skill:

- ❌ **Critic sees the user request** — even paraphrased. The Critic prompt above
  explicitly omits the `{{user.*}}` block.
- ❌ **Shared context G + C** — the G and C prompts above are designed for **isolated
  sessions / sub-agents**. Re-using one conversation for both is "pseudo-GCL" and
  violates AGENTS.md §2.
- ❌ **Critic mutates resources** — the Critic prompt above does not contain any
  `tccli cbs` / SDK invocation. It only reads `{{output.generator_output}}` and
  `{{output.trace}}`.
- ❌ **Silently downgrading on Safety fail** — the Orchestrator's rule #1 emits
  `ABORT` immediately; it cannot be overridden by a "best effort" suggestion.
- ❌ **Trace not persisted** — the Orchestrator's step `Trace persistence` is
  non-negotiable; even on ABORT, a trace entry must be written.
- ❌ **Logging secret content** — extending the AGENTS.md list with the CBS-specific
  ban on letting `TENCENTCLOUD_SECRET_KEY` appear unmasked anywhere in command,
  response, or trace.
- ❌ **`ResizeDisk` shrink submitted** — CBS-specific: the API silently rejects
  with a generic `InvalidParameterValue.DiskSizeTooSmall`; the user gets no clear
  "shrink not supported" message. The Pre-flight rule (rubric §4 rule 3) MUST
  catch this BEFORE the API call. Submitting the shrink burns an audit-log entry
  and a quota slot.
- ❌ **`TerminateDisks` without snapshot offer** — CBS-specific: the most common
  support ticket is "I wanted to detach but it was destroyed because of
  DeleteWithInstance" or "I destroyed the disk but didn't realise there was no
  recent snapshot". The Pre-flight rule (rubric §4 rule 1) MUST surface both
  the snapshot probe AND the DeleteWithInstance flag check.
- ❌ **`ApplySnapshot` rollback without backup of current state** — CBS-specific:
  `ApplySnapshot` overwrites the current disk with the snapshot contents. The
  Pre-flight MUST surface "this operation destroys any data written after the
  snapshot was taken; create a fresh snapshot of the current state first if
  you might need to roll back further". A silent rollback that destroys
  post-snapshot writes is the second most common CBS incident.
- ❌ **`DetachDisks` on RUNNING CVM without unmount warning** — CBS-specific:
  `DetachDisks` skips filesystem flush. The Pre-flight rule (rubric §4 rule 2)
  MUST warn "the OS filesystem must be unmounted first (or stop the CVM)";
  the failure mode is silent data loss of the last few minutes of writes.
- ❌ **`DeleteWithInstance` toggle silently enabled** — CBS-specific: the most
  dangerous `ModifyDiskAttributes` change. User enables it thinking "clean up
  on decommission" but forgets that ANY CVM lifecycle event (maintenance
  termination, ASG replacement, instance recycling) will also destroy the disk.
  The Pre-flight rule (rubric §4 rule 5) MUST require explicit per-change
  confirmation.
- ❌ **Regenerating `ClientToken` on `CreateDisks` retry** — CBS-specific: CBS uses
  `ClientToken` to dedupe creates within a 5-minute window. The Generator MUST
  capture `ClientToken="$(date +%s%N)"` ONCE at the start of the request and
  reuse it for every retry within the same logical operation. A retry that
  regenerates `ClientToken` defeats the dedup and may create duplicate disks.
- ❌ **`ResizeDisk` on `LOCAL_BASIC` / `LOCAL_SSD`** — CBS-specific: local disks
  are physically attached to the host and CANNOT be resized. The Pre-flight
  MUST reject with "DiskType=LOCAL_BASIC/LOCAL_SSD does not support resize;
  create a new disk and migrate data".

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CBS rollout: Generator + Critic + Orchestrator templates (5 rules, resize-shrink rejection, detach-without-unmount guard, DeleteWithInstance toggle warning, snapshot-chain invalidation probe, ApplySnapshot rollback warning) |
| 1.1.0 | 2026-06-19 | Tier A conformance (Phase 5): flesh out §1 (full Generator template with CBS critical invariants: ExpandOnly, snapshot-before-destroy, DeleteWithInstance toggle, filesystem unmount), §2 (full Critic template with Critic-isolation, 5-dimension scoring, rule_violations + invariants report), §3 (Orchestrator with CBS-specific ABORT conditions), §4 (per-operation variants table retained + read-only + Well-Architected read-only variant), §5 (expanded anti-patterns: 6 AGENTS.md inherited + 6 CBS-specific incl. ClientToken regen, LOCAL_BASIC resize, silent ApplySnapshot rollback), §7 See also. Pre-flight + Validate + Recover phases now reference rubric §3 / §4 explicitly; ClientToken handling per rubric Example D |

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-cbs-ops` → `required`, `max_iterations = 2`
- [rubric.md](rubric.md) — the rubric instance these templates score against
  (5 dimensions + 5 CBS-specific safety rules + ExpandOnly invariant §2.1)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — the
  build-time safety gates and pre-flight tables
- [SKILL.md §Quality Gate (GCL)](../SKILL.md#quality-gate-gcl) — GCL applicability
  declaration (`required`, `max_iter=2`)
- [SKILL.md §Execution Flows](../SKILL.md#execution-flows-agent-readable) — every
  operation's Pre-flight → Execute → Validate → Recover shape
- [`references/core-concepts.md`](../cbs-ops/references/core-concepts.md) — DiskType
  × DiskSize matrix, zone match rules, ExpandOnly invariant definition
- [`references/well-architected-assessment.md`](../cbs-ops/references/well-architected-assessment.md) —
  four-pillar assessment (Reliability / Security / Cost / Efficiency)
- Sibling templates: [`qcloud-cvm-ops`](../cvm-ops/references/prompt-templates.md),
  [`qcloud-cdb-ops`](../cdb-ops/references/prompt-templates.md),
  [`qcloud-cos-ops`](../cos-ops/references/prompt-templates.md),
  [`qcloud-clb-ops`](../clb-ops/references/prompt-templates.md),
  [`qcloud-tke-ops`](../tke-ops/references/prompt-templates.md)