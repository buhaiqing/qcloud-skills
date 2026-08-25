# Generator-Critic-Loop (GCL) — Adversarial Quality Gate

> Inspired by GAN's Generator/Discriminator idea, but deliberately **not** a real GAN.
> Naming: **GCL (Generator-Critic-Loop)** to avoid misleading reviewers and LLM trainees.
> Originally drafted against the GCL spec authored for `jdcloud-skills`, then adapted for the Tencent Cloud (`tccli` / `tencentcloud-sdk-python`) execution path. The migration kept the loop mechanics (Generator / Critic / trace schema / safety rules) and replaced all references to the upstream CLI / SDK.

## 1. Purpose

Apply an adversarial **Generator ↔ Critic** loop with a quantitative rubric to every skill execution.
Most valuable in **high-side-effect cloud operations** (delete, stop, restore, CAM/KMS/DDL) where a single
mistake is unrecoverable.

| GAN (real) | GCL (this spec) |
|---|---|
| Discriminator learns sample distribution | Critic scores an **explicit rubric** |
| No termination condition | Must terminate: **PASS / MAX_ITER / SAFETY_FAIL** |
| G and D train in parallel | G and C run **sequentially** |
| Goal: "fool the D" | Goal: "pass the rubric threshold" |

## 2. Roles

| Role | Job | Input | Output | Forbidden |
|---|---|---|---|---|
| **Generator (G)** | Execute the cloud operation | user request + previous Critic feedback | result + execution trace | modifying the rubric; self-scoring |
| **Critic (C)** | Independently audit G's output | G's result + trace + rubric | scores + suggestions | calling `tccli` / SDK / mutating anything |
| **Orchestrator (O)** | Loop control, termination, final return | context + C scores + budget | continue / final result | executing or scoring on its own |

**Hard constraint:** G and C MUST live in **isolated prompt contexts** (preferably isolated sessions
or sub-agents). A shared context is a "pseudo-GCL" and is explicitly banned — see §9.

## 3. Rubric (mandatory per skill)

Each `SKILL.md` MUST declare its skill-specific rubric. Minimum 5 dimensions:

| Dimension | Meaning | Scale | Default threshold |
|---|---|---|---|
| **Correctness** | Resource id / state / config actually matches the request | 0 / 0.5 / 1 | ≥ 0.5 (1.0 required for `delete` / `stop` / CAM / KMS / DDL) |
| **Safety** | Destructive op (`delete` / `stop` / `restore` / CAM / KMS / DDL) was confirmed or guarded | 0 / 1 | = 1 |
| **Idempotency** | Retrying the same call will not cause duplicate side-effects | 0 / 0.5 / 1 | ≥ 0.5 |
| **Traceability** | Output is auditable: command, params, raw response, errors all captured | 0 / 0.5 / 1 | ≥ 0.5 |
| **Spec Compliance** | Conforms to the skill's `core-concepts.md` / `cli-usage.md` constraints | 0 / 0.5 / 1 | ≥ 0.5 |

**Safety = 0 → ABORT immediately, regardless of total score.**

## 4. Loop Flow

```
User Request
     │
     ▼
[0] Pre-flight (Orchestrator)
    - resolve env.* and user.* variables
    - pick skill, load its rubric
    - derive sanitized operation_intent (operation, expected_state, resource_scope, safety_class; no raw user wording or credentials)
     │
     ▼
[1] Generate (G) ───────────────────────┐
    - run tccli / tencentcloud-sdk-python │
    - capture trace                     │
     │                                  │
     ▼                                  │
[2] Critique (C)                       │
    - isolated prompt context           │
    - score every rubric dimension      │
    - emit actionable suggestions       │
     │                                  │
     ▼                                  │
[3] Decide (Orchestrator)              │
    - Safety=0  → ABORT (no partial)   │
    - all pass  → RETURN                │
    - else & iter<max → inject         │
       suggestions into G               │
    - else → RETURN best + unresolved   │
       rubric items                     │
     └──────────────────────────────────┘
```

The Orchestrator owns `operation_intent` generation during Pre-flight. It MUST derive this sanitized object before Critic scoring; the object may include operation, expected state, resource scope, and safety class, but MUST NOT include raw user wording, credentials, or unmasked sensitive identifiers.

## 5. Termination (first match wins)

| Condition | Behavior |
|---|---|
| **PASS** | Every rubric dimension meets its threshold → return G's result |
| **MAX_ITER** | Reached `max_iterations` (default 3) → return **best-so-far** + unresolved rubric items |
| **SAFETY_FAIL** | Safety = 0 → **ABORT**; never return partial or "best-effort" output |

