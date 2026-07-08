# qcloud-skills — Agent guidance

## Repo purpose

Collection of Tencent Cloud AI Agent skills (OpenSpec) for ops runbooks. Each skill is a `SKILL.md` file with YAML frontmatter. Live work happens via `tccli` CLI (primary) or `tencentcloud-sdk-python` (fallback).

## Layout

```
qcloud-skills/
  scripts/                     # Shared executables: validate_*, gcl_runner, gcl_trace_aggregate
  audit-results/               # Runtime output (gitignored)
  qcloud-[product]-ops/        # 24 skill directories
    SKILL.md                   # YAML frontmatter + Markdown runbook
    assets/
      eval_queries.json        # Intent classification test set
      example-config.yaml      # Optional example YAML
      *.schema.json            # JSON Schema / handoff contracts
    references/                # Supporting docs: cli-usage, api-sdk-usage, troubleshooting
```

All schemas, handoff contracts, and skill-specific config live under the owning skill's `assets/` (or `references/` for Markdown-only contracts).

## Skills inventory (24)

- Product-scoped (20): `cvm`, `cdb`, `clb`, `cos`, `es`, `redis`, `monitor`, `tke`, `vpc`, `cam`, `cdn`, `cbs`, `cls`, `ckafka`, `scf`, `mongodb`, `postgres`, `ssl`, `agsx`, `finops`
- Cross-product (3): `qcloud-aiops-diagnosis`, `qcloud-proactive-inspection`, `qcloud-well-architected-review`
- Meta-skill (1): `qcloud-skill-generator` (scaffolds/updates other skills)

Run `ls qcloud-*-ops/` for canonical list.

## Key conventions

- **Dual-path execution**: `tccli` primary; `tencentcloud-sdk-python` fallback. `cli_applicability` field: `cli-first` / `dual-path` (most common, requires `references/cli-usage.md`) / `cli-only` (read-only) / `sdk-only` (verify via `tccli <product> help`).
- **Pre-check → Execute → Verify → Recover**: Standard 4-step runbook shape.
- **Cross-skill delegation**: Check target skill's `## Trigger & Scope` for `delegate-to` markers.
- **Five Core Standards (P0)**: Clear Boundaries, Structured I/O (`{{env.*}}`/`{{user.*}}`/`{{output.*}}`), Explicit Actionable Steps, Complete Failure Strategies (≥10 product-specific error codes with HALT vs retry), Absolute Single Responsibility.
- **Token Efficiency (P0)**: Minimize tokens while preserving executability. Rules: TE-1 (API queries instead of hardcoded tables), TE-3 (error tables ≤3 columns), TE-4 (JSON paths centralized), TE-5 (YAML anchors), TE-6 (eliminate cross-file duplication).
  - **TE Audit Trigger**: After any `SKILL.md`/`references/*.md`/`rubric.md`/`prompt-templates.md` change, scan for >10-line repetitive blocks or >5 inline hardcoded values. Record result in commit footer: `TE-Audit: ...`.
- **Subagent concurrency limit (P0)**: Max 3 concurrent subagents.
- **No web console execution path** (only for docs reference).
- **Minimal-change principle**: Don't reformat/rename/restructure unrelated files.
- **Commit hygiene**:
  - Default: One commit per logical unit.
  - **Hard stops (MUST pause)**: Credentials/secrets in diff, irreversible destructive ops without confirmation, bypassed safety gates, wrong remote/branch/protected branch, sensitive info in commit, mass destructive changes.
- **Python lint gate**: After `*.py` changes, run `ruff check <changed-files>`. After Python SDK code blocks in Markdown, run `python3 scripts/check_markdown_python.py --root .`.
- **UX spec mandatory**: `qcloud-skill-generator/references/user-experience-spec.md`.
- **Asset & schema placement (mandatory)**:
  | Location | Allowed contents |
  |---|---|
  | `qcloud-*-ops/assets/` | `eval_queries.json`, `example-config.yaml`, `*.schema.json`, skill-specific templates |
  | `qcloud-*-ops/references/` | Runbooks, Markdown output contracts, delegation stubs |
  | `scripts/` | Shared executables used by multiple skills |
  | `audit-results/` | Generated traces/reports |

  **Owner skill rule**: Skill defining/primarily consuming a contract owns it. Secondary consumers link via relative path.

## Coding Discipline (Karpathy Guidelines)

### 1. Think Before Coding
- Explicitly state assumptions; ask if uncertain.
- Present multiple interpretations if they exist.
- Suggest simpler approaches when warranted.

### 2. Simplicity First
- No features beyond what was asked.
- No single-use abstractions.
- No unrequested flexibility/configurability.
- Rewrite 200-line solutions that could be 50 lines.

