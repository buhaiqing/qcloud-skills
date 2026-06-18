# SCF GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-scf-ops` |
| CLI | `tccli scf help` |
| max_iterations | 3 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (SCF).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **3**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (SCF — 5 rules). Do not duplicate gate text here.

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


- ❌ **Logging credentials** — extending the AGENTS.md list with the SCF-specific
  ban on letting `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_SECRET_ID` appear
  unmasked anywhere in command, response, or trace.
- ❌ **`DeleteFunction` without trigger enumeration** — SCF-specific: most common
  incident is "I deleted the test function but the timer trigger was still scheduled
  and caused an alert for 3 days". The cascade is silent: SCF does NOT auto-delete
  triggers in some versions, so orphaned triggers continue to fire and produce failed
  invocations visible only in CLS logs.
- ❌ **`UpdateFunctionCode` silent env var overwrite** — SCF-specific: the new code
  package may carry a different `Environment` requirement, and SCF overwrites the
  old env map entirely (NOT merges). Most common incident: "I added `LOG_LEVEL=debug`
  and lost `DATABASE_URL`". The rollback path is **git tag, not API** — once the env
  vars are gone, there is no API call to recover them.
- ❌ **`UpdateFunctionConfiguration` memory reduction without OOM check** —
  SCF-specific: a 2048 MB → 128 MB reduction will OOM on next invocation (cold start
  itself needs > 128 MB for Python imports + module init). The agent must surface
  the OOM risk before the call and require re-confirmation.
- ❌ **`DeleteTrigger` without listing affected async workflows** — SCF-specific:
  removing a CKafka trigger stops message processing; removing a COS trigger stops
  object-event processing; removing a timer trigger stops scheduled invocations.
  Each of these has a **downstream consumer** (DB writes, cache invalidation, etc.)
  that fails silently when the trigger is gone.
- ❌ **`PublishVersion` silent retry on transient errors** — SCF-specific: every
  `PublishVersion` call mints a new immutable version. A retried `InternalError` can
  create version `N+2` instead of `N+1`, leaving the user with phantom versions.
- ❌ **`CreateTrigger` with auto-suffixed name on collision** — SCF-specific: the
  agent must NOT silently rename `my-trigger` → `my-trigger-v2` when a collision
  occurs. Surface the conflict and ask the user.
- ❌ **`InvokeFunction (Event)` without `RequestId` capture** — SCF-specific: Event
  invocations are fire-and-forget. Without the `RequestId`, the agent cannot
  follow up with `GetRequestStatus` and the invocation outcome is unknown.
- ❌ **`InvokeFunction (RequestResponse)` on a function with side effects without
  side-effect disclosure** — SCF-specific: most common incident is "I invoked the
  function to test it but the function writes to the production database and the
  test invocation created 1000 records". The agent must surface the side-effect
  risk before the call and require explicit user confirmation.
- ❌ **Code package from COS in wrong region** — SCF-specific: if the COS bucket
  is in `ap-shanghai` but the function is in `ap-guangzhou`, the SCF service cannot
  fetch the code package. Cross-region reads are not supported for `CosBucketName`+
  `CosObjectName` inputs.
- ❌ **`VpcConfig` with VpcId/SubnetId in different region or zone** —
  SCF-specific: cross-region or cross-zone VpcConfig will fail at `InvalidParameterValue`
  at create time, not at first invocation. The agent must cross-check region and
  zone before the call.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 SCF rollout: Generator + Critic + Orchestrator templates for SCF (5 rules: function-delete cascade, trigger removal disruption, namespace/layer cascade, code update env var overwrite, function invocation side effects). Per-operation augmentation table. SCF-specific anti-patterns. `max_iter=3` per AGENTS.md §8. |
| 1.1.0 | 2026-06-19 | Tier A flesh-out: expanded §1 Generator with full variable list, 9-step pre-flight (including Function × Handler × Runtime matrix, namespace existence, code package size, BEFORE GetFunction capture for UpdateFunctionCode, MemorySize reduction OOM check, git-tag rollback path surface), polling-tail requirements per state-transition op, TriggerDesc JSON shape validation per trigger type, PublishVersion never-idempotent warning, InvokeFunction (Event) RequestId capture. Expanded §2 Critic with 5 SCF-specific rule checks (rules 1–5 from rubric §4), credential/secret hygiene, strict JSON output. Expanded §3 Orchestrator with 9 SCF-specific ABORT conditions (trigger enumeration, alias enumeration, BEFORE GetFunction, git-tag rollback, MemorySize OOM, async workflow enumeration, Event RequestId, side-effect disclosure), failure_pattern extraction for Reflexion integration (AGENTS.md §14). Expanded §4 per-operation table to 13 ops (added CreateAlias, TerminateAsyncEvent, PutProvisionedConcurrencyConfig, DeleteProvisionedConcurrencyConfig, Well-Architected read-only variant). Expanded §5 anti-patterns to 14 entries (added PublishVersion silent retry, CreateTrigger auto-suffix, InvokeFunction Event missing RequestId, COS code package wrong region, VpcConfig cross-region). Added §7 See also. |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-scf-ops` is `recommended`, `max_iter=3`
- [AGENTS.md §9 Anti-Patterns](../../AGENTS.md#9-anti-patterns-banned) — shared GCL anti-patterns
- [AGENTS.md §14 Reflexion Integration](../../AGENTS.md#14-reflexion-integration-lightweight-reflexion) — failure pattern memory
- [rubric.md](rubric.md) — the rubric instance these templates score against
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables
- [SKILL.md §Quality Gate (GCL)](../SKILL.md#quality-gate-gcl) — per-skill GCL header table
- [SKILL.md §Safety Gates (Destructive Operations)](../SKILL.md#safety-gates-destructive-operations) — the build-time sibling of the runtime safety rules
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (CVM pilot)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (CDB pilot)
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (COS pilot)
- [`docs/failure-patterns.md`](../../docs/failure-patterns.md) — cross-session Reflexion memory (≤200 lines, §1 CLI parameter errors)
