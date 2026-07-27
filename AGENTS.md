# qcloud-skills — Agent guidance

## Repo purpose

Collection of Tencent Cloud AI Agent skills (OpenSpec) for ops runbooks. Each skill is a `SKILL.md` file with YAML frontmatter. Live work happens via `tccli` CLI (primary) or `tencentcloud-sdk-python` (fallback).

## Layout

```
qcloud-skills/
  scripts/                     # Shared executables: validate_*, gcl_runner, gcl_trace_aggregate
  audit-results/               # Runtime output (gitignored)
  qcloud-[product]-ops/        # 31 skill directories
    SKILL.md                   # YAML frontmatter + Markdown runbook
    assets/
      eval_queries.json        # Intent classification test set
      example-config.yaml      # Optional example YAML
      *.schema.json            # JSON Schema / handoff contracts
    references/                # Supporting docs: cli-usage, api-sdk-usage, troubleshooting
```

All schemas, handoff contracts, and skill-specific config live under the owning skill's `assets/` (or `references/` for Markdown-only contracts).

## Skills inventory (34)

- Product-scoped (29): `cvm`, `cdb`, `clb`, `cos`, `es`, `redis`, `monitor`, `tke`, `vpc`, `cam`, `cdn`, `cbs`, `cls`, `ckafka`, `scf`, `mongodb`, `postgres`, `ssl`, `agsx`, `finops`, `ccn`, `vpn`, `dc`, `cicd`, `service-mesh`, `migration`, `tcop`, `tdmq`, `apigw`
- Cross-product (4): `qcloud-aiops-diagnosis`, `qcloud-proactive-inspection`, `qcloud-well-architected-review`, `qcloud-copilot`
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
- **Python lint gate**: After `*.py` changes, run `ruff check <changed-files>`. If that exits non-zero, run `ruff check .` to catch pre-existing errors (e.g. E741 ambiguous variable name like `l`) that would break CI — fix them in the same commit. After Python SDK code blocks in Markdown, run `python3 scripts/check_markdown_python.py --root .`.
- **Spec-Plan-Code Alignment Gate (硬性约束)**: 每次任务开发必须经过三阶段闭环：
  1. **SPEC**：在 `docs/superpowers/specs/` 下编写设计文档（背景、架构、Schema、算法、文件清单）
  2. **PLAN**：在同一文档中编写 Phase 清单（每个 Phase 含具体步骤，checkbox 格式）
  3. **Code vs Spec+Plan 核对**：代码完成后逐条对照 SPEC/PHAN，每条注明 ✅/⚠️/❌；发现不一致必须修复再继续
  - **适用场景**：新增功能模块（`scripts/*.py`）、新数据结构、新算法、新子系统
  - **不适用**：单文件 typo 修复、纯粹格式化调整（<5行无逻辑变更）
  - **Spec 位置**：`docs/superpowers/specs/<short-name>-design.md`
  - **自验证**：SPEC 中必须包含 self-check / self-verify 逻辑（如 `assert not errors`）
  - **后续任务**：同一子系统的后续迭代应追加到已有 SPEC/PROD 文件，而非新建
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

Requires `tccli` (pip-installable) and Python 3.8+. Copy `.env.example` to `.env` for local credentials.

```bash
cp .env.example .env
# edit TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY / TENCENTCLOUD_REGION
```

`qcloud-finops-ops` additionally needs `TENCENTCLOUD_FINOPS_CONFIG` (see `.env.example`).

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
  | Skill quality score / upgrade signal | `python3 scripts/skill_quality_score.py --json` (optional; skipped by `validate_local.py` if absent) |
  | Reflexion retrieval (self-evolution) | `python3 scripts/reflexion_retrieve.py retrieve --skill <skill>` |
  | CADL hook compliance | `python3 scripts/cadl_lint.py` (exit 1 if any `qcloud-*-ops/SKILL.md` lacks the canonical hook; `--fix` injects idempotently) |
  | Python files | `ruff check <changed-files>` |
  | Script tests | `cd scripts && python3 -m unittest discover -p "*_test.py" -v` |
  | GCL alarm wiring | `python3 scripts/gcl_alarm_wire.py plan --summary scripts/fixtures/gcl-quality-summary-healthy.json` |
  | Markdown specs/links | `python3 scripts/check_markdown_links.py` |
  | Python SDK code blocks in Markdown | `python3 scripts/check_markdown_python.py --root .` |

- **Runtime GCL**: `scripts/gcl_runner.py` requires external isolated Critic scores in production. `--structural-critic-only` only for CI/local smoke tests.

## Execution lessons (CADL — distilled, reusable)

> Updated as tasks land. Each item is a machine-hardened lesson, de-duplicated against
> the rules above. Absorb these before writing `scripts/*_test.py` or any credential-masking code.

### L1 — `unittest discover` only finds `TestCase` subclasses
Bare `def test_*(self)` functions at module top level are **NOT** discovered by
`cd scripts && python3 -m unittest discover -p "*_test.py"` — it reports "Ran 0 tests".
Always wrap tests in a `class XxxTest(unittest.TestCase)` and call `unittest.main()`.
**Why:** a plan snippet with bare functions silently passes CI with zero coverage.
**How to apply:** every new `scripts/*_test.py` must use `unittest.TestCase`.

### L2 — Subprocess test paths must be cwd-independent
A test that runs `subprocess.run(["scripts/validate_x.py", ...])` fails when the test
is executed from inside `scripts/` (resolves to `scripts/scripts/...`). Use
`Path(__file__).resolve().parent / "validate_x.py"` so the path is cwd-independent.
**Why:** same test passes in one cwd, fails in another — flaky CI.
**How to apply:** any `scripts/*_test.py` that shells out to a sibling script.