### 3. Surgical Changes
- Touch only what you must.
- Match existing style.
- Don't refactor working code.
- Remove only your own unused imports/variables/functions.

### 4. Goal-Driven Execution
- Define verifiable success criteria.
- For multi-step tasks, state a brief plan with verify checkpoints.

## Mandatory rule: 2-round self-review after every skill update

After modifying `SKILL.md`, `references/`, or `assets/`, MUST run 2 rounds before declaring done.

**Round 1 — Self-check against template & standards**:
1. Re-read `qcloud-skill-generator/references/qcloud-skill-template.md` and `qcloud-skill-generator/SKILL.md`.
2. Verify Five Core Standards (see Key Conventions above).
3. Verify Token Efficiency rules (TE-1/TE-3/TE-4/TE-5/TE-6).
4. Cross-check `cli_applicability` against CLI support.
5. Verify YAML frontmatter validity, bumped `version`/`last_updated`, and `related_skills`.
6. Confirm credentials never printed (only `<masked>`).
7. Check `eval_queries.json` coverage (2-4 positive + 2-4 negative cases for new functionality).
8. Verify asset placement (no repo-root `assets/`).

**Round 2 — Adversarial review**:
1. Apply R1 Security, R2 API Fidelity, R3 Safety Gates, R4 UX from `qcloud-skill-generator/references/governance-and-adversarial-review.md`.
2. Walk through Adversarial Scenarios.
3. Verify cross-skill delegation (manual review step; verify delegate-to markers are present in referenced skills and chains are not broken).

**Fix-on-find**: Any problem must be fixed in same change set.

## Prerequisites for execution

```bash
export TENCENTCLOUD_SECRET_ID=your_secret_id
export TENCENTCLOUD_SECRET_KEY=your_secret_key
export TENCENTCLOUD_REGION=ap-guangzhou
```

Requires `tccli` (pip-installable) and Python 3.8+. `qcloud-finops-ops` additionally needs `TENCENTCLOUD_FINOPS_CONFIG`.

## SKILL.md frontmatter — required fields

- `name` / `description` (skill identity and triggers)
- `compatibility` (execution environment)
- `cli_applicability` (`dual-path`/`cli-first`/`cli-only`/`sdk-only`)
- `cli_support_evidence` (verification command)
- `environment` (required env vars)
- `metadata.version` / `metadata.last_updated` (bump on every change)

## Evaluation

- `assets/eval_queries.json`: Intent-classification test cases (`should_trigger: true/false`).
- **Build-time regression commands**:
  | Change scope | Command |
  |---|---|
  | Full local validation | `python3 scripts/validate_local.py` |
  | SKILL.md frontmatter | `python3 scripts/validate_skills_frontmatter.py` |
  | well-architected-assessment.md JSON | `python3 scripts/validate_product_assessment.py` |
  | GCL rubric/prompt/Quality Gate | `python3 scripts/check_gcl_conformance.py` |
  | gcl_runner.py/gcl_trace_aggregate.py | GCL smoke command + `python3 scripts/gcl_trace_aggregate.py --since-hours 168` |
  | Python files | `ruff check <changed-files>` |
  | Script tests | `cd scripts && python3 -m unittest discover -p "*_test.py" -v` |
  | GCL alarm wiring | `python3 scripts/gcl_alarm_wire.py plan --summary scripts/fixtures/gcl-quality-summary-healthy.json` |
  | Markdown specs/links | `python3 scripts/check_markdown_links.py` |
  | Python SDK code blocks in Markdown | `python3 scripts/check_markdown_python.py --root .` |

- **Runtime GCL**: `scripts/gcl_runner.py` requires external isolated Critic scores in production. `--structural-critic-only` only for CI/local smoke tests.

## Adding or modifying a skill

1. **New skill**: Use `qcloud-skill-generator` (enforces 2-round review).
2. **Existing skill update**: Read meta-skill workflow, apply 2-round self-review.
3. After `git add`, re-run Round 2 against staged version.

## Files that do NOT exist

- No repo-root `assets/` directory.
- No `package.json`, `Makefile`, non-stdlib test runner (except listed scripts in `scripts/` and `.github/workflows/validate-skills.yml`).
- No `CLAUDE.md`, `opencode.json`, `.cursorrules`.
- `.omc/`, `.omo/`, `.codebuddy/`, `.omc/project-memory.json` are gitignored.
- `docs/superpowers/plans/` contains historical notes, not runtime source.

## Key References

