# AGSX GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-agsx-ops` |
| CLI | `tccli ags help` |
| max_iterations | 3 |
- **SDK-only** — no `tccli ags`

Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (AGSX).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **3**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (AGSX — 5 rules). Do not duplicate gate text here.

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


- ❌ **`tccli ags ...` for an AGSX mutation** — AGSX-specific. `tccli` does
  not ship an `ags` subcommand; `tccli ags help` returns "Invalid product"
  (verified per SKILL.md frontmatter `cli_support_evidence`). Any
  `tccli ags ...` invocation in a mutation trace ⇒ Spec Compliance = 0.
  This is the single most common AGSX mistake — copying a CVM/COS/CBS
  command shape and substituting `ags` for the product name. The fix is
  always: rewrite the mutation as a Python SDK call using
  `from tencentcloud.ags.v20250920 import ags_client, models`.
- ❌ **Credential literal in Python source** — AGSX-specific (extends the
  AGENTS.md §9 list with the SDK-side ban). Code like
  `SecretKey="AKIDxxxxxxxxxxxxxxxx"` in a Python script is a hard
  secret-leak regardless of trace masking. The only safe pattern is
  `os.environ.get("TENCENTCLOUD_SECRET_KEY")` (env-var read). Same rule
  applies to `TENCENTCLOUD_SECRET_ID` and `E2B_API_KEY`. Any literal
  credential in source ⇒ Safety = 0 + Spec Compliance = 0.
