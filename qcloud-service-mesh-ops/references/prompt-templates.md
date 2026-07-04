# TCM GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-service-mesh-ops` |
| CLI | `tccli tcm` (dual-path) |
| max_iterations | 2 |

**Dual-path execution:** Primary path is `tccli tcm` CLI; fallback is Python SDK (`tencentcloud-sdk-python`).

Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (TCM).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (TCM — 3 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–3; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

---

## 5. Anti-patterns (banned)

> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.

- ❌ **Silent mesh delete** — TCM-specific: deleting a mesh without echoing the Mesh ID + Name and warning about all linked clusters being orphaned is the same family of bug as deleting a database without naming it; the Generator must show the mesh ID + name and the Critic must catch it.
- ❌ **Unlink without traffic warning** — TCM-specific: unlinking a cluster without warning that production traffic governed by the mesh will be disrupted is the most common "why did my traffic break" incident; the warning is mandatory.
- ❌ **Version change without restart warning** — TCM-specific: modifying the mesh version without showing current vs new version and warning that the data plane will restart (brief disruption) causes unexpected downtime; the Generator must show the diff and require confirmation.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.1.0 | 2026-07-04 | Rewritten to 7-section Tier A format: TE-6 backbone references, §4 per-operation variants, §5 anti-patterns. Aligned with rubric §4 (3 rules). |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [rubric.md](rubric.md) — the rubric instance these templates score against
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables