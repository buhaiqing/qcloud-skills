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
- **Python lint gate**: After `*.py` changes, run `ruff check <changed-files>`. After Python SDK code blocks in Markdown, run `python3 scripts/check_markdown_python.py --root .`.
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
  | Skill quality score / upgrade signal | `python3 scripts/skill_quality_score.py --json` |
  | Reflexion retrieval (self-evolution) | `python3 scripts/reflexion_retrieve.py retrieve --skill <skill>` |
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

**这不是一条规范，而是一套工作闭环——任何实质任务完成后，Agent 必须走完「提取 → 落点判定 → 写入 → 门禁 → 复用」才能结束。** 目的是让每次踩坑、每次评审、每次跨 skill 协作都变成下一次的可复用资产，形成复利。

> 本机制升级自原 `Reflection & Retrospective` 段。原资产类型清单（failure-patterns 条目 / checklist / 脚本 / 模板 / 决策记录 / 排查流）继续有效，下文将其纳入闭环的「写入」步骤。

### 为什么是机制而非规范

单条规则（如"记得写 AGENTS.md"）会被忽略，因为无触发、无闭环。CADL 把沉淀变成工作流的**必经出口**：任务不做沉淀 = 任务未完成。Agent 调用任何 Skill 后都走到这一步，Skill 本身也通过 `qcloud-skill-generator` 的「资产沉淀钩子」（见 `qcloud-skill-generator/SKILL.md` Standard 6）提示大模型。

### 触发条件（满足任一即必须走 CADL，不局限 CodeGraph）

- 多步 / 跨文件任务完成
- 跨 Skill 协作（用了 delegation matrix 或并行 agent）
- 评审 / 修复循环（如 GCL、2-round self-review、adversarial review）
- 发现 repo 缺陷 / 坑（即使不在本次 scope，也记）
- 验证中发现预存 FAIL 并归因
- 用户给出可复用的工作流偏好（如"用双写子命令绕过 tccli bug"）

### 闭环步骤

```
1. 提取   → 从刚完成的任务中抽象出可复用模式：
            踩坑避免 / 评审维度 / 协作模式 / 验证命令 / 复用 helper
            格式："问题 → 反模式 → 正确做法（含代码示例）"
2. 落点判定 → 离开本仓库还有用？ → 用户级 ~/.config/opencode/AGENTS.md
            仅本仓库适用？     → 项目级 AGENTS.md（本文件）
            是某 skill 专属可调用的能力？ → 独立 Skill 文件（经 qcloud-skill-generator）
3. 写入   → 可执行、有示例、有边界、先 grep 现有 AGENTS.md 确认未覆盖（不重复）
4. 门禁   → 写入前查 wc -l，本文件 ≥500 行先精简再写（见 AGENTS.md 行数门禁）
            写入 failure-patterns.md 时遵守 ≤200 行约束与 skill+command+error 去重（见 Reflexion hard constraints）
5. 复用   → 下次同类任务，Agent 读 AGENTS.md 即获得该资产 → 复利生效
```

### 资产类型（写入步骤的可选落点）

- `docs/failure-patterns.md` entry（踩坑 / 失败模式，受 Reflexion 约束）
- Check list / rule
- Script / utility function（`scripts/` 共享可执行文件）
- Template
- Decision record
- Troubleshooting flow

### Skill 侧钩子（让每个 Skill 自带沉淀意识）

- **源头**：`qcloud-skill-generator` 在生成每个 skill 时，须在 `SKILL.md` 末尾注入一行（见 Standard 6）：
  `> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。`
  未来所有 `qcloud-*-ops` 自动继承此意识。
- **现存 skill（渐进迁移，pending）**：后续迭代中逐批在 SKILL.md 末尾补同一行提示，使大模型调用任何 skill 后都看到触发信号。本次合并仅落地机制定义 + qcloud-skill-template.md 注入点 + qcloud-skill-generator Standard 6 强制约束；存量 qcloud-*-ops 的逐批补行不在本次 scope，按最小改动原则不在此时批量改写 34 个 skill 文件。
- **大模型侧**：Agent 在任意 skill 调用结束前，主动检查 CADL 触发条件，而非等用户提醒。

### 反模式（违反 CADL）

| 反模式 | 正确做法 |
|---|---|
| 任务做完就结束，不沉淀 | 走完 CADL 闭环再交付 |
| 把一次性上下文当资产写进 AGENTS.md | 只沉淀跨任务可复用的模式 |
| 重复已有条目 | 写入前 grep 确认未覆盖 |
| 只在 CodeGraph / GCL 相关任务才沉淀 | 评审/修复/协作/验证都触发 |

## CodeGraph — code intelligence (MANDATORY)

`.codegraph/` (SQLite KG + file watcher) pre-indexes every symbol, edge, and call
path in THIS repo. `codegraph_explore` is the Read-equivalent: one capped call
returns verbatim source PLUS caller/callee blast-radius and test-coverage flags —
faster and more accurate than any grep+read loop or sub-agent code-mapping.

**This repo already enforces the sync half of this discipline in
`qcloud-copilot/SKILL.md` ("改 `.py` 后 `codegraph sync`") and in the two
`agent-inspection-prompt.md` checklists. The query-first half was missing and is
added here as a hard rule.**

### Rule 1 — Query-first, never grep/read first (MANDATORY)

Before ANY code-understanding work, call `codegraph_explore` with symbol/file
names or a natural-language question. ONE call usually answers the whole question
and returns source you can `Edit` from directly.

- "how does X work" / architecture / a bug / "where is X" → `codegraph_explore`
- Reading/editing a named symbol → put its name in the query; treat returned
  source as already Read.
- Need a flow across symbols → name the endpoints; it rides dynamic-dispatch
  hops grep can't follow and returns the path.

### Rule 2 — Sync after edits (MANDATORY)

After editing `.py` / `.ts` / `.go` / `.rs` / etc., the index lags writes by
~1s via the file watcher. Before the NEXT `codegraph_explore` that depends on the
edit, confirm sync (the daemon auto-syncs on file change; if a query returns a
staleness banner for a file you just wrote, `Read` that specific file).

### Rule 3 — anti-pattern (from a real failure)

Do NOT fire `explore` / `librarian` sub-agents or run grep+read loops to map
code THIS repo already indexes. In one session, 5 delegated `explore` agents for
code-mapping hung 16–22 min and returned nothing; the same `codegraph_explore`
call answered in one round-trip WITH blast-radius + "⚠️ no tests" coverage flags.
Delegated agents are for UNINDEXED targets (other repos, web, docs), never for
re-deriving the local KG.

### Rule 4 — scope guard

- CodeGraph covers THIS repo only. For an unindexed project, run `codegraph init`
  first (don't run it yourself unprompted — it's the user's decision).
- It does NOT index configs/docs as code; use Read/Grep for those.
- It is read-only intelligence. Correctness is still the compiler/tests' job —
  trust the returned source, but verify with LSP/tests before claiming done.

### What to extract from each result

- **Source blocks**: safe to Edit from; do not re-Read.
- **Blast radius** ("N callers", "⚠️ no tests found"): scope your change and
  know what needs new tests BEFORE editing.
- **Staleness banner**: only the listed files are pending re-index — Read those,
  trust the rest.