- ❌ **Swallowing `TencentCloudSDKException` without inspecting `e.code`** —
  AGSX-specific (mirrors rubric §3.5 row 8). A bare `except Exception: pass`
  discards `Code`, `Message`, and `RequestId`, which are exactly the
  fields the troubleshooting playbook needs to drive HALT vs retry.
  Acceptable: `except TencentCloudSDKException as e: ... e.code ...`.
  Unacceptable: `except:` or `except Exception: ...` without `e.code`
  inspection. The Critic must flag this as Spec Compliance = 0.
  prompt above explicitly omits the `{{user.*}}` block. This matches
  the AGENTS.md §9 ban and is the same pattern across all sibling
  templates.
  for **isolated sessions / sub-agents**. Re-using one conversation for
  both is "pseudo-GCL" and violates AGENTS.md §2.
  contain any SDK invocation or `tccli` reference. It only reads
  `{{output.generator_output}}` and `{{output.trace}}`.
  #1 emits `ABORT` immediately; it cannot be overridden by a "best
  effort" suggestion.
  persistence` is non-negotiable; even on ABORT, a trace entry must
  be written.
- ❌ **Logging raw `ApiKey` value** — AGSX-specific. `CreateAPIKey`
  returns the secret value exactly once. Echoing it to trace, console,
  or any persistent log is unrecoverable secret exposure — the value
  cannot be re-fetched. The only acceptable representation in any
  non-ephemeral context is `ak-****<last4>`. The Critic must flag
  any raw `ApiKey` substring as `raw_api_key_in_trace: true` and the
  Orchestrator must ABORT.
- ❌ **`DeleteSandboxTool` without `DescribeSandboxInstanceList`
  enumerate-first pre-check** — AGSX-specific (mirrors rubric §4
  rule 1). Deleting a tool while instances are still active orphans
  every live e2b-protocol session under it (the platform does NOT
  auto-redirect). The 5-second `DescribeSandboxInstanceList` with
  `ToolId` filter is non-negotiable.
- ❌ **`StartSandboxInstance` retry without `DescribeSandboxInstanceList`
  guard** — AGSX-specific. Each call creates a new `InstanceId` with
  new sandbox-hour billing. A retry on `InternalError` without first
  confirming no instance is already `RUNNING` for the requested
  `ToolId` orphans the first instance and bills it twice.
- ❌ **`CreateAPIKey` retry on transient `InternalError` after a
  successful response** — AGSX-specific. The secret value is returned
  exactly once per successful call. Retrying on a transient error
  after the SDK has already returned a response produces a DIFFERENT
  key and overwrites the user's already-stored secret.
- ❌ **`UpdateSandboxTool` reducing `DefaultTimeout` without
  in-flight-session warning** — AGSX-specific (mirrors rubric §4
  rule 4). The platform may terminate in-flight sessions that exceed
  the new timeout. The 5-second BEFORE/AFTER diff and the explicit
  in-flight warning are non-negotiable.
- ❌ **Metadata passed as dict to `StartSandboxInstance`** — AGSX-
  specific. The `Metadata` field MUST be an array of
  `{"Key": ..., "Value": ...}` objects. A `{"key": "value"}` dict
  silently serialises to the wrong shape and the server rejects the
  request with `InvalidParameter` — or worse, accepts the malformed
  payload and ignores the metadata entirely.
- ❌ **Telling the user to use the AGSX web console for state changes** —
  AGSX-specific. The console is read-only by policy (see SKILL.md
  "Overview"); the agent must not route any state change through the
  console. If the user reports "I clicked Delete in the console",
  the agent should HALT and explain the console is not an agent
  execution path.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 AGSX rollout: Generator + Critic + Orchestrator templates for AGSX (5 rules, isolated-context enforcement, SDK-only path with `v20190312` import, agent-pool cascade, force-termination no-rollback, pool config disruption, provisioning cost). 40-line skeleton, 4 sections (§1, §4, §5, §6) |
| 1.1.0 | 2026-06-19 | Tier A flesh-out: added §2 Critic (full isolation, SDK exception handling check, raw ApiKey detection, sdk_only_violation flag), §3 Orchestrator (full decision logic with SDK-only ABORT clause, max_iter=3), §4 Per-operation variants (8 rows incl. `UpdateSandboxTool` BEFORE/AFTER, `CreateAPIKey` shown-once, `StartSandboxInstance` retry-guard, `CreatePreCacheImageTask`, Well-Architected read-only variant), §5 Anti-patterns (8 AGSX-specific patterns: tccli call, credential literal, SDK exception swallow, raw ApiKey log, delete-without-enumerate, retry-without-guard, CreateAPIKey retry, Metadata dict, console path), §7 See also. Updated §1 Generator to mandate `v20250920` import path (the current API version per `SKILL.md` frontmatter `api_profile: 2025-09-20`) with `v20190312` legacy variant only for `agent_runtime` sub-product. Source-of-truth cross-references moved to AGENTS.md §7. SDK-only hard constraint documented per `cli_applicability: sdk-only` and `cli_support_evidence` in SKILL.md frontmatter |

| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7 Prompt Templates](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) — the 5-dimension rubric spec these templates score against
- [AGENTS.md §5 Termination](../../AGENTS.md#5-termination-first-match-wins) — `PASS` / `MAX_ITER` / `SAFETY_FAIL` semantics
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-agsx-ops` is `recommended`, `max_iter=3`
- [AGENTS.md §9 Anti-Patterns](../../AGENTS.md#9-anti-patterns-banned) — the seven cross-skill anti-patterns this file extends
- [AGENTS.md §14 Reflexion Integration](../../AGENTS.md#14-reflexion-integration-lightweight-reflexion) — failure pattern memory for cross-session learning
- [rubric.md](rubric.md) — the rubric instance these templates score against (Tier A, 8 sections, 5 AGSX-specific safety rules)
- [SKILL.md](../SKILL.md) — the build-time safety gates, pre-flight tables, and Quality Gate (GCL) chapter
- [SKILL.md frontmatter `cli_applicability`](../SKILL.md) — `sdk-only` policy and `cli_support_evidence` (`tccli ags help` → "Invalid product")
- [references/api-sdk-usage.md](api-sdk-usage.md) — full SDK examples for all 10 APIs
- [references/troubleshooting.md](troubleshooting.md) — error remediation playbook (`e.code` → HALT/retry mapping)
- [references/core-concepts.md](core-concepts.md) — AGSX domain model and sandbox types
- [references/cli-behavior.md](cli-behavior.md) — the canonical "Invalid product" verification command (`tccli ags help`) and the AGSX subcommand-absence matrix across supported `tccli` versions; cited by rubric §3.5 row 1 as the build-time evidence the Generator must capture
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (CVM pilot, compute)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (CDB pilot, database)
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (COS pilot, object storage — canonical Tier A template this file is adapted from)
- [`qcloud-redis-ops/references/prompt-templates.md`](../redis-ops/references/prompt-templates.md) — sibling templates (Redis pilot — closest analogue: ephemeral-key, FLUSHALL-style audit-blind-spot surface)
