# CBS GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-cbs-ops` |
| CLI | `tccli cbs help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (CBS).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (CBS — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

---

## 5. Anti-patterns (banned)


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.


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
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

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