| Document | Description |
|----------|-------------|
| `qcloud-skill-generator/SKILL.md` | Meta Skill generator — full workflow, P0/P1 checklist, Token Efficiency rules |
| `qcloud-skill-generator/references/governance-and-adversarial-review.md` | Governance & adversarial review — R1–R4 pre-merge security/resilience/UX |
| `qcloud-skill-generator/references/qcloud-skill-template.md` | Canonical SKILL.md template |
| `qcloud-skill-generator/references/user-experience-spec.md` | UX compliance requirements |
| `docs/gcl-spec.md` | Runtime GCL spec — rubric, trace schema, prompt templates |
| `docs/reflexion-memory.md` | Reflexion rules — cross-session failure-pattern memory governance |
| `docs/failure-patterns.md` | Reflexion memory store |

## Runtime Quality Gates: GCL & Reflexion

Detailed specs externalized to reduce context size. Read before modifying:
- `docs/gcl-spec.md`: GCL-related changes
- `docs/reflexion-memory.md`: Reflexion-related changes
- `docs/failure-patterns.md`: Only when retrieving/updating failure patterns

### GCL hard constraints

- Production GCL requires isolated Generator and Critic contexts.
- Critic is read-only (no `tccli`/SDK calls, no resource mutation).
- Critic sees only sanitized `{{output.operation_intent}}`, Generator output, trace, and rubric.
- Orchestrator generates `operation_intent` before Critic scoring (omits raw user wording, credentials, sensitive IDs).
- `Safety = 0` / `SAFETY_FAIL` aborts immediately.
- Every GCL loop bounded by `max_iterations`.
- Every GCL run persists masked trace under `audit-results/gcl-trace-*.json`.
- Production MUST use external isolated Critic scores; `--structural-critic-only` only for CI/local smoke tests.
- GCL prompt templates use `{{env.*}}`/`{{user.*}}`/`{{output.*}}` (no bare `{...}`).

### Reflexion hard constraints

- Reflexion retrieval is optional hint, not mandatory gate.
- `docs/failure-patterns.md` ≤ 200 lines.
- Deduplicate patterns by `skill` + `command` + `error`.
- Patterns from GCL trace `failure_pattern` or self-review findings only.
- Promote high-frequency patterns to anti-pattern docs.

### Relationship to build-time self-review

Build-time 2-round self-review and runtime GCL are independent gates.

## GCL Trigger Check (MANDATORY)

Before coding, check if GCL is required:

### Check List

1. **Task type**: Contains 修复/新增/重构/变更/优化/测试 or fix/add/refactor/change/optimize/test? → YES
2. **Code lines**: Expected change >5 lines? → YES
3. **File type**: Modifying `*/SKILL.md`, `*/references/rubric.md`, `*/references/prompt-templates.md`, `AGENTS.md`, `qcloud-skill-generator/SKILL.md`, `docs/gcl-spec.md`, `docs/reflexion-memory.md`? → YES
4. **Ops config**: Modifying YAML/JSON/TOML/HCL/Terraform/K8s/Ansible/Docker Compose? → YES (no exceptions)

If any YES, trigger GCL Multi sub-Agent architecture.

### GCL Execution Steps (when triggered)

0. **Pre-flight check**: Confirm current branch is not `main`/`master`/`trunk` and `git remote -v` points to the expected remote. Pause if on a protected branch or mismatched remote.
1. Create worktree: `git worktree add ../<repo>-<feature> -b feature/<feature>`
2. Announce model configuration: Generator (vendor X) + Critics (vendor Y, ≥2, different from Generator)
3. Launch Generator Agent in worktree
4. Launch ≥2 parallel Critic Agents (Data Quality, Safety Rules, Spec Compliance, Token Efficiency)
5. Execute GCL loop (max_iter per skill defaults — see `docs/gcl-spec.md` §8): Generator code → Critics parallel review → Generator fix → Critics re-review
6. Main Agent makes PASS/RETRY/ABORT decision, merges, deletes worktree

### Exceptions

- <5-line typo/comment fixes
- Pure doc/formatting changes

### Verification

After task completion, run: `python3 scripts/verify_gcl_execution.py "<task_description>" <commit_hash>`

## Reflection & Retrospective (P0)

### Core Concept

Every task must produce at least one reusable asset:
- `docs/failure-patterns.md` entry
- Check list/rule
- Script/utility function
- Template
- Decision record
- Troubleshooting flow

### Trigger Points

- After completing a SKILL.md change
- After GCL Critic finds new issues
- After optimizing 3+ skills
- After fixing repeated bugs
- After complex tradeoff decisions

### Execution Flow

1. After task complete, ask:
   - What pitfalls were encountered? → failure-patterns.md
   - What code/pattern is reusable? → template/script
   - What experience should be documented? → update references/AGENTS.md
2. Produce at least one asset
3. Place asset per Asset placement rules
4. Complete and record

### Prohibited Behaviors

- Leaving no docs/records after task
- Fixing pitfalls without recording to failure-patterns.md
- Not building systematic safeguards for repeated issues
- Only thinking "next time" without formal record