`max_iterations` defaults per skill class — see §8.

## 6. Trace & Audit (mandatory)

Every GCL run MUST persist a JSON trace:

```json
{
  "trace_schema_version": "v1",
  "skill": "qcloud-cvm-ops",
  "request": "<sanitized user request>",
  "operation_intent": {
    "operation": "stop_instances",
    "resource_scope": ["ins-***"],
    "expected_state": "STOPPED",
    "safety_class": "destructive"
  },
  "rubric_version": "v1",
  "masked_fields": ["request", "operation_intent.resource_scope"],
  "iterations": [
    {
      "iter": 1,
      "generator": { "command": "...", "args": {}, "exit_code": 0, "result_excerpt": "..." },
      "critic": {
        "scores": {
          "correctness": 1, "safety": 1, "idempotency": 0.5,
          "traceability": 1, "spec_compliance": 1
        },
        "suggestions": ["..."],
        "blocking": false
      },
      "decision": "RETRY"
    }
  ],
  "final": {
    "status": "PASS",
    "iter": 2,
    "output": "...",
    "failure_pattern": null  // P0-C: {"severity": "critical"|"major"|"minor"}
  }
}
```

### 6b. Three-Layer Compliance Check (Hallucination Detection)

Post-processing optional gate via `--three-layer-check` flag (default False). All output to stderr; never blocks the JSON result path.

| Layer | Script | What it checks |
|---|---|---|
| **Layer 1** | `cli_param_validator.py` | CLI `--flag` existence vs tccli knowledge base (13 skills covered). Invalid flags → `low`/`high` severity. Extensible via `TCLOUD_OPERATIONS` env var (JSON). |
| **Layer 2** | `schema_validator.py` | Response JSON structure: required fields, RequestId presence, data field consistency for list queries, error-without-RequestId (hallucination). 13 skills × actions covered. |
| **Layer 3** | `waf_compliance.py` | Safety (destructive without `--confirmed`), cost (monthly estimate vs thresholds), batch size (≥5 warn / ≥20 fail), idempotency (missing ClientToken on writes), slow convergence. Thresholds overridable via `WAF_*` env vars. |

All three layers are **non-blocking** in v1.6.0 — they emit alerts but do not abort execution. Future versions may promote Layer 3 safety violations to `SAFETY_FAIL`.

Path: `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` — unified with the existing
`audit-results/` directory (e.g. `qcloud-finops-ops` reports, `qcloud-proactive-inspection` traces).

## 7. Prompt Templates (mandatory per skill)

Each skill's `references/prompt-templates.md` (or equivalent) MUST contain:

1. **Generator Prompt Template** — placeholders: `{{user.request}}`, `{{output.critic_feedback}}`, `{{output.rubric}}`
2. **Critic Prompt Template** — placeholders: `{{output.operation_intent}}`, `{{output.generator_output}}`, `{{output.trace}}`, `{{output.rubric}}`

> **Placeholder syntax** MUST follow the repository-wide convention
> (see top-level **Five Core Standards → Structured I/O**): `{{env.*}}` / `{{user.*}}` / `{{output.*}}`.
> Bare `{...}` placeholders are NOT allowed in skill prompt templates.

**Critic prompt must hide the raw user request** to prevent "answer-aligned" rubber-stamping. It may use the sanitized `{{output.operation_intent}}` derived by the Orchestrator.
Recommended skeleton:

```text
You are an independent cloud-operation auditor.
You will see one execution result and its trace. Score it STRICTLY against the rubric below.
Do NOT consider the original user request — judge only what was actually done.

rubric: {{output.rubric}}
operation_intent: {{output.operation_intent}}
generator_output: {{output.generator_output}}
trace: {{output.trace}}

Return strict JSON:
{
  "scores": { "correctness": 0|0.5|1, "safety": 0|0.5|1, "idempotency": 0|0.5|1,
              "traceability": 0|0.5|1, "spec_compliance": 0|0.5|1 },
  "suggestions": ["≤ 3 concrete, executable improvements"],
  "blocking": true|false
}
```

## 8. Per-Skill Defaults (QCloud)

Destructive workload → **required**, max_iter=2. Read-only / advisory → **optional**, max_iter=5. Meta → **optional**, max_iter=3.

