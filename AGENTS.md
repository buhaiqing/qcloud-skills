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
- **Minimal-change principle.** Prefer owner-scoped, minimal diffs. Do not reformat, rename, or restructure unrelated skill files while updating one skill; defer broad cleanups to an explicit follow-up task.
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
   - **TE-6**: SKILL.md has no inline Python/CLI scripts duplicated in references/; GCL G/C/O skeletons in `qcloud-skill-generator/references/gcl-prompt-backbone.md`; product `prompt-templates.md` §4 defers to `references/rubric.md` §4 (§5 product anti-patterns only)
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

**Validation command matrix:**

| Change scope | Required command |
|---|---|
| Any `SKILL.md` frontmatter or metadata change | `python3 scripts/validate_skills_frontmatter.py` |
| Any `references/well-architected-assessment.md` Worker Output Contract example JSON change | `python3 scripts/validate_product_assessment.py` |
| Any GCL rubric, prompt template, or `## Quality Gate (GCL)` section change | `python3 scripts/check_gcl_conformance.py` |
| Any script test or GCL runner change | `cd scripts && python3 -m unittest discover -p "*_test.py" -v` |
| Any GCL alarm wiring change | `python3 scripts/gcl_alarm_wire.py plan` |

**Runtime GCL (Phase 2):** `scripts/gcl_runner.py` implements the Orchestrator loop (trace → external Critic → PASS/RETRY/SAFETY_FAIL). Critic scores MUST be injected from an isolated agent context via `--critic-json` or stdin. Production GCL MUST use externally supplied isolated Critic scores; `--structural-critic-only` is allowed only for CI/local structural smoke tests and MUST NOT be used for production execution, human acceptance, or quality pass decisions.

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
  - `scripts/gcl_runner_test.py` — unit tests for GCL runner behavior
  - `scripts/gcl_trace_aggregate.py` — GCL trace → quality summary (Phase 3; feeds monitor-ops / inspection)
  - `scripts/gcl_alarm_wire.py` — Cloud Monitor alarm wiring for GCL metrics
  - `scripts/check_gcl_conformance.py` — GCL rubric/prompt/Quality Gate conformance check
  - `.github/workflows/validate-skills.yml` — CI for the above
- No `CLAUDE.md`, `opencode.json`, `.cursorrules` in this repo.
- `.omc/`, `.omo/`, `.codebuddy/`, `.omc/project-memory.json` are gitignored cache data — not source.
- `docs/superpowers/plans/` contains historical planning notes; safe to read but not a runtime source of truth.

---

## Key References

| Document | Description |
|----------|-------------|
| `qcloud-skill-generator/SKILL.md` | **Meta Skill generator** — full workflow, P0/P1 checklist, Token Efficiency rules |
| `qcloud-skill-generator/references/governance-and-adversarial-review.md` | Governance & adversarial review — R1–R4 pre-merge security/resilience/UX scenarios |
| `qcloud-skill-generator/references/qcloud-skill-template.md` | Canonical SKILL.md template |
| `qcloud-skill-generator/references/user-experience-spec.md` | UX compliance requirements for all skills |
| `docs/gcl-spec.md` | **Runtime GCL spec** — rubric, trace schema, prompt templates, per-skill defaults, roadmap/changelog |
| `docs/reflexion-memory.md` | **Reflexion rules** — lightweight cross-session failure-pattern memory governance |
| `docs/failure-patterns.md` | **Reflexion memory store** — bounded structured failure patterns for cross-session learning |

---

## Runtime Quality Gates: GCL & Reflexion

Detailed runtime-quality specifications are intentionally externalized to reduce always-loaded context size:

| Spec | Read before modifying |
|---|---|
| `docs/gcl-spec.md` | any `## Quality Gate (GCL)` section, `references/rubric.md`, `references/prompt-templates.md`, `scripts/gcl_runner.py`, `scripts/gcl_trace_aggregate.py`, `scripts/gcl_alarm_wire.py`, `scripts/check_gcl_conformance.py`, or GCL-related CI wiring |
| `docs/reflexion-memory.md` | `docs/failure-patterns.md`, trace `failure_pattern` extraction, Reflexion retrieval/persistence logic, or failure-memory governance |
| `docs/failure-patterns.md` | only when retrieving or updating reusable failure patterns; keep it bounded and deduplicated |

### GCL hard constraints

- Production GCL requires isolated Generator and Critic contexts; shared-context G+C is banned.
- Critic is read-only: it MUST NOT call `tccli`, use SDK clients, mutate resources, or self-score Generator output.
- Critic MUST NOT see the raw user request; it may use sanitized `{{output.operation_intent}}`, Generator output, trace, and rubric.
- Orchestrator owns `operation_intent` generation before Critic scoring; it MUST omit raw user wording, credentials, and unmasked sensitive identifiers.
- `Safety = 0` / `SAFETY_FAIL` MUST abort immediately; never return partial or best-effort output.
- Every GCL loop MUST be bounded by `max_iterations`; unbounded retry loops are banned.
- Every GCL run MUST persist a masked trace under `audit-results/gcl-trace-*.json`.
- Production GCL MUST use externally supplied isolated Critic scores; `--structural-critic-only` is allowed only for CI/local structural smoke tests and MUST NOT be used for production execution, human acceptance, or quality pass decisions.
- GCL prompt templates MUST use `{{env.*}}` / `{{user.*}}` / `{{output.*}}`; bare `{...}` placeholders are banned.
- GCL `required` / `recommended` skills MUST keep `## Quality Gate (GCL)` in `SKILL.md`, plus `references/rubric.md` and `references/prompt-templates.md`.

### Reflexion hard constraints

- Reflexion retrieval is an optional hint, not a mandatory gate.
- `docs/failure-patterns.md` MUST stay ≤ 200 lines; prune low-frequency entries when needed.
- Deduplicate patterns by `skill` + `command` + `error`; increment `count` on matches.
- Patterns MUST come from GCL trace `failure_pattern` fields or self-review findings, not ad-hoc subjective notes.
- Promote high-frequency patterns to anti-pattern docs and remove duplicates from memory.

### Relationship to build-time self-review

Build-time 2-round self-review and runtime GCL are independent gates. A clean self-review does not exempt runtime scoring; a passing GCL rubric does not exempt sloppy skill updates.
