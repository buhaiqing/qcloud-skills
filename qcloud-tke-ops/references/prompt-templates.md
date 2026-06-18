# TKE GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-tke-ops` |
| CLI | `tccli tke help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (TKE).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (TKE — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

---

## 5. TKE-specific anti-patterns


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.

- ❌ **Version jump without addon compat check** — UpdateClusterVersion from 1.28 to 1.30 (skipping 1.29) is allowed by the API but breaks addons
- ❌ **DeleteCluster without YAML export** — cluster deletion is irreversible; YAML export is the only recovery path
- ❌ **Drain >50% nodes without PDB check** — draining too many nodes can crash pod scheduling
- ❌ **Public endpoint enabled without IP whitelist** — K8s API server exposed to public internet without ACL
- ❌ **containerRuntime=docker** — docker is deprecated; must use containerd

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 TKE rollout: templates (5 rules, version-upgrade addon-compat guard, node-drain PDB guard, public-endpoint security). Initially cross-referenced CLB templates |
| 1.1.0 | 2026-06-04 | Made templates self-contained: inlined full Generator/Critic/Orchestrator prompts with TKE-specific API names, safety rules, abort conditions, and anti-patterns. Removed CLB cross-reference dependency |
| 1.2.0 | 2026-06-19 | Added §7 See also (Tier A prompt conformance) |

---

| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |

---

## 7. See also

- [AGENTS.md §7 Prompt Templates](../../AGENTS.md#7-prompt-templates-mandatory-per-skill)
- [`rubric.md`](rubric.md) — 5 TKE-specific safety rules
- [SKILL.md](../SKILL.md)
