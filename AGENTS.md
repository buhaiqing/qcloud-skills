# qcloud-skills — Agent guidance

## Repo purpose

Collection of Tencent Cloud AI Agent skills (OpenSpec) for ops runbooks. Each skill is a `SKILL.md` file with YAML frontmatter that an agent reads as an instruction document — these are **NOT executable code**. Live work happens via `tccli` CLI (primary) or `tencentcloud-sdk-python` (fallback) at runtime.

## Layout

```
qcloud-skills/                 # repo root — cross-cutting tooling only (see Asset placement below)
  scripts/                     # Shared executables: validate_*, gcl_runner, gcl_trace_aggregate
  audit-results/               # Runtime output (gitignored); not skill source
  qcloud-[product]-ops/        # 24 skill directories (see Skills Inventory below)
    SKILL.md                   # YAML frontmatter (metadata) + Markdown runbook
    assets/
      eval_queries.json        # Intent classification test set (should_trigger true/false)
      example-config.yaml      # Optional example YAML
      *.schema.json            # JSON Schema / handoff contracts owned by THIS skill
    references/                # Supporting docs: cli-usage, api-sdk-usage, troubleshooting, ...
```

**There is no repo-root `assets/` directory.** Every schema, handoff contract, and skill-specific config lives under the owning skill's `assets/` (or `references/` for Markdown-only contracts).

## Skills inventory (24)

Product-scoped skills (20): `cvm`, `cdb`, `clb`, `cos`, `es`, `redis`, `monitor`, `tke`, `vpc`, `cam`, `cdn`, `cbs`, `cls`, `ckafka`, `scf`, `mongodb`, `postgres`, `ssl`, `agsx`, `finops`.

Cross-product skills (3): `qcloud-aiops-diagnosis` (multi-metric correlation), `qcloud-proactive-inspection` (5-step pipeline), `qcloud-well-architected-review` (4-pillar assessment).

Meta-skill (1): `qcloud-skill-generator` — **scaffolds/updates** other skills, not for live ops. Always check this before manually editing a `SKILL.md` if the change is structural.

Run `ls qcloud-*-ops/` for the canonical list. The `README.md` skill list is also maintained but lags behind when new skills land.

## Key conventions