| Skill | GCL | Default max_iter | Notes |
|---|---|---|---|
| `qcloud-cvm-ops` | **required** | 2 | `TerminateInstances` / `StopInstances` are destructive |
| `qcloud-cdb-ops` | **required** | 2 | `IsolateDBInstance` / `DropDB` / DDL |
| `qcloud-clb-ops` | **required** | 2 | `DeleteLoadBalancers` / `DeleteListeners` cut traffic |
| `qcloud-cos-ops` | **required** | 2 | `DELETE Bucket` / `DELETE Object` is irreversible |
| `qcloud-es-ops` | **required** | 2 | `DeleteCluster` / `DeleteIndex` |
| `qcloud-redis-ops` | **required** | 2 | `DestroyInstances` / `ClearInstance` (FLUSHALL) |
| `qcloud-tke-ops` | **required** | 2 | `DeleteCluster` / `DeleteNode` |
| `qcloud-vpc-ops` | **required** | 2 | `DeleteVpc` / `ReleaseAddresses` |
| `qcloud-cam-ops` | **required** | 2 | `DetachPolicy` / `DeleteUser` / `RotateAccessKey` |
| `qcloud-cdn-ops` | recommended | 3 | `DeleteCdnDomain` / purge cache |
| `qcloud-cbs-ops` | **required** | 2 | `TerminateDisks` is destructive |
| `qcloud-cls-ops` | recommended | 3 | `DeleteLogset` / `DeleteTopic` |
| `qcloud-ckafka-ops` | **required** | 2 | `DeleteInstance` / `DeleteTopic` |
| `qcloud-scf-ops` | recommended | 3 | `DeleteFunction` / `DeleteNamespace` |
| `qcloud-mongodb-ops` | **required** | 2 | `DropDB` / `TerminateDBInstance` |
| `qcloud-postgres-ops` | **required** | 2 | `DropDB` / `TerminateDBInstance` / DDL |
| `qcloud-ssl-ops` | recommended | 3 | `DeleteCertificates` |
| `qcloud-agsx-ops` | recommended | 3 | SDK-only skill; protect against `DeleteAgentPool` |
| `qcloud-finops-ops` | optional | 3 | reports only; must NOT auto-execute billing changes |
| `qcloud-monitor-ops` | recommended | 3 | `DeleteAlarmPolicy` / `UnbindAlarmRuleResource` |
| `qcloud-aiops-diagnosis` | optional | 5 | read-only; cross-skill correlation |
| `qcloud-proactive-inspection` | recommended | 3 | 5-step pipeline; idempotency is the main risk |
| `qcloud-well-architected-review` | optional | 5 | advisory only; 4-pillar assessment |
| `qcloud-skill-generator` | optional | 3 | meta; must enforce 2-round self-review |

Each skill may override `max_iter` in its own `SKILL.md` (under `## Quality Gate (GCL)`).

## 9. Anti-Patterns (banned)

- ❌ **Shared context G+C** — defeats independence → banned
- ❌ **Subjective scoring** — Critic must use the rubric, not "vibes" → banned
- ❌ **Unbounded loop** — always hard-cap iterations → banned
- ❌ **Critic sees the user request** — encourages rubber-stamping → banned
- ❌ **Silently downgrade on Safety fail** — must ABORT visibly → banned
- ❌ **Trace not persisted** — no post-mortem possible → banned
- ❌ **Critic mutates resources** — Critic is read-only by definition → banned
- ❌ **Structural critic as quality pass** — `--structural-critic-only` is limited to CI/local smoke tests and cannot approve production or human acceptance gates → banned

## 10. Rollout Roadmap

| Phase | Status | Primary artifact | Gate |
|---|---|---|---|
| 1 | Done | `qcloud-cvm-ops/references/{rubric.md,prompt-templates.md}` | CVM pilot for destructive operations |
| 2 | Done | `scripts/gcl_runner.py` | External Critic via `--critic-json`/stdin; structural critic is CI/local smoke only and never a production quality pass |
| 3 | Done | `scripts/gcl_trace_aggregate.py` + `qcloud-monitor-ops/assets/gcl-quality-summary.schema.json` | Quality summary feeds monitor / inspection |
| 4 | Done | `scripts/gcl_alarm_wire.py` | Cloud Monitor alarm plan/apply for GCL SLOs |
| 4.1 | Done | `scripts/check_gcl_conformance.py` | Tier-A conformance for all 24 skills |

Detailed phase changes live in the changelog below.

## 11. Relationship to existing 2-round self-review

GCL is the **runtime** counterpart to the **build-time** "Mandatory rule: 2-round self-review after every skill update"
above. They do not overlap:

| Stage | Owner | Purpose |
|---|---|---|
| **Skill update (build time)** | skill author | Diff skill against template; 5 Core Standards; R1–R4 governance |
| **Skill execution (runtime)** | Generator + Critic | Score a single execution against the skill's rubric; gate side-effects |

Both gates must pass — a clean self-review does not exempt runtime scoring, and a perfect rubric
does not exempt a sloppy skill update.

