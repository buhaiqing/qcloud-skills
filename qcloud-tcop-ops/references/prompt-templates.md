# TCOP GCL Prompt Templates

> **TE-6:** G/C/O backbone → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.
> TCOP is a **read-only advisory** skill (`sdk-only`). No destructive operations are invoked directly.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-tcop-ops` |
| SDK | `tencentcloud-sdk-python` — `tencentcloud.tcop` namespace |
| max_iterations | 1 |

Load rubric §4 before Execute; append gate results to trace `preflight`.

TCOP-specific instruction: all recommendations MUST be presented as proposals with explicit delegation-to-product-skill warnings.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (TCOP).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **1**.

TCOP-specific instruction: because this skill is read-only/advisory, a Safety=0 / rule violation returns a blocking result rather than cloud ABORT; the user sees the warning and chooses whether to delegate to the product skill.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (TCOP — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation → blocking result; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Validate → Recover).

Read-Only Assessment variant (delegate from `qcloud-well-architected-review`):
- `{{user.mode}}` = `well-architected-readonly`
- `max_iterations` = 1
- No ABORT; return `{{output.product_assessment}}` per [well-architected-assessment.md](references/well-architected-assessment.md)

---

## 5. Anti-patterns (banned)

> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.

- ❌ **Presenting TCOP recommendations as executable commands** — TCOP-specific: every recommendation is a proposal. Phrases like "resize the instance now" or "delete the idle resource" bypass product-skill safety gates.
- ❌ **Missing delegation warning to owning product skill** — TCOP-specific: a right-sizing recommendation for CVM must explicitly say "delegate execution to `qcloud-cvm-ops`".
- ❌ **Auto-generating a report that implies actions are taken** — TCOP-specific: `GenerateOptimizationReport` output must label all items as "proposed" and surface side-effect warnings.
- ❌ **Attempting `tccli tcop ...`** — TCOP-specific: `tccli` does not support this product. Any CLI invocation is guaranteed to fail with "Invalid choice".
- ❌ **Exposing cost/waste data in trace without context need** — TCOP-specific: raw cost figures should appear only in user-facing output, not in broad trace contexts.
- ❌ **Unbounded polling for `DescribeOptimizationReport`** — TCOP-specific: polling must use interval 5s and max 120s.
- ❌ **Credential values in SDK examples or trace** — TCOP-specific: all examples use `{{env.*}}` placeholders; `SecretKey` must never be echoed.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-08 | Initial TCOP prompt templates: Generator, Critic, Orchestrator control |
| 1.1.0 | 2026-07-09 | Tier A conformance: flesh out to 7 sections (Generator / Critic / Orchestrator / Per-operation variants / Anti-patterns / Changelog / See also). Added read-only assessment variant and TCOP-specific anti-patterns |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) — banned anti-patterns (re-stated in §5 above)
- [rubric.md](rubric.md) — the rubric instance these templates score against (8 sections, Tier A, 5 TCOP-specific safety rules)
- [SKILL.md](../SKILL.md) — the build-time safety gates, Execution Flows, and `## Quality Gate (GCL)` chapter
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time destructive-op confirmation list
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (read-only FinOpsAnalysis variant reference)