- **Dual-path execution**: `tccli` CLI is primary; `tencentcloud-sdk-python` is fallback. The `cli_applicability` frontmatter field declares the policy per skill: `cli-first` / `dual-path` (most common — must ship `references/cli-usage.md` and document BOTH paths in every flow) / `cli-only` (read-only skills) / `sdk-only` (e.g. `qcloud-agsx-ops` — `tccli` does not ship an `ags` subcommand; verify via `tccli ags help`).
- **Pre-check → Execute → Verify → Recover** is the standard 4-step runbook shape. Every operation must follow it.
- **Cross-skill delegation**: CVM → VPC/CLB/COS; Monitor → CVM/CLB/VPC; CDB/ES → VPC/Monitor/COS; **Well-Architected** → `qcloud-well-architected-review` (orchestrator) dispatches read-only workers on each `qcloud-*-ops`; **proactive inspection** → `qcloud-proactive-inspection` delegates Discovery to product skills. Check the target skill's `## Trigger & Scope` for explicit `delegate-to` markers before inventing a flow.
- **Five Core Standards** (P0 quality gates, all skills must satisfy): Clear Boundaries, Structured I/O (`{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders), Explicit Actionable Steps, Complete Failure Strategies (≥ 10 product-specific error codes with HALT vs retry), Absolute Single Responsibility.
- **Token Efficiency** (P0 — 强制): 在保持 Agent 可执行性的前提下最小化 Token 消耗。规则包括 TE-1（API 查替代硬编码表）、TE-3（紧凑错误表 ≤3 列）、TE-4（JSON paths 集中声明）、TE-5（YAML anchors）、TE-6（消除跨文件重复）。详见下方 Round 1 检查清单。
- **No web console as agent execution path.** The console may be referenced for product docs but never for state changes.
- **UX spec** in `qcloud-skill-generator/references/user-experience-spec.md` is mandatory for all generated skills.
- **Asset & schema placement (mandatory)** — skill-owned artifacts MUST NOT be placed at repo root. Use this split:

  | Location | Allowed contents | Forbidden |
  |---|---|---|
  | `qcloud-*-ops/assets/` | `eval_queries.json`, `example-config.yaml`, `*.schema.json`, skill-specific templates | Cross-skill executables |
  | `qcloud-*-ops/references/` | Runbooks, output contracts in Markdown, delegation stubs | Duplicate JSON schemas that belong in `assets/` |
  | `scripts/` (repo root) | Shared **executables** used by multiple skills (`validate_*.py`, `gcl_runner.py`, `gcl_trace_aggregate.py`) | JSON Schema, handoff contracts, example YAML |
  | `audit-results/` (runtime) | Generated traces/reports (`gcl-trace-*.json`, inspection outputs) | Source-of-truth schema files |

  **Owner skill rule:** the skill that **defines and primarily consumes** the contract owns the file. Secondary consumers link to the owner via relative path — they do not copy or re-home the schema.

  | Artifact | Owner skill | Secondary consumers (link only) |
  |---|---|---|
  | `gcl-quality-summary.schema.json` | `qcloud-monitor-ops` | `qcloud-proactive-inspection` (report embed), `scripts/gcl_trace_aggregate.py` (docstring) |
  | `finops-handoff.schema.json` | `qcloud-aiops-diagnosis` | `qcloud-finops-ops` |
  | `inspection-handoff.schema.json` | `qcloud-aiops-diagnosis` | `qcloud-proactive-inspection` |

  **When adding a new `*.schema.json` or handoff contract:**
  1. Pick the owner skill (primary consumer of the JSON contract).
  2. Create under `qcloud-<owner>-ops/assets/<name>.schema.json`.
  3. Reference from owner `SKILL.md` / `references/` and owner `example-config.yaml` if config-driven.
  4. Secondary skills cite the owner path (e.g. `../qcloud-monitor-ops/assets/...`) — never `assets/` at repo root.
  5. If a repo-root `scripts/*.py` emits JSON matching the schema, its docstring MUST point at the owner skill path (script ≠ schema owner).

  **Anti-pattern (banned):** creating `assets/` at repo root because a script is shared — shared **code** lives in `scripts/`; shared **contracts** still belong to an owning skill.

## Mandatory rule: 2-round self-review after every skill update

After any modification to a skill's `SKILL.md`, `references/`, or `assets/`, the agent **MUST** run **2 rounds of self-review** before declaring done. This is non-negotiable.

**Round 1 — Self-check against the template & standards** (run before claiming complete):
1. Re-read `qcloud-skill-generator/references/qcloud-skill-template.md` and `qcloud-skill-generator/SKILL.md` for the canonical shape; diff the changed skill against the template.
2. Run the **Five Core Standards** checklist (above). Each must be marked satisfied or N/A with reason.
3. Run the **Token Efficiency** checklist. Verify each TE rule:
   - **TE-1**: Hardcoded tables annotated with "Use API for latest" and query command
   - **TE-3**: Error tables ≤3 columns, compact format; per-operation tables replaced with reference to main table
   - **TE-4**: JSON paths centralized at file top, not duplicated per operation
   - **TE-5**: example-config.yaml uses YAML anchors to eliminate repeated fields
   - **TE-6**: SKILL.md has no inline Python/CLI scripts duplicated in references/; use SDK references instead
4. Cross-check `cli_applicability` against actual CLI support. If `dual-path`, confirm every execution flow shows BOTH `tccli` and SDK steps; if `sdk-only`, confirm the absence of `references/cli-usage.md` is intentional and `cli_support_evidence` cites the verification (`tccli ags help` → "Invalid product" for agsx).
5. Verify the YAML frontmatter is valid, `version` and `last_updated` are bumped, and `related_skills` reflect the new state.
6. Confirm credentials are never printed in any output path — only `<masked>`.
7. Check that eval_queries.json coverage of new triggers is updated (add 2–4 positive + 2–4 negative cases for new functionality).
8. **Asset placement:** any new `*.schema.json`, handoff contract, or skill config YAML is under the **owning** `qcloud-*-ops/assets/` — not repo-root `assets/`. Cross-skill scripts stay in `scripts/` only; they reference the owner schema path in docstring/comments. Secondary consumers link to owner; no duplicate copies.

**Round 2 — Adversarial review** (mirror the meta-skill's governance doc):
1. Apply the four review categories from `qcloud-skill-generator/references/governance-and-adversarial-review.md`: **R1 Security** (credential leaks), **R2 API Fidelity** (invented methods, wrong params — must match official API doc), **R3 Safety Gates** (delete confirmations, pre-backup, rollback), **R4 UX** (Quick Start present, error format, output schema).
2. Walk through the **Adversarial Scenarios** in the same file and confirm none apply.
3. Verify cross-skill delegation works: if the new flow touches another product, confirm the `delegate-to` skill is named and the right `SKILL.md` reference is included.

**Fix-on-find** — any problem surfaced in either round must be fixed in the same change set, not deferred. The change is not "done" until both rounds report clean. Do not skip a round because the diff "looks small"; templates and reference paths drift silently.

## Prerequisites for execution

```bash
export TENCENTCLOUD_SECRET_ID=your_secret_id
export TENCENTCLOUD_SECRET_KEY=your_secret_key
export TENCENTCLOUD_REGION=ap-guangzhou
```

Requires `tccli` (pip-installable) and Python 3.8+. `qcloud-finops-ops` additionally needs `TENCENTCLOUD_FINOPS_CONFIG` pointing at `assets/example-config.yaml` in production.

## SKILL.md frontmatter — required fields

- `name` / `description` — skill identity and trigger conditions (triggers are how agents route; vague descriptions break routing).
- `compatibility` — execution environment (CLI/SDK, Python version, network).
- `cli_applicability` — `dual-path` / `cli-first` / `cli-only` / `sdk-only`. Determines whether `references/cli-usage.md` is mandatory.
- `cli_support_evidence` — cite the verification command (e.g. `tccli cvm help` showing the operations, or `tccli ags help` returning "Invalid product" for sdk-only).
- `environment` — list of required env vars.
- `metadata.version` / `metadata.last_updated` — bump on every change.

## Evaluation

`assets/eval_queries.json` per skill holds intent-classification test cases (`should_trigger: true/false`). No test runner exists in-repo; these are for external evaluation harnesses. When adding capability, add eval cases in the same change.

**Build-time regression:** after changing any `references/well-architected-assessment.md` Worker Output Contract example JSON, run:

```bash
python3 scripts/validate_product_assessment.py
python3 scripts/validate_skills_frontmatter.py
```

Exit non-zero ⇒ fix finding ID / pillar mismatch before claiming done.

**Runtime GCL (Phase 2):** `scripts/gcl_runner.py` implements the Orchestrator loop (trace → external Critic → PASS/RETRY/SAFETY_FAIL). Critic scores MUST be injected from an isolated agent context via `--critic-json` or stdin; use `--structural-critic-only` only for CI smoke tests.

## Adding or modifying a skill

1. **New skill** → use `qcloud-skill-generator` (do not hand-roll). It enforces the 2-round review internally.
2. **Existing skill update** → read the meta-skill's `SKILL.md` workflow section, then apply the 2-round self-review above.
3. After `git add`, re-run round 2 once more against the staged version to catch anything the in-editor view hid.

## Files that do NOT exist

- No repo-root **`assets/`** directory — all skill schemas and handoff contracts live under `qcloud-*-ops/assets/` (see **Asset & schema placement** above).
- No `package.json`, `Makefile`, CI configs, build scripts, linter, typechecker, or test runner — **except**:
  - `scripts/validate_product_assessment.py` — Well-Architected worker JSON regression
  - `scripts/validate_skills_frontmatter.py` — SKILL.md frontmatter checks
  - `scripts/gcl_runner.py` — GCL Orchestrator (Phase 2; external Critic required in production)
  - `scripts/gcl_trace_aggregate.py` — GCL trace → quality summary (Phase 3; feeds monitor-ops / inspection)
  - `.github/workflows/validate-skills.yml` — CI for the above
- No `CLAUDE.md`, `opencode.json`, `.cursorrules` in this repo.
- `.omc/`, `.omo/`, `.codebuddy/`, `.omc/project-memory.json` are gitignored cache data — not source.
- `docs/superpowers/plans/` contains historical planning notes; safe to read but not a runtime source of truth.

---

## Generator-Critic-Loop (GCL) — Adversarial Quality Gate

> Inspired by GAN's Generator/Discriminator idea, but deliberately **not** a real GAN.
> Naming: **GCL (Generator-Critic-Loop)** to avoid misleading reviewers and LLM trainees.
> Sourced from `jdcloud-skills/AGENTS.md` GCL spec, adapted for the Tencent Cloud (`tccli` / `tencentcloud-sdk-python`) execution path.

### 1. Purpose

Apply an adversarial **Generator ↔ Critic** loop with a quantitative rubric to every skill execution.
Most valuable in **high-side-effect cloud operations** (delete, stop, restore, CAM/KMS/DDL) where a single
mistake is unrecoverable.

| GAN (real) | GCL (this spec) |
|---|---|
| Discriminator learns sample distribution | Critic scores an **explicit rubric** |
| No termination condition | Must terminate: **PASS / MAX_ITER / SAFETY_FAIL** |
| G and D train in parallel | G and C run **sequentially** |
| Goal: "fool the D" | Goal: "pass the rubric threshold" |

### 2. Roles

| Role | Job | Input | Output | Forbidden |
|---|---|---|---|---|
| **Generator (G)** | Execute the cloud operation | user request + previous Critic feedback | result + execution trace | modifying the rubric; self-scoring |
| **Critic (C)** | Independently audit G's output | G's result + trace + rubric | scores + suggestions | calling `tccli` / SDK / mutating anything |
| **Orchestrator (O)** | Loop control, termination, final return | context + C scores + budget | continue / final result | executing or scoring on its own |

**Hard constraint:** G and C MUST live in **isolated prompt contexts** (preferably isolated sessions
or sub-agents). A shared context is a "pseudo-GCL" and is explicitly banned — see §9.

### 3. Rubric (mandatory per skill)

Each `SKILL.md` MUST declare its skill-specific rubric. Minimum 5 dimensions:

| Dimension | Meaning | Scale | Default threshold |
|---|---|---|---|
| **Correctness** | Resource id / state / config actually matches the request | 0 / 0.5 / 1 | ≥ 0.5 (1.0 required for `delete` / `stop` / CAM / KMS / DDL) |
| **Safety** | Destructive op (`delete` / `stop` / `restore` / CAM / KMS / DDL) was confirmed or guarded | 0 / 1 | = 1 |
| **Idempotency** | Retrying the same call will not cause duplicate side-effects | 0 / 0.5 / 1 | ≥ 0.5 |
| **Traceability** | Output is auditable: command, params, raw response, errors all captured | 0 / 0.5 / 1 | ≥ 0.5 |
| **Spec Compliance** | Conforms to the skill's `core-concepts.md` / `cli-usage.md` constraints | 0 / 0.5 / 1 | ≥ 0.5 |

**Safety = 0 → ABORT immediately, regardless of total score.**

### 4. Loop Flow

```
User Request
     │
     ▼
[0] Pre-flight (Orchestrator)
    - resolve env.* and user.* variables
    - pick skill, load its rubric
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

### 5. Termination (first match wins)

| Condition | Behavior |
|---|---|
| **PASS** | Every rubric dimension meets its threshold → return G's result |
| **MAX_ITER** | Reached `max_iterations` (default 3) → return **best-so-far** + unresolved rubric items |
| **SAFETY_FAIL** | Safety = 0 → **ABORT**; never return partial or "best-effort" output |

`max_iterations` defaults per skill class — see §8.

### 6. Trace & Audit (mandatory)

Every GCL run MUST persist a JSON trace:

```json
{
  "skill": "qcloud-cvm-ops",
  "request": "<sanitized user request>",
  "rubric_version": "v1",
  "iterations": [
    {
      "iter": 1,
      "generator": { "command": "...", "args": {...}, "exit_code": 0, "result_excerpt": "..." },
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
  "final": { "status": "PASS", "iter": 2, "output": "..." }
}
```

Path: `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` — unified with the existing
`audit-results/` directory (e.g. `qcloud-finops-ops` reports, `qcloud-proactive-inspection` traces).

### 7. Prompt Templates (mandatory per skill)

Each skill's `references/prompt-templates.md` (or equivalent) MUST contain:

1. **Generator Prompt Template** — placeholders: `{{user.request}}`, `{{output.critic_feedback}}`, `{{output.rubric}}`
2. **Critic Prompt Template** — placeholders: `{{output.generator_output}}`, `{{output.trace}}`, `{{output.rubric}}`

> **Placeholder syntax** MUST follow the repository-wide convention
> (see top-level **Five Core Standards → Structured I/O**): `{{env.*}}` / `{{user.*}}` / `{{output.*}}`.
> Bare `{...}` placeholders are NOT allowed in skill prompt templates.

**Critic prompt must hide the raw user request** to prevent "answer-aligned" rubber-stamping.
Recommended skeleton:

```text
You are an independent cloud-operation auditor.
You will see one execution result and its trace. Score it STRICTLY against the rubric below.
Do NOT consider the original user request — judge only what was actually done.

rubric: {{output.rubric}}
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

### 8. Per-Skill Defaults (QCloud)

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

Each skill may override `max_iter` in its own `SKILL.md` (under `## Quality Gate`).

### 9. Anti-Patterns (banned)

- ❌ **Shared context G+C** — defeats independence → banned
- ❌ **Subjective scoring** — Critic must use the rubric, not "vibes" → banned
- ❌ **Unbounded loop** — always hard-cap iterations → banned
- ❌ **Critic sees the user request** — encourages rubber-stamping → banned
- ❌ **Silently downgrade on Safety fail** — must ABORT visibly → banned
- ❌ **Trace not persisted** — no post-mortem possible → banned
- ❌ **Critic mutates resources** — Critic is read-only by definition → banned

### 10. Rollout Roadmap

- **Phase 1 (this commit)** — add this section to `AGENTS.md`; pilot on **`qcloud-cvm-ops`** only
  (most representative destructive workload: `TerminateInstances`, `StopInstances`,
  `ResetInstances` with reset-image, and CAM-driven reset) with its `references/prompt-templates.md`
  and `references/rubric.md`. `qcloud-cdb-ops` and `qcloud-cos-ops` follow in the next PR.
- **Phase 2** — add `scripts/gcl_runner.py` as a reusable Orchestrator (wraps `tccli` calls
  with isolated sub-agent Critic). **Done (2026-06-09):** orchestrator loop + trace persistence;
  Critic via `--critic-json`/stdin; `--structural-critic-only` for CI.
- **Phase 3** — feed `gcl-trace-*.json` into `qcloud-monitor-ops` (custom metric) and
  `qcloud-proactive-inspection` for quality dashboards. **Done (2026-06-13):**
  `scripts/gcl_trace_aggregate.py`, `qcloud-monitor-ops/assets/gcl-quality-summary.schema.json`,
  `qcloud-monitor-ops/references/gcl-quality-dashboard.md`, inspection report embed in
  `qcloud-proactive-inspection/references/reporting.md`; `gcl_trace_ref` on aiops bundles.
- **Phase 4** — wire rubric pass-rate to Cloud Monitor alarms (real incidents refine thresholds).

### 11. Relationship to existing 2-round self-review

GCL is the **runtime** counterpart to the **build-time** "Mandatory rule: 2-round self-review after every skill update"
above. They do not overlap:

| Stage | Owner | Purpose |
|---|---|---|
| **Skill update (build time)** | skill author | Diff skill against template; 5 Core Standards; R1–R4 governance |
| **Skill execution (runtime)** | Generator + Critic | Score a single execution against the skill's rubric; gate side-effects |

Both gates must pass — a clean self-review does not exempt runtime scoring, and a perfect rubric
does not exempt a sloppy skill update.

### 12. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL specification added to `AGENTS.md` (adapted from `jdcloud-skills/AGENTS.md`; per-skill defaults remapped to qcloud skill set; `tccli` / `tencentcloud-sdk-python` execution path; Phase 1 pilot scoped to `qcloud-cvm-ops`) |

### 13. See also

- Each skill's `references/rubric.md` (when shipped) — the rubric instance
- Each skill's `references/prompt-templates.md` (when shipped) — the G/C/O prompt skeletons
- `qcloud-skill-generator/references/governance-and-adversarial-review.md` — build-time R1–R4 review (sister gate)