### L3 — Credential-masking regex must cover bare secret-id suffixes
`mask_trace`-style redaction must mask `AKID<hex>` (Tencent secret id with no
`=`/`:`/space delimiter) and `TENCENTCLOUD_SECRET_KEY=<val>`. A pattern that only
matches `key=value` shape leaks the bare id. Use
`re.sub(r"(AKID|secretId|secretKey)[A-Za-z0-9]+", r"\1<masked>", text)`.
**Why:** a brittle regex passed review but leaked `AKIDabcdef12345` verbatim.
**How to apply:** any trace/source sanitization before persistence (KPI#1).

### L4 — KPI rejection paths need explicit tests
A validator may enforce a rule correctly yet have zero tests for the rejection path
(e.g. destructive-without-token → KPI#2, `leak_checked=false` → KPI#1). Add a test
per rejection branch so a future regression fails CI instead of passing silently.
**Why:** correct-but-untested logic hides regressions.
**How to apply:** every gating validator in `scripts/`.

### L5 — Tests must assert populated values, not just key presence
A test that asserts a field *exists* (`"intent_keywords" in s`) passes even when the
value is `[]`/empty — letting a parser/transform bug through (seen: YAML block-scalar
`>-` broke `description`→`intent_keywords` for all 30 skills). Assert the actual
populated value (non-empty list, real substring) for at least one representative case.
**Why:** presence-only assertions give false confidence (green CI, broken data).
**How to apply:** every parser/extractor test in `scripts/`; pair with L1/L4.

### L6 — New CI gates must be proven to BOTH fire and stay silent
An additive gate (e.g. KPI gate in `validate_local`) that only passes the
"no trigger" path gives false confidence. Prove it two ways: (1) silent /
exit-0 when its trigger condition is absent, AND (2) fails (non-zero exit) when
a deliberately-bad fixture that *should* trip it is dropped in. For the KPI gate
this meant crafting an `evidence-*.json` with `safety.leak_checked=false` and
asserting `validate_local` exits 1 with "KPI targets unmet".
**Why:** a gate that never rejects is a no-op wearing a green checkmark.
**How to apply:** every additive CI/quality gate in `scripts/`; craft a negative
fixture that must trip it and assert the non-zero exit (pairs with L4).

### L7 — Re-read the live target file before writing integration specs
A written plan's integration steps are HYPOTHESES, not instructions. Earlier or
parallel efforts may have already implemented the piece you planned to add. On
this branch, `gcl_runner.py` (from an unrelated prior commit) ALREADY had
`mask_secrets()`, `run_command(timeout=...)`, and `persist_trace()` — so the
plan's "add timeout to subprocess.run" / "replace persistence with post_record"
snippets would have conflicted and broken the L4 metrics tracker. Re-reading the
live file first turned a would-be regression into a clean additive integration.
**Why:** executing plan integration snippets against a drifted target causes
duplication or breakage the reviewer must undo.
**How to apply:** before any task that edits an existing file, Read the current
file (or grep its defs) and reconcile the plan step with reality; adapt the spec
to be strictly additive when the capability already exists.

### L8 — Green but vacuous: assert metrics are non-vacuous, not just well-typed
A test that checks "returns a float in [0,1]" passes even when the algorithm is
starved of data or uses a wrong matching strategy. The router's confusion_matrix
returned valid floats (test passed) but was 0.0 everywhere — because (a) the
registry had 21/30 skills with EMPTY intent_keywords (L5), and (b) raw substring
matching can't match CamelCase `DescribeInstances` against `describe my cvm
instances`. Fix required BOTH enriching the source data AND correcting the
algorithm (token-overlap on CamelCase-split words). For any ranking/ML-style
component, assert the metric is MEANINGFUL (e.g. `top1_accuracy > 0` on real
fixtures), not just well-typed. Pairs with L5/L6.

### L9 — Consumer quality is bounded by producer data contract
A consumer (router) only parses what the producer (registry) emits. The router
"passed" while the registry fed it empty keywords — the bug lived upstream. When
a component depends on data from another module, verify the PRODUCER emits
populated, correctly-shaped data (here: enrich `intent_keywords` from the skill's
own curated `eval_queries.json intents`), rather than papering over the gap in
the consumer. Trace the data contract end-to-end before declaring a feature done.

### L10 — Convergence gates on runtime artifacts must skip gracefully, not fail
The single-entry `scripts/Makefile` `all` target wires validate → registry →
golden → kpi. The `kpi` step consumes `audit-results/evidence-*.json`, which is
(1) generated only at runtime and (2) gitignored. A naive `python3
aggregate_kpi.py audit-results/evidence-*.json` would explode (no match → argv
literal → FileNotFound) on a clean checkout, turning a green pipeline red. Fix:
guard the recipe with `if ls audit-results/evidence-*.json >/dev/null 2>&1; then
…; else echo "skipped"; fi`. This is the COUNTERPART of L6 (prove gates fire)
and L4 (rejection tests): gates on *optional runtime output* must be silent-skip
when absent, while gates on *committed input* must hard-fail. Pair the skip with a
unit/integration test that asserts the gate DOES fire when the artifact IS
present (see aggregate_kpi rejection tests, L4/L6).

**Why:** a convergence entry point that fails on a clean checkout blocks every
dev and CI run that hasn't produced evidence yet — the pipeline becomes unc0mmittable.
**How to apply:** any Makefile/CI step that depends on gitignored or
runtime-generated files; make it skip-with-message when absent, and keep a
separate test proving it rejects when present.

### L11 — A KPI gate is only as real as the data it ingests (close the producer→consumer gap)
After wiring the Evidence Kernel, `aggregate_kpi` KPIs `#2 destructive_coverage`
and `#3 provenance` were GREEN but VACUOUS: `emit_evidence_record` HARDCODED
`"destructive": False` and `"token": env_value` (never consulting the real
`preflight`/`bind_token` result already computed in `cmd_run`), while `provenance`
was scored truthy on ANY dict — so both KPIs were pinned at 1.0 and could never
fail. The fix was two-sided (L9 again): (a) PRODUCER — thread the actual PreFlight
`pf` into `emit_evidence_record` and emit real `destructive` + `token_bound`;
(b) CONSUMER — require `provenance.source` ∈ a known enum, and count `token_bound`
not raw token presence. Then add REJECTION tests proving each gate fires (a
destructive op without a bound token → exit 1; unknown provenance source → exit 1).
**Why:** a metric computed from hardcoded/pinned inputs is indistinguishable from
a real one in CI but gives false assurance (repeats L8 at the data layer).
**How to apply:** when a gate reads data emitted by another module, trace the
PRODUCER's actual emission (don't trust the field name) AND assert the CONSUMER
rejects malformed/empty input; ship both halves with a firing test.

## Adding or modifying a skill

1. **New skill**: Use `qcloud-skill-generator` (enforces 2-round review).
2. **Existing skill update**: Read meta-skill workflow, apply 2-round self-review.
3. After `git add`, re-run Round 2 against staged version.

## Files that do NOT exist

- No repo-root `assets/` directory.
- No repo-root `Makefile`, `package.json`, or non-stdlib test runner (except listed scripts in `scripts/` and `.github/workflows/validate-skills.yml`). A `scripts/Makefile` exists as the harness convergence entry point — it is NOT a repo build system.
- No agent-specific config files (e.g. `CLAUDE.md`, `opencode.json`, `.cursorrules`, and similar per-agent artifacts).
- Agent runtime state dirs (e.g. `.omc/`, `.omo/`, `.codebuddy/`, and similar) are gitignored.
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
| `docs/cadl-spec.md` | CADL long-form spec — trigger conditions, 5-step loop, asset types, anti-patterns |

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

### Hard Rule: Worktree Lifecycle (applies to ALL worktree tasks)

Every feature developed in a git worktree MUST be merged back to `main` and the
worktree cleaned up once the task is complete. This is mandatory for **every**
worktree — not only GCL-triggered ones.

1. **Merge back**: From the `main` checkout, `git merge --no-ff feature/<feature>` (or
   fast-forward if linear) so the work lands on `main`.
2. **Clean up**: `git worktree remove ../<repo>-<feature> --force` then
   `git branch -d feature/<feature>` to delete the stale branch.
3. **Verify**: `git worktree list` shows only the `main` checkout; no orphaned
   worktree directories remain on disk.

Do NOT leave feature branches or worktree directories around after the task is
done. A completed worktree that is not merged+removed is considered an incomplete
handoff.

### Exceptions

- <5-line typo/comment fixes
- Pure doc/formatting changes

### Verification

After task completion, run: `python3 scripts/verify_gcl_execution.py "<task_description>" <commit_hash>`

## 复利资产沉淀机制（Compound-Asset Distillation Loop, CADL, P0）

实质任务完成 = 走完 CADL 闭环（不做沉淀 = 任务未完成）。**长篇规范 → [`docs/cadl-spec.md`](docs/cadl-spec.md)**；本节只列硬规则。

### 硬规则（MUST / SHOULD NOT）
- **MUST**：每个完成的任务走 5 步：`提取 → 落点判定 → 写入 → 门禁 → 复用`（详见 `docs/cadl-spec.md` §3）。
- **MUST**：所有 `qcloud-*-ops/SKILL.md` 末尾保留规范的钩子行；`scripts/cadl_lint.py` 是强制门禁，缺钩子即构建失败。
- **MUST**：沉淀前先 `grep` 现有 AGENTS.md / `docs/failure-patterns.md` 避免重复（去重键：`skill + command + error`）。
- **MUST**：写本文件前查 `wc -l AGENTS.md`；≥500 行先精简再写。
- **SHOULD NOT**：一次性上下文、跨任务无复用价值的经验，写进 AGENTS.md。
- **SHOULD NOT**：覆盖 Reflexion 的 200 行 cap 或去重约束（详见 `docs/reflexion-memory.md`）。

### 钩子行（canonical hook, byte-for-byte）
```
> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
```
源头：`qcloud-skill-generator/references/qcloud-skill-template.md` 末尾。`Standard 6` 在生成时强制注入；`scripts/cadl_lint.py` 在验证时强制存在。

### 快速入口
- 自动化：`python3 scripts/cadl_lint.py`（lint）/ `--fix`（幂等补钩子）


## Agent-Agnostic Principle (P0)

**本仓库的全部规则、规范、质量门与沉淀机制，均不绑定任何特定的 coding agent 或其运行时检测机制（所谓"扣点检测"）。规则在任何 OpenSpec 兼容 agent 下都应可被落实。**

- **不依赖特定 agent 的目录 / 文件制品**：如 `.codegraph/`、`.omc/`、`.omo/`、`.codebuddy/` 等属各 agent 自身运行时状态，本仓库规则不得将其作为触发或判定条件；它们仅被 gitignore，不参与规则落实。
- **不硬编码特定 agent 的指引文件路径**：用户级 / 项目级指引文件（AGENTS / CLAUDE / CURSOR 等）的路径随所用 agent 而变，规则只描述"落到哪一层（用户级 / 项目级 / 独立 Skill）"，不写死具体产品路径。
- **工具可选，提供等价 fallback**：当某规则推荐具体工具（如代码智能、KG 索引）时，必须同时给出不依赖该工具的等价做法（如 Read / Grep），使规则在缺失该工具的环境下依然成立。
- **规则以行为结果为导向**：每条规则以"期望的可验证结果"定义（如"任务结束前完成资产沉淀""破坏性操作前确认"），而非"调用某 agent 的某命令"。这样无论底层 agent 是 OpenCode / Cursor / Claude Code / 其他，行为一致。

> 本原则是本文件的最高约束之一：任何新增规则若隐含对特定 coding agent 的依赖，视为违反 P0，须在合并前解耦。

## CodeGraph — code intelligence (recommended when available)

> **Agent-Agnostic note:** CodeGraph is an optional local tool. If the current agent
> environment provides it (`.codegraph/` + `codegraph_explore`), follow the rules below.
> If not, the equivalent behavior is: use Read / Grep directly on the source — the
> *expected result* (accurate, blast-radius-aware code understanding) is unchanged.
> This rule never blocks work on environments without CodeGraph.

`.codegraph/` (SQLite KG + file watcher) pre-indexes every symbol, edge, and call
path in THIS repo. `codegraph_explore` is the Read-equivalent: one capped call
returns verbatim source PLUS caller/callee blast-radius and test-coverage flags —
faster and more accurate than any grep+read loop or sub-agent code-mapping.

**This repo already enforces the sync half of this discipline in
`qcloud-copilot/SKILL.md` ("改 `.py` 后 `codegraph sync`") and in the two
`agent-inspection-prompt.md` checklists. The query-first half was missing and is
added here as a recommended rule (mandatory only where CodeGraph is present).**

### Rule 1 — Query-first, never grep/read first (when CodeGraph available)

Before ANY code-understanding work in THIS repo, prefer `codegraph_explore` with symbol/file
names or a natural-language question. ONE call usually answers the whole question
and returns source you can `Edit` from directly. (If CodeGraph is unavailable, Read / Grep the source directly — same expected outcome.)

- "how does X work" / architecture / a bug / "where is X" → `codegraph_explore`
- Reading/editing a named symbol → put its name in the query; treat returned
  source as already Read.
- Need a flow across symbols → name the endpoints; it rides dynamic-dispatch
  hops grep can't follow and returns the path.

### Rule 2 — Sync after edits (when CodeGraph available)

After editing `.py` / `.ts` / `.go` / `.rs` / etc. in a CodeGraph-enabled environment, the index lags writes by
~1s via the file watcher. Before the NEXT `codegraph_explore` that depends on the
edit, confirm sync (the daemon auto-syncs on file change; if a query returns a
staleness banner for a file you just wrote, `Read` that specific file).

### Rule 3 — anti-pattern (from a real failure, CodeGraph environments)

Do NOT fire `explore` / `librarian` sub-agents or run grep+read loops to map
code THIS repo already indexes. In one session, 5 delegated `explore` agents for
code-mapping hung 16–22 min and returned nothing; the same `codegraph_explore`
call answered in one round-trip WITH blast-radius + "⚠️ no tests" coverage flags.
Delegated agents are for UNINDEXED targets (other repos, web, docs), never for
re-deriving the local KG. (In non-CodeGraph environments this rule is moot — just Read / Grep directly.)

### Rule 4 — scope guard

- CodeGraph covers THIS repo only. For an unindexed project, run `codegraph init`
  first (don't run it yourself unprompted — it's the user's decision; only relevant where CodeGraph is present).
- It does NOT index configs/docs as code; use Read/Grep for those.
- It is read-only intelligence. Correctness is still the compiler/tests' job —
  trust the returned source, but verify with LSP/tests before claiming done.

### Rule 5 — API-First before writing tests or invoking external tools (P0 when CodeGraph available)

Before writing tests for any module/class, or before calling an external tool/MCP
that depends on a module's API, you MUST confirm the actual signature with
`codegraph_explore`. Writing tests against a misread or outdated signature produces
three costs: (1) tests that crash at import, (2) tests that pass against the wrong
behavior, (3) rework every time the discrepancy surfaces in CI.

**Workflow**:
1. `codegraph_explore <symbol_name>` → get actual signature + field names
2. If stale (staleness banner) → `Read` the file directly to confirm
3. Only then write tests or call the external tool with correct arguments

**Fallback** (when CodeGraph unavailable): `Read` the source file directly — same
expected outcome, no sub-agents or grep+read loops.

**This rule applies to ALL test files**, including tests for modules written in
previous sessions or by other agents.

**Evidence from this repo**: Writing unit tests for `ml/predictors/` and
`lib/selective_workflow` without confirming signatures → `TypeError` on every
test (3 rounds of rework). After confirming signatures via `codegraph_explore`,
all 49 tests pass in one shot.

### What to extract from each result

- **Source blocks**: safe to Edit from; do not re-Read.
- **Blast radius** ("N callers", "⚠️ no tests found"): scope your change and
  know what needs new tests BEFORE editing.
- **Staleness banner**: only the listed files are pending re-index — Read those,
  trust the rest.

## Code Review Best Practices

> 来自 Phase G review 实战：5 分钟读代码发现 1 个 CRITICAL + 2 个 HIGH 安全隐患，单元测试 100% 通过但从未触发。

### Review 时必须检查的边界（与测试正交）

**审计/日志类**：
- `__exit__` 是否 re-raise 原始异常？静默吞异常 = 审计数据丢失（CRITICAL）
- 写入文件时磁盘满 / 权限错误是否有 fallback？

**外部调用类**：
- `subprocess.run()` 后是否检查 `returncode`？错误信息是否可见给调用方？
- tccli/API 失败时调用方是否一致检查 `"Error"` key？

**正则类**：
- regex 是否在 `__post_init__` 预编译（不在循环/热路径现编译）？
- 是否有搜索长度限制（`[:10_000]`）防止 ReDoS？

**Fallback/降解类**：
- 模块级 fallback 用 `except Exception` 而非 `except ImportError`（捕获语法错误和传递依赖）
- 外部库私有属性（`_tree_variance` 等）跨版本可能失效 → 用公共 API 替代

**Docstring 类**：
- 示例代码块 `sw = SelectiveWorkflow(...)` 是否与实际 `__init__` 签名一致？
- 默认路径/配置是否与代码一致？

### Review 产出标准

每条 issue 必须包含：
- `file:line` 精确定位
- severity 评级（CRITICAL/HIGH/MEDIUM/LOW）
- 修复建议（具体代码，不是方向）

### 子 Agent MCP 不可用时的 Fallback

code-reviewer 返回 403 → 直接用 `Read` 工具读文件，手动执行上述检查列表。

## Senior Delivery Protocol

- **Autonomous execution**: Once requirements and risk boundaries are clear, proceed without repeated confirmation; ask only when an irreversible decision or missing external fact cannot be safely inferred.
- **Complexity-based isolation**: For multi-file, high-risk, or parallel work, choose a worktree when it improves isolation or rollback. Merge, verify, and remove it before handoff; keep small, low-risk changes in the current checkout.
- **Plan-before-code**: For substantial work, complete SPEC/PLAN and execution gates before touching implementation. Do not use documentation as a substitute for tests or verification.
- **Evidence before claims**: Never claim fixed, complete, or passing without fresh command output. Report pre-existing failures separately from regressions introduced by the task.
- **Minimal senior refactoring**: Prefer root-cause fixes and coherent boundaries over compatibility clutter; preserve legacy adapters only where they protect existing consumers, and define their removal criteria.
- **Post-delivery review**: After every substantial task, review architecture, tests, failures, operational risks, and reusable lessons. Record only cross-task assets; place repo-wide rules here and detailed patterns in the narrowest relevant document.
- **AGENTS.md budget**: Before adding rules, search for overlap and check line count. If this file grows, consolidate or move detailed examples/checklists to linked docs; keep this file as a concise policy index.

## 进度文档维护规范（Progress Document Maintenance）

> 进度文档是团队协作的事实来源；任务完成但文档未更新等于未交付。

### 触发条件

满足任一即必须更新对应进度文档（与 CADL 触发条件重叠，不重复）：

- 任意 SPEC/PLAN 中标记的任务项完成（`[ ]` → `[x]`/`[⚠️]`/`[❌]`）
- 跨 Phase 依赖打通或新增遗留项
- 架构决策变更（即使未写代码）
- Pre-existing 问题发现（不影响本任务但需记录）

### 范围认定

进度文档包括：
- `docs/superpowers/plans/*.md` 中的 Phase/Step checkbox 表
- `docs/superpowers/specs/*.md` 中的 DoD/验收标准对照表

每项勾选须注明：
- 状态：`[x]` 完成 / `[⚠️]` 部分完成 / `[❌]` 放弃
- 证据：commit hash（若已提交）或变更摘要
- 说明：关键决策、遗留项、与其他 Phase 的依赖

### 最小更新单位

- 单个 `[ ]` 勾选可单独更新，无需等待整个 Phase 完成
- 跨 Phase 共用项（如身份语义）在一个 Phase 更新后，其他 Phase 同步勾注引用
- DoD 未满足但需继续前进时，先标记 `[⚠️]` + 说明阻塞原因，再继续

### 反模式

| 反模式 | 正确做法 |
|---|---|
| 任务完成后不更新 plan，留在 `[ ]` 状态 | 按本规范立即更新 checkbox + 证据 |
| 遗留项不记录，假装已完成 | 标记 `[ ]` 保留或 `[❌]` + 说明原因 |
| 只更新 checkbox 不写证据（commit/摘要） | 证据是必需的；无 commit 时写变更摘要 |
| 批量完成后一次性补更新 | 单项完成即更新，不攒批 |

### 与 CADL 的关系

进度文档更新是 CADL "复用" 步骤的显式门禁之一：完成某项后若不更新进度文档，CADL 闭环不完整。不要求每条 CADL 都写进度文档（那是规范层），但每条 SPEC/PLAN checkbox 变更必须同步。

### AGENTS.md 行数门禁

本规范若使 AGENTS.md ≥500 行，应将详细示例/检查清单移至 linked docs，保持本文件为简洁策略索引。