## 12. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL specification added to `AGENTS.md` (adapted from a sister-farm GCL spec; per-skill defaults remapped to qcloud skill set; `tccli` / `tencentcloud-sdk-python` execution path; Phase 1 pilot scoped to `qcloud-cvm-ops`) |
| 1.1.0 | 2026-06-15 | **Lightweight Reflexion Integration:** cross-session failure-pattern learning added; `docs/failure-patterns.md` became the centralized bounded memory store; GCL trace schema gained `failure_pattern`; Pre-flight gained optional pattern retrieval |
| 1.2.0 | 2026-06-18 | **Phase 4 completion:** `scripts/gcl_alarm_wire.py` (plan/apply/dry-run) + Cloud Monitor alarm policies; `scripts/gcl_runner_test.py` (35 unit tests); `failure_pattern` extraction in `gcl_runner.py`; `qcloud-skill-generator` Charter C7 + Output table GCL artifacts; `## Quality Gate (GCL)` template section |
| 1.3.0 | 2026-06-19 | **Phase 4.1 Tier A conformance:** `scripts/check_gcl_conformance.py` (CI gate); 19 skills fleshed out to 8-section rubric + 7-section prompt-templates + Tier A SKILL.md `## Quality Gate (GCL)` chapter; `qcloud-skill-generator` (Tier D) gained full GCL artifacts |
| 1.4.0 | 2026-06-19 | **Spec extraction and roadmap compression:** detailed GCL and Reflexion specs moved from `AGENTS.md` to `docs/gcl-spec.md` and `docs/reflexion-memory.md`; `AGENTS.md` now keeps only hard constraints, read triggers, and validation pointers; Roadmap compressed to a status table while detailed phase changes remain in this unified changelog |
| 1.5.0 | 2026-07-19 | **P0/P1 runtime quality improvements:** (1) `scripts/predictive_analyzer.py` — capacity prediction engine with OLS, Holt's ES, anomaly alerting per `prediction-engine.md` schema; (2) `scripts/cross_skill_impact.py` — dependency graph, BFS propagation, Kahn topo sort; (3) `scripts/incident_timeline_aggregator.py` — RCA/Event bundle aggregation, topology linking, causal chain; (4) Success pattern retrieval integrated into `gcl_runner.py` pre-flight (`success_pattern_retrieve`, `success_pattern_mine`); `format_for_injection` renamed `ff_fail` to avoid conflict; combined `REFLEXION_PATTERNS` env var with success first; `matched_successes` field added to `preflight_reflexion` trace; (5) Hallucination detection + distribution drift integrated into `gcl_runner.py` post-processing via `--enable-post-process` flag (default False); `post_process()` calls `detect_hallucinations()` and `compute_drift()` after PASS and MAX_ITER paths |
| 1.6.0 | 2026-07-20 | **Three-layer compliance check (Hallucination Detection):** `--three-layer-check` flag enables: layer1=`cli_param_validator.py` (CLI flag existence vs tccli knowledge base, 13 skill coverage); layer2=`schema_validator.py` (response JSON schema vs OpenAPI-style KB: required fields, RequestId, data field consistency); layer3=`waf_compliance.py` (offline safety/cost/stability: destructive confirmation, batch size thresholds, cost estimation, idempotency). All output to stderr; non-blocking.
| 1.7.0 | 2026-08-26 | **Agentic maturity hardening:** (1) fail-safe defaults — `autonomy_policy.py` no-match fallback → `human_approval`, `agent_slo.py` empty samples → N/A + breach; (2) KB automation — `scripts/kb_sync_openapi.py` generates Layer-1/2 KBs from tccli metadata (`assets/shared/tcloud_{cli_flags,response_schemas,kb_coverage}.json`, 21 skills / ~2040 actions), validators merge generated KB via `TCLOUD_KB_DIR`, drift gate `kb_drift_check`; (3) memory efficacy — preflight trace records `injection_id` + `matched_failure_keys[]`, `scripts/reflexion_efficacy.py` reports hint coverage / prevention rate; (4) closed loop — `scripts/self_evolution_loop.py` wires `upgrade_signal` → root cause → golden gate → `SelfHealPRWorkflow`. Spec: `docs/superpowers/specs/agentic-maturity-hardening-design.md` |

## 13. See also

- Each skill's `references/rubric.md` (when shipped) — the rubric instance
- Each skill's `references/prompt-templates.md` (when shipped) — the G/C/O prompt skeletons
- `qcloud-skill-generator/references/governance-and-adversarial-review.md` — build-time R1–R4 review (sister gate)
