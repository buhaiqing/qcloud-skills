# CI/CD GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-cicd-ops` |
| CLI | `tccli` not available (sdk-only) |
| max_iterations | 2 |

**SDK-only constraint:** All execution uses Python SDK (`tencentcloud-sdk-python`). No tccli commands are available for CI/CD operations.

Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (CI/CD).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (CI/CD — 3 rules). Do not duplicate gate text here.

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


- ❌ **Silent pipeline delete** — CI/CD-specific: deleting a pipeline without echoing the ID and name and warning about automation removal is the same family of bug as deleting a database without naming it; the Generator must show the pipeline ID + name and the Critic must catch it.
- ❌ **Stop without artifact warning** — CI/CD-specific: stopping a running build without warning that partial artifacts will be discarded is the most common "why did my artifacts disappear" incident; the 50% heuristic is not relevant here but the warning is mandatory.
- ❌ **Start without duplicate-build check** — CI/CD-specific: triggering a pipeline build without checking for an already-running build creates duplicate builds that waste resources and confuse the deployment flow; the Generator must check and warn.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-04 | Initial CI/CD GCL templates: Generator + Critic + Orchestrator templates for CI/CD (3 rules, SDK-only execution, automation removal hygiene, build abort guard, duplicate-build check). |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [rubric.md](rubric.md) — the rubric instance these templates score against
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables
