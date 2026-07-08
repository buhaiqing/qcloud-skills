# COS GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-cos-ops` |
| CLI | `coscmd --help` (object ops); bucket/lifecycle/ACL/versioning via Python SDK `tencentcloud.cos` (no `tccli cos` service) |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (COS).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (COS — 5 rules). Do not duplicate gate text here.

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


- ❌ **Logging secret content** — extending the AGENTS.md list with the COS-specific
  ban on letting `{{user.local_secret_content}}` / `TENCENTCLOUD_SECRET_KEY` appear
  unmasked anywhere in command, response, or trace.
- ❌ **Silent `public-read` / `public-read-write` ACL** — COS-specific: applying
  `public-read` or `public-read-write` without object enumeration is the same family
  of bug as a credential leak; the Generator must surface the default and the Critic
  must catch it.
- ❌ **Treating `DeleteObject` on a versioning-enabled bucket as a hard delete** —
  COS-specific: the most common misunderstanding. `DeleteObject` without `VersionId`
  on a versioning-enabled bucket creates a `DeleteMarker`, not a hard delete.
- ❌ **`coscmd delete -r` without `--dry-run` first** — COS-specific: a single typo on
  a prefix can wipe a million objects. The 30-second `--dry-run` is non-negotiable.
- ❌ **`PutBucketLifecycle` with broad prefix and cold transition in one shot** —
  COS-specific: cold storage transitions are nearly free to apply, costly to recover.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 COS rollout: Generator + Critic + Orchestrator templates for COS (5 rules, isolated-context enforcement, versioning + public-ACL + batch-delete hygiene, FinOpsAnalysis read-only variant) |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [rubric.md](rubric.md) — the rubric instance these templates score against
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (CVM pilot)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (CDB pilot)
